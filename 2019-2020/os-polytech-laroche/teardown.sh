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

sudo snap remove openstackclients
sudo snap remove microstack
sudo sysctl -w net.ipv4.ip_forward=0
read -p 'Ip of your host machine (to remove iptables SNAT): '  IP_LAB
sudo iptables -t nat -A POSTROUTING ! -d 10.20.20.0/24 -o eth0 -j SNAT --to-source ${IP_LAB}
