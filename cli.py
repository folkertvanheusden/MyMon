#! /usr/bin/python3

from configuration import *
import mysql.connector
import sys

dbh = mysql.connector.connect(host=db_host, user=db_user, password=db_pass, database=db_db)

def lookup(dbh, table, col, check_for):
    ch = dbh.cursor(dictionary=True)

    ch.execute('SELECT nr FROM ' + table + ' WHERE ' + col + '=%(check_for)s', { 'check_for' : check_for })

    row = ch.fetchone()

    ch.close()

    if row == None:
        return None

    return row['nr']

def list_table(dbh, table, columns):
    ch = dbh.cursor(dictionary=True)

    columns_str = ', '.join(columns)

    ch.execute('SELECT ' + columns_str + ' FROM ' + table + ' ORDER BY ' + columns_str)

    for row in ch.fetchall():
        col_vals = [row[col] for col in columns]

        print('\t'.join(col_vals))

    ch.close()

def list_checks(dbh):
    ch = dbh.cursor(dictionary=True)

    ch.execute('''
SELECT
    checks.type as type, `interval`, status, l.check_name AS name, hosts.host as host, contacts.email as email
FROM
    checks, check_local as l, hosts, contacts
WHERE
    l.nr=checks.check_nr AND hosts.nr=checks.host_nr AND contacts.nr=checks.contact_nr
UNION
SELECT
    checks.type as type, `interval`, status, r.check_name AS name, hosts.host as host, contacts.email as email
FROM
    checks, check_remote as r, hosts, contacts
WHERE
    r.nr=checks.check_nr AND hosts.nr=checks.host_nr AND contacts.nr=checks.contact_nr
''')

    for row in ch.fetchall():
        col_vals = [str(row[col]) for col in row]

        print('\t'.join(col_vals))

    ch.close()

ch = dbh.cursor(dictionary=True)

if len(sys.argv) < 2:
    print('Command missing')
    print()
    print()
    print('configure a locally running check:')
    print('\tadd-local-check "check-name" "check command-line"')
    print()
    print('add/list a host that can be checked:')
    print('\tadd-host "hostname"')
    print('\tlist-hosts')
    print()
    print('add/list a contact who will be alarmed when something goes wrong:')
    print('\tadd-contact "e-mail address"')
    print('\tlist-contacts')
    print()
    print('configure a check:')
    print('\tadd-check "local/remote" "check-interval" "hostname" "contact" "check-name"')
    print('\t- check-interval in seconds')
    print('\t- contact is the configured e-mail address (see add-contact)')
    print('\t- check-name is the configured check (see add-local-check)')
    print('\tlist-checks')
    print()
    print()
    sys.exit(1)

elif sys.argv[1] == 'add-host':
    ch.execute('INSERT INTO hosts(host) VALUES(%(host)s)', { 'host': sys.argv[2] })

elif sys.argv[1] == 'list-hosts':
    list_table(dbh, "hosts", ("host",))

elif sys.argv[1] == 'add-contact':
    ch.execute('INSERT INTO contacts(email) VALUES(%(email)s)', { 'email': sys.argv[2] })

elif sys.argv[1] == 'list-contacts':
    list_table(dbh, "contacts", ("email",))

elif sys.argv[1] == 'add-local-check':
    if len(sys.argv) != 4:
        print(f'Usage: {sys.argv[1]} "check-name" "check command-line"')

    else:
        ch.execute('INSERT INTO check_local(check_name, cmdline) VALUES(%(check_name)s, %(cmdline)s)', { 'check_name': sys.argv[2], 'cmdline': sys.argv[3] })

elif sys.argv[1] == 'list-local-checks':
    list_table(dbh, "check_local", ("check_name", "cmdline"))

elif sys.argv[1] == 'add-check':
    if len(sys.argv) != 7:
        print(f'Usage: {sys.argv[1]} "local/remote" "check-interval" "hostname" "contact" "check-name"')

    else:
        local_check = sys.argv[2] == 'local'

        if local_check == False:
            print('Currently only local checks are supported.')
            sys.exit(1)

        interval = int(sys.argv[3])

        if interval <= 0:
            print('The check-interval cannot be less than 1.')
            sys.exit(1)

        host_name = lookup(dbh, 'hosts', 'host', sys.argv[4])

        contact = lookup(dbh, 'contacts', 'email', sys.argv[5])

        check_nr = lookup(dbh, 'check_local' if local_check else 'check_remote', 'check_name', sys.argv[6])

        if host_name == None:
            print(f'Hostname "{host_name}" is not known, add using add-host')
            sys.exit(1)

        if contact == None:
            print(f'Contact "{contact}" is not known, add using add-contact')
            sys.exit(1)

        values = { 'type' : 'local' if local_check else 'remote',
                   'check_nr' : check_nr,
                   'interval' : interval,
                   'host_nr' : host_name,
                   'contact_nr' : contact
                   }

        ch.execute('INSERT INTO checks (type, check_nr, last_check, `interval`, status, host_nr, last_check_result_str, contact_nr) VALUES(%(type)s, %(check_nr)s, "0000-00-00 00:00:00", %(interval)s, "unknown", %(host_nr)s, "", %(contact_nr)s)', values)

elif sys.argv[1] == 'list-checks':
    list_checks(dbh)

else:
    print(f'"{sys.argv[1]}" is not understood')

ch.close()

dbh.commit()
