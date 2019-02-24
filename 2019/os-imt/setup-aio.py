# $ pipenv run setup-aio  # thanks to Pipfile > scripts > setup-aio
import logging
import os

from enoslib.api import generate_inventory, emulate_network, validate_network
from enoslib.infra.enos_g5k import api
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_g5k.configuration import *


logging.basicConfig(level=logging.DEBUG)
LOG   = logging.getLogger(__name__)
TEAMS = [
    ("ronana", "alebre")
]

# "alacour"
# "amanue"
# "aqueiros"
# "blemee"
# "bpeyresaube"
# "cg"
# "damarti"
# "eguerin"
# "jfreta"
# "kforest"
# "launea"
# "lparis"
# "maguyo"
# "mmaheo"
# "mmainchai"
# "mnoritop"
# "nfrayssinhe"
# "nguegan"
# "qeud"
# "rgrison"
# "rlao"
# "sedahmani"
# "tandrieu"
# "thlailler"
# "vjorda"

def make_conf(testing=True):
    prod_net = NetworkConfiguration(
        id="net", type="prod", roles=["net"], site="nantes")

    os = MachineConfiguration(
        roles=["openstack"],
        cluster="ecotype",
        nodes=2 if testing else 14,
        primary_network=prod_net)

    conf = None
    if testing:
        conf = (Configuration.from_settings(
                    walltime="60:00:00",
                    job_name="os-imt-aio-test",
                    env_name="ubuntu1804-x64-min",
                    oar_site="nantes")
                .add_network_conf(prod_net)
                .add_machine(**os.__dict__))
    else:
        conf = (Configuration.from_settings(
                    reservation="2019-02-25 07:00:01",
                    walltime="62:00:00",
                    job_name="os-imt-aio",
                    env_name="ubuntu1804-x64-min",
                    oar_site="nantes")
                .add_network_conf(prod_net)
                .add_machine(**os.__dict__))

    conf.finalize()
    return conf

def get_node_addresses(roles):
    return sorted(set([n.address for nodes in roles.values()
                                 for n in nodes]))

def bootstrap(roles):
    nodes = get_node_addresses(roles)
    cmd   = lambda cmd: api.exec_command_on_nodes(nodes, cmd, cmd)

    # Install the bare necessities
    packages = [ 'htop', 'python', 'vim']
    cmd("apt-get update && apt-get -y --force-yes install %s" % ' '.join(packages))

    # Setup ssh for root w/ password
    cmd('echo "root:os-imt" | chpasswd')
    cmd('echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config')
    cmd('echo "PermitRootLogin yes"        >> /etc/ssh/sshd_config')
    cmd('systemctl restart ssh')

    return nodes

# Claim the resources and do the scaffolding
roles, networks = G5k(make_conf(testing=True)).init()
nodes = bootstrap(roles)

print("Node affectation:")
for (team, node) in zip(TEAMS, nodes):
    print("  %s ⇒ %s" % (team, node))
