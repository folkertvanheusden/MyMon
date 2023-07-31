what it is
----------

MyMon is a really simpel monitoring application.
It can (using Nagios check_* programs) do all kinds of checks.
Performance data (from MyMon but also as returned by the check
programs) will be inserted into an InfluxDB.


how to implement
----------------

* create a database in mysql

* insert the database schema in the newly created mysql db
  mysql -u user -ppassword newdb < schema.sql

* set access rights:
  grant insert,select,update on newdb.* to user@localhost
    identified by 'password';
  flush privileges;

* create a database in influxdb

* copy the settings into configuration.py

* using 'cli.py' you can add a checks to the system, e.g.:
  * ./cli.py add-contact user@domain.com
  * ./cli.py add-host some.server.tld
  * ./cli.py add-local-check 'check_ssl_cert' '/usr/lib/nagios/plugins/check_ssl_cert -H %host%'
  * ./cli.py add-check local 300 some.server.tld user@domain.com check_ssl_cert

  Run cli.py without parameters to show a list of commands
  and their parameters.


how to run
----------

./scheduler.py


license
-------

Published under the MIT license by
Folkert van Heusden <mail@vanheusden.com>.
