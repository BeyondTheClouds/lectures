# $ pipenv run python setup.py  # thanks to Pipfile > scripts > setup-aio
import logging
import socket

from enoslib.types import Host, Roles

from enoslib.api import (play_on, ensure_python3)
from enoslib.infra.enos_g5k.provider import G5k
from enoslib.infra.enos_g5k.configuration import (Configuration,
                                                  NetworkConfiguration,
                                                  MachineConfiguration,)


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


def make_conf(testing=True) -> Configuration:
    conf = {
        "reservation": "2020-11-09 07:00:01",
        "walltime": "35:59:38",
        "job_name": "imta-fila3-os",
        "env_name": "ubuntu2004-x64-min",
        "resources": {
            "networks": [
                {
                    "id": "net",
                    "type": "prod",
                    "roles": ["network_interface"],
                    "site": "rennes",
                },
                # Keep this for future work, for a deployment
                # based OpenStack.
                # {
                #     # Note: *NEVER* assigns this to a machine!
                #     "id": "net_ext",
                #     "type": "slash_22",
                #     "roles": ["neutron_external_interface"],
                #     "site": "rennes",
                # },
            ],
            "machines": [
                {
                    "roles": ["OpenStack"],
                    "cluster": "paravance",
                    "nodes": 1,
                    "primary_network": "net",
                    "secondary_networks": [ ],
                }
            ],
        }
    }

    # conf = (Configuration.from_settings(
    #            reservation="2020-11-09 07:00:01",
    #            walltime="35:59:58",
    #            job_name="os-imt-aio",
    #            job_type="deploy",
    #            env_name="ubuntu2004-x64-min")
    #         .add_network_conf(project_net)
    #         # .add_network_conf(external_net)
    #         .add_machine(**os.__dict__))

    if testing:
        del(conf["reservation"])
        conf["walltime"] = "05:00:00"
        conf["job_name"] = "imta-fil3-os-test"
        conf["resources"]["machines"][0]["nodes"] = 1

    return Configuration.from_dictionnary(conf)


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

        # IP Forwarding
        p.raw('sysctl -w net.ipv4.ip_forward=1')

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


if __name__ == "__main__":
    # Claim the resources
    infra = G5k(make_conf(testing=True))
    roles, networks = infra.init(force_deploy=False)

    # Provision machines
    provision(roles)

    # Display subnet
    subnet = [n for n in networks
                if "neutron_external_interface" in n["roles"]]
    print(subnet)

    # Assign machines
    print("Lab machine assignations:")
    addrs = map(get_addr, roles["OpenStack"])
    for (team, addr) in zip(TEAMS, addrs):
        team_members_str = ', '.join(m for m in team)
        print(f"- {team_members_str} :: ~{addr}~")

    # # Destroy
    # infra.destroy()
