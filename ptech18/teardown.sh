#!/usr/bin/env bash
for vm in $(openstack server list -c Name -f value); do \
  echo "Deleting ${vm}..."; \
  openstack server delete "${vm}"; \
done

for ip in $(openstack floating ip list -c "Floating IP Address" -f value); do \
  echo "Deleting ${ip}..."; \
  openstack floating ip delete "${ip}"; \
done

sudo snap remove openstackclients
sudo snap remove microstack
