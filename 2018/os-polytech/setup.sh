#!/usr/bin/env bash
sudo apt update
sudo apt install -y curl tcpdump
sudo snap install microstack --classic --edge
sudo snap install openstackclients --classic --edge
