#!/usr/bin/env bash
openstack server create --wait --image debian-9 \
  --flavor m1.mini --network test \
  --key-name admin \
  --user-data ./install-mariadb.sh \
  wordpress-db

wait_cloudinit wordpress-db

WP_APP_FIP=$(openstack floating ip create -c floating_ip_address -f value external)

sed -i '13s|.*|DB_HOST="'$(openstack server show wordpress-db -c addresses -f value | sed -Er "s/test=//g")'"|' ./install-wp.sh

openstack server create --wait --image debian-9 \
  --flavor m1.mini --network test \
  --key-name admin \
  --user-data ./install-wp.sh \
  wordpress-app

wait_cloudinit wordpress-app

openstack server add floating ip wordpress-app "${WP_APP_FIP}"
