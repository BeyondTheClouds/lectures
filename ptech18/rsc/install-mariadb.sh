#!/usr/bin/env bash
#
# Install and configure MariaDB for Debian 9.

# Fix DNS resolution
echo "" >> /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# Parameters
DB_ROOTPASSWORD=root
DB_NAME=wordpress    # Wordpress DB name
DB_USER=silr         # Wordpress DB user
DB_PASSWORD=silr     # Wordpress DB pass

# Install MariaDB
apt update -q
apt install -q -y mariadb-server mariadb-client

# Next line stops mysql install from popping up request for root password
export DEBIAN_FRONTEND=noninteractive
sed -i 's/127.0.0.1/0.0.0.0/' /etc/mysql/mariadb.conf.d/50-server.cnf
systemctl restart mysql

# Setup MySQL root password and create a user and add remote privs to app subnet
mysqladmin -u root password ${DB_ROOTPASSWORD}

# Create the wordpress database
cat << EOSQL | mysql -u root --password=${DB_ROOTPASSWORD}
FLUSH PRIVILEGES;
CREATE USER '${DB_USER}'@'localhost';
CREATE DATABASE ${DB_NAME};
SET PASSWORD FOR '${DB_USER}'@'localhost'=PASSWORD("${DB_PASSWORD}");
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER '${DB_USER}'@'%';
SET PASSWORD FOR '${DB_USER}'@'%'=PASSWORD("${DB_PASSWORD}");
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASSWORD}';
EOSQL
