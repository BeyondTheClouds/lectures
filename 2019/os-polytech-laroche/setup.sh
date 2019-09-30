#!/usr/bin/env bash
# Install the bare necessities
set -o errexit
set -o xtrace

apt install -y curl tcpdump kmod
snap install openstackclients --classic --candidate

# Make nova use qemu instead of qemu-kvm
# i.e,:
# > [libvirt]
# > virt_type = kvm             # rewrite to qemu
# > cpu_mode = host-passthrough # rewrite to host-model
NOVA_HYPERV_CONF=/var/snap/microstack/common/etc/nova/nova.conf.d/hypervisor.conf
sed -i 's|virt_type.\+|virt_type = qemu|' $NOVA_HYPERV_CONF
sed -i 's|cpu_mode.\+|cpu_mode = host-model|' $NOVA_HYPERV_CONF
snap restart microstack.nova-compute

# Workaround to modify openstack configurartion files (the `--classic`
# mode doesn't help here): Setup an overlay and change horizon conf to
# make it listen on any host
OV_NAME="snap-microstack-overlay"
if ! fgrep -q "$OV_NAME on" <<< $(mount -l)
then
    HORIZON=/snap/microstack/current/lib/python2.7/site-packages/openstack_dashboard/local
    UPP_BIN="$(mktemp -d)"
    WORK_BIN="$(mktemp -d)"

    mount --types overlay --options \
        lowerdir=$HORIZON,upperdir=$UPP_BIN,workdir=$WORK_BIN \
        $OV_NAME $HORIZON

    echo "ALLOWED_HOSTS = ['*']" >> $HORIZON/local_settings.py
    snap restart microstack.horizon-uwsgi
fi

# Put snap openstackclients into the path.
export PATH=/snap/bin:$PATH

set +o xtrace
sysctl -w net.ipv4.ip_forward=0 > /dev/null
extcidr=10.20.20.0/24  # find it with `sudo iptables -t nat -L`
iptables -w -t nat -D POSTROUTING -s $extcidr ! -d $extcidr -j MASQUERADE > /dev/null
