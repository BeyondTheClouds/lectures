#!/usr/bin/env bash
set -o errexit
set -o xtrace

# Install the bare necessities
apt install -y curl tcpdump kmod
snap install openstackclients --classic --candidate

# Initialize  OpenStack
microstack.init --auto

# Put Identity endpoint in the `microstack` region.
#
# Identity endpoint is put in `None` region. This makes it unavailable
# from a client in the default `microstack` region (as student).
# $ sudo microstack.openstack endpoint list --service Identity
# > +--------+--------------+--------------+-----------+----------------------------+
# > | Region | Service Name | Service Type | Interface | URL                        |
# > +--------+--------------+--------------+-----------+----------------------------+
# > | None   | keystone     | identity     | admin     | http://10.20.20.1:5000/v3/ |
# > | None   | keystone     | identity     | internal  | http://10.20.20.1:5000/v3/ |
# > | None   | keystone     | identity     | public    | http://10.20.20.1:5000/v3/ |
# > +--------+--------------+--------------+-----------+----------------------------+
for id in $(microstack.openstack endpoint list --service identity -c ID -f value)
do
    microstack.openstack endpoint set --region microstack "${id}"
done

# Identity endpoint is unavailable after init for whatever reason.
# > microstack.openstack endpoint list
# endpoint for identity service in microstack region not found
# microstack.keystone-manage bootstrap \
#         --bootstrap-username admin \
#         --bootstrap-password keystone \
#         --bootstrap-project-name admin \
#         --bootstrap-role-name admin \
#         --bootstrap-service-name keystone \
#         --bootstrap-region-id microstack \
#         --bootstrap-admin-url "http://10.20.20.1:5000/v3/" \
#         --bootstrap-public-url "http://10.20.20.1:5000/v3/"

# Make nova use qemu instead of qemu-kvm
# i.e,:
# > [libvirt]
# > virt_type = kvm             # rewrite to qemu
# > cpu_mode = host-passthrough # rewrite to host-model
NOVA_HYPERV_CONF=/var/snap/microstack/common/etc/nova/nova.conf.d/hypervisor.conf
sed -i 's|virt_type.\+|virt_type = qemu|' $NOVA_HYPERV_CONF
sed -i 's|cpu_mode.\+|cpu_mode = host-model|' $NOVA_HYPERV_CONF
snap restart microstack.nova-compute

# Change horizon conf to make it listen on any host
HORIZON_CONF=/var/snap/microstack/common/etc/horizon/local_settings.d/_09_rcherr_horizon_tweaks.py
echo "# Allow connections from any hosts" > $HORIZON_CONF
echo "ALLOWED_HOSTS = ['*']" > $HORIZON_CONF
snap restart microstack.horizon-uwsgi

# Put snap openstackclients into the path.
export PATH=/snap/bin:$PATH

set +o xtrace
# Remove icmp and tcp security group rules of `microstack.init --auto`
for rule in $(microstack.openstack security group rule list --protocol icmp -c ID -f value)
do
    microstack.openstack security group rule delete "${rule}"
done
for rule in $(microstack.openstack security group rule list --protocol tcp -c ID -f value)
do
    microstack.openstack security group rule delete "${rule}"
done

# Undo the external network setup of `microstack.init --auto`
sysctl -w net.ipv4.ip_forward=0 > /dev/null
extcidr=10.20.20.0/24  # find it with `sudo iptables -t nat -L`
iptables -w -t nat -D POSTROUTING -s $extcidr ! -d $extcidr -j MASQUERADE > /dev/null
set -o xtrace
