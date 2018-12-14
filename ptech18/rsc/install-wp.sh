#!/usr/bin/env bash
#
# Install and configure Apache to serve Wordpress for Debian 9.

# Fix DNS resolution
echo "" >> /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# Parameters
DB_NAME=wordpress
DB_USER=silr
DB_PASSWORD=silr
DB_HOST=<TODO>

apt-get update -y
apt-get upgrade -y
apt-get install -q -y --force-yes wordpress apache2 curl

cat << EOF > /etc/apache2/sites-available/wp.conf
Alias /wp/wp-content /var/lib/wordpress/wp-content
Alias /wp /usr/share/wordpress
<Directory /usr/share/wordpress>
    Options FollowSymLinks
    AllowOverride Limit Options FileInfo
    DirectoryIndex index.php
    Require all granted
</Directory>
<Directory /var/lib/wordpress/wp-content>
    Options FollowSymLinks
    Require all granted
</Directory>
EOF

a2ensite wp
service apache2 reload

cat << EOF > /etc/wordpress/config-default.php
<?php
define('DB_NAME', '${DB_NAME}');
define('DB_USER', '${DB_USER}');
define('DB_PASSWORD', '${DB_PASSWORD}');
define('DB_HOST', '${DB_HOST}');
define('WP_CONTENT_DIR', '/var/lib/wordpress/wp-content');
?>
EOF
