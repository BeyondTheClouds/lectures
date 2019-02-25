#!/usr/bin/env bash
sudo snap install microstack --classic --edge
sudo snap install openstackclients --classic --edge

# Make nova use kvm instead of qemu by deleting qemu specific conf
sed -i '7,$d' /var/snap/microstack/common/etc/nova/nova.conf.d/hypervisor.conf
snap restart microstack.nova-compute

# Setup overlay and allow horizon to listen on any host
UPP_BIN="$(mktemp -d)"
WORK_BIN="$(mktemp -d)"
HORIZON=/snap/microstack/current/lib/python2.7/site-packages/openstack_dashboard/local

mount --types overlay --options \
  lowerdir=$HORIZON,upperdir=$UPP_BIN,workdir=$WORK_BIN \
  "snap-microstack-overlay" $HORIZON

sed -i '39s/.*/ALLOWED_HOSTS = ['*']/' $HORIZON/local_settings.py
snap restart microstack.horizon-uwsgi
