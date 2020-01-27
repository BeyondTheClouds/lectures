#!/usr/bin/env bash
function wait_contextualization {
  # Get the log
  local vm="$1"
  local console_log=$(openstack console log show --lines=20 "${vm}")

  # Loop till cloud-init finished
  local cloudinit_end_rx="Cloud-init v\. .\+ finished"
  echo "Waiting for cloud-init to finish..."
  echo "Current status is:"
  while ! echo "${console_log}"|grep -q "${cloudinit_end_rx}"
  do
      echo "${console_log}"
      sleep 5

      # Compute the new console log before clearing
      # so the screen is not blank for two long.
      local new_console_log=$(openstack console log show --lines=20 "${vm}")

      # Clear the screen (`cuu1` move cursor up by one line, `el`
      # clear the line)
      while read -r line; do
          tput cuu1; tput el
      done <<< "${console_log}"

      console_log="${new_console_log}"
  done

  # cloud-init finished
  echo "${console_log}"|grep "${CLOUDINIT_END_RX}"
}

openstack server create --wait --image debian-9 \
  --flavor m1.mini --network test \
  --key-name admin \
  --user-data ./rsc/install-mariadb.sh \
  wordpress-db

wait_contextualization wordpress-db

sed -i '13s|.*|DB_HOST="'$(openstack server show wordpress-db -c addresses -f value | sed -Er "s/test=//g")'"|' ./rsc/install-wp.sh

openstack server create --wait --image debian-9 \
  --flavor m1.mini --network test \
  --key-name admin \
  --user-data ./rsc/install-wp.sh \
  wordpress-app

wait_contextualization wordpress-app

WP_APP_FIP=$(openstack floating ip create -c floating_ip_address -f value external)

openstack server add floating ip wordpress-app "${WP_APP_FIP}"
