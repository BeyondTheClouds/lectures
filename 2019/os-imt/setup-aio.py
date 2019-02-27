# $ pipenv run setup-aio  # thanks to Pipfile > scripts > setup-aio
import logging
import os
import socket

from enoslib.api import generate_inventory, emulate_network, validate_network
from enoslib.infra.enos_g5k import api
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_g5k.configuration import *


logging.basicConfig(level=logging.DEBUG)
LOG   = logging.getLogger(__name__)
TEAMS = [
    ("ronana",      "alebre"),
    ("alacour",     "mnoritop"),
    ("aqueiros",    "rlao"),
    ("blemee",      "launea"),
    ("bpeyresaube", "nguegan"),
    ("cg",          "mmainchai"),
    ("damarti",     "eguerin"),
    ("jfreta",      "vjorda"),
    ("kforest",     "maguyo"),
    ("lparis",      "sedahmani"),
    ("mmaheo",      "qeud"),
    ("nfrayssinhe", "thlailler"),
    ("rgrison",     "tandrieu"),
]

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

def get_nodes(roles):
    return sorted(set([n.address for nodes in roles.values()
                                 for n in nodes]))

def bootstrap(roles):
    nodes = get_nodes(roles)
    cmd   = lambda cmd: api.exec_command_on_nodes(nodes, cmd, cmd)

    # Install the bare necessities
    packages = [ 'silversearcher-ag', 'curl', 'htop', 'python', 'tcpdump', 'vim']
    cmd('apt update')
    cmd("apt install -y --force-yes %s" % ' '.join(packages))

    # Setup ssh for root w/ password
    cmd('echo "root:os-imt" | chpasswd')
    cmd('echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config')
    cmd('echo "PermitRootLogin yes"        >> /etc/ssh/sshd_config')
    cmd('systemctl restart ssh')

    # Put /snap/bin in PATH
    cmd('echo "export PATH=/snap/bin:${PATH}" >> /root/.bashrc')

    # Disable ip forwarding (for pedagogical purpose)
    cmd('sudo sysctl -w net.ipv4.ip_forward=0')

    return nodes

# Claim the resources and do the scaffolding
roles, networks = G5k(make_conf(testing=False)).init(force_deploy=False)
nodes = bootstrap(roles)
addrs = map(socket.gethostbyname, nodes)

print("Lab machine assignations:")
for (team, addr) in zip(TEAMS, addrs):
    print("- %s :: ~%s~" % (', '.join(p for p in team), addr))
