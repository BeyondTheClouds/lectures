#!/usr/bin/env bash
# Fix DNS resolution
echo "" >> /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# Install figlet and lolcat
apt update
apt install -y figlet lolcat
