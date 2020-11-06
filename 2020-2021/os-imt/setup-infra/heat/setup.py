# Install openstack on top of g5k thanks to enos and configures account for
# students.
#
# Executions:
# $ pipenv install
# $ pipenv run setup  # thanks to Pipfile > scripts > setup-heat
#

import logging
import os
import socket
import yaml

import openstack
import enos.task as enos

# logging.basicConfig(level=logging.ERROR)
logging.basicConfig(level=logging.DEBUG)
LOG   = logging.getLogger(__name__)
TEAMS = [
    ("ronana",      "alebre"),
    ("acharpentier", "ltaillebourg"),
    ("bescouvois", "ldelhommeau"),
    ("iboughalem", "brivard"),
    ("gjacquet","kmer"),
    ("gguirriec", "sbouttier"),
    ("vlouradour", "vquiedeville"),
    ("ebarus", "cegarcia"),
    ("vbourcier", "bvrignaud"),
    ("ytelaoumaten","llebert"),
    ("adelforges","isow"),
]

ENOS_CONF = {
    'provider': {
        'type': 'g5k',
        'env_name': 'debian9-x64-min',
        'job_name': 'imta-fila3-os-test2',
        # 'walltime': '26:00:00'
        'walltime': '3:00:00'
    },
    'resources': {
        'paravance': {
            # 'compute': 13,
            'compute': 2,
            'network': 1,
            'control': 1
        }
    },
    'inventory': 'inventories/inventory.sample',
    'registry': { 'type': 'internal' },
    'enable_monitoring': False,
    'kolla_repo': "https://git.openstack.org/openstack/kolla-ansible",
    'kolla_ref': 'stable/stein',
    'kolla': {
        'kolla_base_distro': "centos",
        'kolla_install_type': "source",
        'enable_heat': True
    }
}


def install_os():
    # Deploy openstack using enos
    args = { '--force-deploy': False, '--env': None, }
    enos.deploy(ENOS_CONF, **args)

    # Get the `env`. I could have put the `enoslib.tasks.@enostask` on top of
    # `install_os` to get an access to the `env`. But, it doesn't always work
    # because of the decorator that assumes `--env` is a filepath at line 100
    # of task.py [1] despite of line 106 that accepts dict.
    #
    # [1] https://gitlab.inria.fr/discovery/enoslib/blob/408e3e2814454704df74fab579958b8be35e5972/enoslib/task.py#L100
    env = None
    with os.open('current/env', 'r') as env_file:
        env = yaml.safe_load(env_file)

    return env


def make_cloud(cloud_auth_url: str):
    """Connects to `cloud_auth_url` OpenStack cloud.

    Args:
        cloud_auth_url (str): Identity service endpoint for authentication,
            e.g., "http://10.0.2.15:80/identity". Do not add the '/v3'!

    Returns:
        An new openstack.connection.Connection

    Refs:
        [1] https://docs.openstack.org/openstacksdk/latest/user/connection.html
        [2] https://developer.openstack.org/api-ref/identity/v3/?expanded=password-authentication-with-unscoped-authorization-detail,password-authentication-with-scoped-authorization-detail#password-authentication-with-scoped-authorization
    """
    LOG.info(f"New authentication for {cloud_auth_url} with admin")
    cloud = openstack.connect(
        # Use Admin credential -- Same everywhere in this PoC!
        auth_url=cloud_auth_url,
        password='demo',
        project_domain_id='default',
        project_domain_name='default',
        project_name='admin',    # for project's scoping, mandatory for service
                                 # catalog, see [2].
        region_name='RegionOne',
        user_domain_id='default',
        user_domain_name='default',
        username='admin')

    LOG.info("Authentication plugin %s" % cloud)
    return cloud


def make_account(identity, users):
    # Make new project
    project_name = "project-%s" % '-'.join(u for u in users)
    project = identity.find_project(project_name)

    if not project:
        project = identity.create_project(
            domain_id='default',
            parent_id='default',
            name=project_name,
            description="Project of %s." % ', '.join(u for u in users))

    LOG.info("Project %s" % project)

    for user_name in users:
        # Create users
        user = identity.find_user(user_name)

        if not user:
            user = identity.create_user(
                domain_id='default', name=user_name, password="os-imt")

        LOG.info("User %s" % user)

        # Assign to member, heat role
        for r in ["member", "heat_stack_owner"]:
            role = identity.find_role(r)
            LOG.info("Role %s" % role)

            identity.assign_project_role_to_user(project, user, role)

    return project


def make_private_net(net, project, enos_env):
    # Make private net
    # https://docs.openstack.org/openstacksdk/latest/user/resources/network/v2/network.html#openstack.network.v2.network.Network
    private_net = net.find_network("private", project_id=project.id)

    if not private_net:
        private_net = net.create_network(
            name="private",
            project_id=project.id,
            provider_network_type="vxlan")

    LOG.info("Private net %s" % private_net)

    # Make subnet
    # https://docs.openstack.org/openstacksdk/latest/user/resources/network/v2/subnet.html#openstack.network.v2.subnet.Subnet
    private_snet = net.find_subnet("private-subnet", network_id=private_net.id)

    if not private_snet:
        private_snet = net.create_subnet(
            name="private-subnet",
            network_id=private_net.id,
            project_id=project.id,
            ip_version=4,
            is_dhcp_enable=True,
            cidr="10.0.0.0/24",
            gateway_ip="10.0.0.1",
            allocation_pools=[{"start": "10.0.0.2", "end": "10.0.0.254"}],
            dns_nameservers=[enos_env['networks'][0]['dns'], "8.8.8.8"])

    LOG.info("Private subnet %s" % private_snet)

    return private_snet


def make_router(net, project, priv_snet):
    # Get public net and router if any
    public_net  = net.find_network("public", ignore_missing=False)
    public_snet = net.find_subnet("public-subnet", ignore_missing=False)
    router = net.find_router("router", project_id=project.id)


    if not router:
        router = net.create_router(
            name="router",
            project_id=project.id)

        # TODO: Add public gateway with `add_gateway_to_router`
        #
        # The following python code doesn't work and I don't know why:
        #
        # > res = net.add_gateway_to_router(
        # >     router,
        # >     network_id=public_net.id,
        # >     enable_snat=True,
        # >     external_fixed_ips=[{'subnet_id': public_snet.id,}])
        #
        # But the following CLI is OK:
        # $ openstack router set {router.id} --external-gateway {public_net.name}
        #
        # So I resume myself to write the next code based on
        # python-openstackclient [1]
        #
        # [1] https://github.com/openstack/python-openstackclient/blob/70ab3f9dd56a638cdff516ca85baa5ebd64c888b/openstackclient/network/v2/router.py#L636-L658
        res = net.update_router(
            router,
            external_gateway_info={
                'network_id':public_net.id,
                'enable_snat':True,
                'external_fixed_ips':[{'subnet_id': public_snet.id,}]
            })
        LOG.info("Ext gateway %s" % res)

        res = net.add_interface_to_router(router, subnet_id=priv_snet.id)
        LOG.info("Res net %s" % res)


def make_sec_group_rule(net, project):
    # Delete default security group rule
    sgrs = [sgr for sgr in net.security_group_rules()
                if sgr.project_id == project.id]
    for sgr in sgrs:
        net.delete_security_group_rule(sgr)
        LOG.info("Delete sgr %s" % sgr)

    # Find the sec group for this project
    sg_default = net.find_security_group("default", project_id=project.id)

    # Let all traffic goes in/out
    protocols = ["icmp", "udp", "tcp"]
    directions = ["ingress", "egress"]
    crit = [(p, d) for p in protocols for d in directions]

    for (p, d) in crit:
        sgr = net.create_security_group_rule(
            direction=d,
            ether_type="IPv4",
            port_range_min=None if p == "icmp" else 1,
            port_range_max=None if p == "icmp" else 65535,
            project_id=project.id,
            protocol=p,
            remote_ip_prefix="0.0.0.0/0",
            security_group_id=sg_default.id)

        LOG.info("New sgr %s" % sgr)


def make_flavors(cpt):
    f_mini = cpt.find_flavor('m1.mini')

    if not f_mini:
        f_mini = cpt.create_flavor(
            name='m1.mini',
            disk=5,
            is_public=True,
            ram=2048,
            vcpus=2,
            swap=1024)

    LOG.info("Flavor %s" % f_mini)

# TODO: add debian 10 image


# Main

enos_env = install_os()
cloud = make_cloud(f"http://{enos_env['config']['vip']}:35357/v3")
for team in TEAMS:
    project = make_account(cloud.identity, team)
    priv_snet = make_private_net(cloud.network, project, enos_env)
    priv_net = make_router(cloud.network, project, priv_snet)
    make_sec_group_rule(cloud.network, project)
    make_flavors(cloud.compute)
