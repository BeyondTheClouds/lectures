#!/usr/bin/env bash
set -o errexit
set -o xtrace

. admin-openrc.sh

# Delete VMs
for vm in $(openstack server list -c ID -f value); do \
  echo "Deleting ${vm}..."; \
  openstack server delete "${vm}"; \
done

# Releasing floating IPs
for ip in $(openstack floating ip list -c "Floating IP Address" -f value); do \
  echo "Releasing ${ip}..."; \
  openstack floating ip delete "${ip}"; \
done

sudo snap remove --purge openstackclients
sudo snap remove --purge microstack
