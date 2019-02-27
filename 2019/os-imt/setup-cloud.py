import logging
import os
import socket
import yaml

import openstack


logging.basicConfig(level=logging.INFO)
LOG   = logging.getLogger(__name__)
TEAMS = [
    ("ronana",      "alebre"),
    ("alacour",     "mnoritop"),
    ("aqueiros",    "rlao"),
    ("blemee",      "launea"),
    ("bpeyresaube", "nguegan"),
    ("cg",          "mmainchai"),
    ("damartin",    "eguerin"),
    ("jfreta",      "vjorda"),
    ("kforest",     "maguyo"),
    ("lparis",      "sedahmani"),
    ("mmaheo",      "qeud"),
    ("nfrayssinhe", "thlailler"),
    ("rgrison",     "tandrieu"),
]

ENOS_ENV = None
# with f as open("/home/rcherrueau/enos-5.0.1/current/env", "r"):
#     ENOS_ENV = yaml.load(f)

ENOS_ENV = {'networks': [
    {
        "cidr": "10.16.0.0/18",
        "dns": "172.16.111.118",
        "end": "10.16.61.251",
        "gateway": "10.16.63.254",
        "roles": ["network_interface"],
        "start": "10.16.26.0",
    },
    {
        "cidr": "10.16.64.0/18",
        "dns": "172.16.111.118",
        "end": "10.16.125.255",
        "gateway": "10.16.127.254",
        "roles": ["neutron_external_interface"],
        "start": "10.16.90.0",
    }
    ]}

def make_cloud(cloud_auth_url):
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
    LOG.info("New authentication for %s with admin" % cloud_auth_url)
    cloud = openstack.connect(
        # Use Admin credential -- Same everywhere in this PoC!
        auth_url="%s" % cloud_auth_url,
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


def make_private_net(net, project):
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
            dns_nameservers=[ENOS_ENV['networks'][0]['dns'], "8.8.8.8"])

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

        # XXX: Add public gateway
        # res = net.add_gateway_to_router(
        #     router,
        #     network_id=public_net.id,
        #     enable_snat=True,
        #     external_fixed_ips=[{'subnet_id': public_snet.id,}])
        # LOG.info("Res net %s" % res)
        LOG.error("openstack router set %s --external-gateway %s" % (router.id , public_net.name))

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
        sgr_name = "%s-%s" % (p,d)
        if not net.find_security_group_rule(sgr_name, project_id=project.id):
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


cloud = make_cloud("http://10.16.61.255:35357/v3")
project = make_account(cloud.identity, TEAMS[0])
priv_snet = make_private_net(cloud.network, project)
priv_net = make_router(cloud.network, project, priv_snet)
make_sec_group_rule(cloud.network, project)
# pub_net = make_public_net(cloud.network, project)
