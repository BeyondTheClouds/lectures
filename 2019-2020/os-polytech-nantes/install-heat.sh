#!/usr/bin/env bash
set -o errexit
set -o xtrace

# Create the Heat database
cat << EOSQL | sudo microstack.mysql
CREATE DATABASE heat;
GRANT ALL PRIVILEGES ON heat.* TO 'heat'@'localhost' IDENTIFIED BY 'HEAT_DBPASS';
GRANT ALL PRIVILEGES ON heat.* TO 'heat'@'%' IDENTIFIED BY 'HEAT_DBPASS';
EOSQL

# Create the service credentials
microstack.openstack user create --domain default --password HEAT_PASS heat
microstack.openstack role add --project service --user heat admin
microstack.openstack service create --name heat --description "Orchestration" orchestration
microstack.openstack endpoint create --region microstack orchestration public http://10.20.20.1:8004/v1/%\(tenant_id\)s
microstack.openstack endpoint create --region microstack orchestration internal http://10.20.20.1:8004/v1/%\(tenant_id\)s
microstack.openstack endpoint create --region microstack orchestration admin http://10.20.20.1:8004/v1/%\(tenant_id\)s
microstack.openstack service create --name heat-cfn --description "Orchestration"  cloudformation
microstack.openstack endpoint create --region microstack cloudformation public http://10.20.20.1:8000/v1
microstack.openstack endpoint create --region microstack cloudformation internal http://10.20.20.1:8000/v1
microstack.openstack endpoint create --region microstack cloudformation admin http://10.20.20.1:8000/v1

# Create the Heat domain
microstack.openstack domain create heat
microstack.openstack user create --domain heat --password HEAT_DOMAIN_PASS heat_domain_admin
microstack.openstack role add --domain heat --user-domain heat --user heat_domain_admin admin
microstack.openstack role create heat_stack_owner
microstack.openstack role add --project admin --user admin heat_stack_owner
microstack.openstack role create heat_stack_user

# Install OpenStack Heat
apt update
apt install -y heat-api heat-api-cfn heat-engine crudini

# Configure Heat template
crudini --set /etc/heat/heat.conf database connection "mysql+pymysql://heat:HEAT_DBPASS@10.20.20.1/heat"
crudini --set /etc/heat/heat.conf DEFAULT transport_url "rabbit://openstack:rabbitmq@10.20.20.1"
crudini --set /etc/heat/heat.conf DEFAULT heat_metadata_server_url "http://10.20.20.1:8000"
crudini --set /etc/heat/heat.conf DEFAULT heat_waitcondition_server_url "http://10.20.20.1:8000/v1/waitcondition"
crudini --set /etc/heat/heat.conf DEFAULT stack_domain_admin "heat_domain_admin"
crudini --set /etc/heat/heat.conf DEFAULT stack_domain_admin_password "HEAT_DOMAIN_PASS"
crudini --set /etc/heat/heat.conf DEFAULT stack_user_domain_name "heat"
crudini --set /etc/heat/heat.conf keystone_authtoken www_authenticate_uri "http://10.20.20.1:5000"
crudini --set /etc/heat/heat.conf keystone_authtoken auth_url "http://10.20.20.1:5000"
crudini --set /etc/heat/heat.conf keystone_authtoken memcached_servers "10.20.20.1:11211"
crudini --set /etc/heat/heat.conf keystone_authtoken auth_type "password"
crudini --set /etc/heat/heat.conf keystone_authtoken project_domain_name "default"
crudini --set /etc/heat/heat.conf keystone_authtoken user_domain_name "default"
crudini --set /etc/heat/heat.conf keystone_authtoken project_name "service"
crudini --set /etc/heat/heat.conf keystone_authtoken username "heat"
crudini --set /etc/heat/heat.conf keystone_authtoken password "HEAT_PASS"
crudini --set /etc/heat/heat.conf trustee auth_type "password"
crudini --set /etc/heat/heat.conf trustee auth_url "http://10.20.20.1:5000"
crudini --set /etc/heat/heat.conf trustee username "heat"
crudini --set /etc/heat/heat.conf trustee password "HEAT_PASS"
crudini --set /etc/heat/heat.conf trustee user_domain_name "default"
crudini --set /etc/heat/heat.conf clients_keystone auth_uri "http://10.20.20.1:5000"

# Populate the Heat database
su -s /bin/sh -c "heat-manage db_sync" heat

# Restart the Heat services
systemctl restart heat-api heat-api-cfn heat-engine
