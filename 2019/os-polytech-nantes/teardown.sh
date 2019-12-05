#!/usr/bin/env bash
set -o xtrace

# Undo the external network setup of `microstack.init --auto`
sysctl -w net.ipv4.ip_forward=0 > /dev/null
extcidr=10.20.20.0/24  # find it with `sudo iptables -t nat -L`
iptables -w -t nat -D POSTROUTING -s $extcidr ! -d $extcidr -j MASQUERADE > /dev/null

sudo apt purge --yes --quiet --autoremove heat-api heat-api-cfn heat-engine

sudo snap remove --purge openstackclients
sudo snap remove --purge microstack
