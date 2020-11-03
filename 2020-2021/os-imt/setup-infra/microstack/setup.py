# $ pipenv run python setup.py  # thanks to Pipfile > scripts > setup-aio
import logging
import socket

from enoslib.types import Host, Roles

from enoslib.api import (play_on, ensure_python3)
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_g5k.configuration import (Configuration,
                                                  NetworkConfiguration,
                                                  MachineConfiguration, )


logging.basicConfig(level=logging.DEBUG)
LOG = logging.getLogger(__name__)
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


def get_addr(h: Host) -> str:
    'Returns the address of a Host `h`'
    try:
        return socket.gethostbyname(h.address)
    except socket.gaierror:
        return h.address


# Get node on funk, for a specific set on ecotype nodes:
# funk -m date -s "2020-02-03 12:01:00" -r ecotype:15 -w 60:00:00 -o "-t deploy -p \"host in (
#   'ecotype-1.nantes.grid5000.fr', 'ecotype-2.nantes.grid5000.fr', 'ecotype-3.nantes.grid5000.fr',
#   'ecotype-4.nantes.grid5000.fr', 'ecotype-5.nantes.grid5000.fr', 'ecotype-6.nantes.grid5000.fr',
#   'ecotype-7.nantes.grid5000.fr', 'ecotype-8.nantes.grid5000.fr', 'ecotype-9.nantes.grid5000.fr',
#   'ecotype-10.nantes.grid5000.fr', 'ecotype-11.nantes.grid5000.fr', 'ecotype-12.nantes.grid5000.fr',
#   'ecotype-13.nantes.grid5000.fr', 'ecotype-14.nantes.grid5000.fr', 'ecotype-15.nantes.grid5000.fr',
#   'ecotype-16.nantes.grid5000.fr', 'ecotype-17.nantes.grid5000.fr')\"" -j "os-imt-aio" --yes
def make_conf(testing=True):
    # Configure the expected infrastructure for G5k
    kavlan = NetworkConfiguration(
        id="net",
        type="kavlan",
        roles=["network_interface"],
        site="rennes")

    prod_net = NetworkConfiguration(
        id="net_ext",
        type="prod",
        roles=["neutron_external_interface"],
        site="rennes")

    os = MachineConfiguration(
        roles=["OpenStack"],
        cluster="paravance",
        nodes=15,
        # primary_network=kavlan,
        # secondary_networks=[prod_net])
        primary_network=prod_net,
        secondary_networks=[])

    conf = (Configuration.from_settings(
               reservation="2020-11-09 07:00:01",
               walltime="35:59:58",
               job_name="os-imt-aio",
               env_name="ubuntu2004-x64-min")
            # .add_network_conf(kavlan)
            .add_network_conf(prod_net)
            .add_machine(**os.__dict__))

    # Override configuration for testing the lab
    if testing:
        conf.reservation = None
        conf.walltime = "09:00:00"
        conf.job_name = "imta-fila3-os"
        conf.machines[0].nodes = 2

    conf.finalize()
    return conf


def provision(rs: Roles):
    ensure_python3(roles=rs)

    with play_on(roles=rs, pattern_hosts="OpenStack") as p:
        # Install the bare necessities
        p.apt(pkg=['bat', 'curl', 'htop', 'tcpdump', 'lynx', 'vim', 'kmod'],
              update_cache=True)
        # Workaround ripgrep error
        # https://bugs.launchpad.net/ubuntu/+source/rust-bat/+bug/1868517
        p.raw('apt download ripgrep')
        p.raw('dpkg --force-overwrite -i ripgrep*.deb')

        # Setup ssh for root w/ password
        p.raw('echo "root:os-imt" | chpasswd')
        p.blockinfile(path='/etc/ssh/sshd_config',
                      block='''
                      PasswordAuthentication yes
                      PermitRootLogin yes
                      ''')
        p.systemd(name='ssh', state='restarted')

        # Enhance default bash
        for l in ('. /etc/bash_completion',         # Offer bash completion
                  'export PATH=/snap/bin:${PATH}',  # Put /snap/bin in PATH
                  'alias cat="bat --style=plain"',    # Better cat
                  'alias fgrep="rg --fixed-strings"'  # Better fgrep
                  ) :
            p.lineinfile(path='/root/.bashrc', line=l)


# Claim the resources
infra = G5k(make_conf(testing=True))
roles, networks = infra.init(force_deploy=False)

# Provision machines
provision(roles)

# Assign machines
print("Lab machine assignations:")
addrs = map(get_addr, roles["OpenStack"])
for (team, addr) in zip(TEAMS, addrs):
    team_members_str = ', '.join(m for m in team)
    print(f"- {team_members_str} :: ~{addr}~")

# # Destroy
# infra.destroy()
