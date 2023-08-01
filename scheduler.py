#! /usr/bin/python3

# python3 -m pip install emails
# python3 -m pip install influxdb

from configuration import *
import datetime
import emails
import html
from influxdb import InfluxDBClient
import mysql.connector
import re
import subprocess
import threading
import time


class poller:
    def __init__(self, mysql_host, mysql_user, mysql_pass, mysql_db, influx_host, influx_port, influx_db, email_from, email_addr, email_smtp):
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_pass = mysql_pass
        self.mysql_db   = mysql_db

        self.influx_host = influx_host
        self.influx_port = influx_port
        self.influx_db   = influx_db

        self.email_from = email_from
        self.email_addr = email_addr
        self.email_smtp = email_smtp

        self.th = threading.Thread(target=self._thread)
        self.th.start()

    # local are always nagios style checks
    def _do_local_check(self, cmdline):
        start_t = time.time()

        # print(f'Invoking {cmdline}')

        result = subprocess.run(cmdline, capture_output=True, shell=True, timeout=15.0)

        end_t = time.time()

        rc_str = result.stdout.decode('utf-8').rstrip('\n')

        # print(f'Reply: {rc_str}, return code: {result.returncode}')

        values = dict()

        if result.returncode <= 2 and result.returncode >= 0:
            values['check-duration'] = end_t - start_t

            pipe = rc_str.find('|')

            if pipe != -1:
                perf_str = rc_str[pipe + 1:]
                rc_str = rc_str[0:pipe]

                if len(perf_str) > 0:
                    performance_pairs = perf_str.split(' ')

                    # print(f'Performance data: {performance_pairs}')

                    for pair in performance_pairs:
                        if pair == '':
                            continue

                        try:
                            key, value = pair.split('=')

                            values[key] = value

                        except ValueError:
                            print(f'Invalid performance pair {pair}')

            elif result.returncode < 0:
                result.returncode = 3

        return (rc_str, values, result.returncode)

    def _put_influx(self, meta, name, data):
        iclient = InfluxDBClient(host=self.influx_host, port=self.influx_port)
        iclient.switch_database(self.influx_db)  # TODO

        record = dict()
        record['measurement'] = name

        record['tags'] = meta

        record['time'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        record['fields'] = dict()

        for field in data:
            field_data = data[field]

            if isinstance(field_data, str) and field_data[0] >= '0' and field_data[0] <= '9':  # then assume float value
                # strip text and other data

                semicol = field_data.find(';')
                if semicol != -1:
                    field_data = field_data[0:semicol]

                try:
                    field_data = float(re.sub('[A-z%]', '', field_data))

                except ValueError as ve:
                    # use as is
                    pass

            record['fields'][field] = field_data

        if iclient.write_points([ record ]) == False:
            print('Failed writing to InfluxDB!')

        iclient.close()

    def do_escapes(self, work_on, parameters):
        for p in parameters:
            work_on = work_on.replace(f'%{p}%', parameters[p])

        return work_on

    def state_to_str(self, state):
        if state == 0:
            return 'ok'

        if state == 1:
            return 'warning'

        if state == 2:
            return 'fatal'

        if state == 3:
            return 'unknown'

        return f'?{state}?'

    def _send_email(self, group_nr, host_name, check_name, check_result, previous_state):
        dbh = mysql.connector.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_pass, database=self.mysql_db)

        ch = dbh.cursor(dictionary=True)

        ch.execute('SELECT email FROM contactgroups, contacts WHERE contactgroups.group_nr=%(group_nr)s AND contactgroups.contact_nr=contacts.nr', { 'group_nr': group_nr })

        for row in ch.fetchall():
            new_state = self.state_to_str(check_result[2])

            # TODO: this is not XSS safe:
            # (in case a plugin returns unchecked user data)
            escaped_output = html.escape(check_result[0])

            message = emails.html(html=f'<p>State of {check_name} on {host_name} went from {previous_state} to {new_state}</p><p>Output: {escaped_output}</p>',
                    subject=f'State for {check_name}@{host_name}: {new_state}', mail_from=(self.email_from, self.email_addr))

            r = message.send(to=row['email'], smtp={'host': self.email_smtp, 'timeout': 15})

            if r.status_code != 250:
                print(f'Failed to send e-mail to {row["email"]}: {r.status_code}')

            else:
                print(f'e-mail sent to {row["email"]}')

        ch.close()

        dbh.close()

    def _do_poller(self, base_nr, type_, check_nr, host_nr, previous_state, contactgroups_nr, muted):
        dbh = mysql.connector.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_pass, database=self.mysql_db)

        # get cmdline, replace macros, invoke

        check_result = None

        check_name = None

        meta_data = dict()

        if type_ == 'local':
            ch = dbh.cursor(dictionary=True)

            ch.execute('SELECT host FROM hosts WHERE nr=%(host_nr)s', { 'host_nr': host_nr })

            meta_data = ch.fetchone()

            if meta_data == None:
                print(f'Host {host_nr} missing')

            else:
                ch.execute('SELECT cmdline, check_name FROM check_local WHERE nr=%(check_nr)s', { 'check_nr': check_nr })

                row = ch.fetchone()

                if row == None:
                    print(f'Error: local check missing')

                else:
                    check_name = row['check_name']
                    cmdline = row['cmdline']

                    # other k/vs
                    ch.execute('SELECT `key`, `value` FROM keyvalue WHERE host_nr=%(host_nr)s AND check_nr=%(base_nr)s', { 'host_nr': host_nr, 'base_nr': base_nr })

                    for row in ch.fetchall():
                        meta_data[row['key']] = row['value']

                    # replace macros
                    processed_cmdline = self.do_escapes(cmdline, meta_data)

                    print(f"Executing local check {check_nr}: {processed_cmdline}")

                    check_result = self._do_local_check(processed_cmdline)

            ch.close()

        elif type_ == 'remote':
            # TODO
            pass

        else:
            print(f'Error: check is not local nor remote')

        # update status

        check_result_data = None

        if check_result[2] == 3 or check_result[2] == None:
            check_result_data = { 'nr': base_nr, 'status': 'unknown', 'result_str': check_result[0] }

        elif check_result[2] == 2:
            check_result_data = { 'nr': base_nr, 'status': 'fatal', 'result_str': check_result[0] }

        elif check_result[2] == 1:
            check_result_data = { 'nr': base_nr, 'status': 'warning', 'result_str': check_result[0] }

        elif check_result[2] == 0:
            check_result_data = { 'nr': base_nr, 'status': 'ok', 'result_str': check_result[0] }

        else:
            print(f'Unexpected check result {check_result}')

        if check_result_data != None:
            # print(f'Result: {check_result_data}')

            # previous_state comes from the database and is thus a string (ok, warning, ...)
            if self.state_to_str(check_result[2]) != previous_state:
                if muted == 0:
                    self._send_email(contactgroups_nr, meta_data['host'], check_name, check_result, previous_state)

            ch = dbh.cursor()
            ch.execute('UPDATE checks SET status=%(status)s, last_check_result_str=%(result_str)s WHERE nr=%(nr)s', check_result_data)
            ch.close()

            self._put_influx(meta_data, check_name, check_result[1])

        dbh.commit()

        dbh.close()

    def _thread(self):
        dbh = mysql.connector.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_pass, database=self.mysql_db)

        while True:
            try:
                ch = dbh.cursor(dictionary=True)

                print('Check for checks to run')

                any_started = False

                # see what needs to be checked now
                ch.execute('''
SELECT
    nr, type, check_nr, host_nr, status, contactgroups_nr, muted,
    (
     -- are other checks dependent on this check?
     SELECT
         COUNT(*) > 0
     FROM
         (
          -- get a list of checks to which an other check depends on
          SELECT
             distinct depends_on_check_nr
          FROM
             check_dependencies, checks
          WHERE
             check_dependencies.check_nr IN (
                                             -- find checks that need an update and are enabled
                                             SELECT
                                                nr
                                             FROM
                                                 checks
                                             WHERE
                                                 (now() >= DATE_ADD(last_check, INTERVAL `interval` SECOND) OR last_check = '0000-00-00 00:00:00') AND
                                                 enabled=1
                                            ) AND
             checks.nr=depends_on_check_nr AND
             (now() >= DATE_ADD(last_check, INTERVAL `interval` SECOND) OR last_check = '0000-00-00 00:00:00')
         ) AS prio_in
     WHERE
         prio_in.depends_on_check_nr=nr
    ) AS prio
FROM
    checks
WHERE
    (now() >= DATE_ADD(last_check, INTERVAL `interval` SECOND) OR last_check = '0000-00-00 00:00:00') AND enabled=1
ORDER BY
    prio DESC,
    last_check ASC''')

                wait_for = []

                for row in ch.fetchall():
                    print(f'Starting check {row["check_nr"]}, prio: {row["prio"]}')

                    # commit before invoking check so that it won't get executed too soon (e.g. when check_interval < check_execution_duration)
                    ch.execute("UPDATE checks SET last_check = NOW() WHERE nr=%(nr)s", { 'nr': row['nr'] })
                    dbh.commit()

                    cur_th = threading.Thread(target=self._do_poller, args=(row['nr'], row['type'], row['check_nr'], row['host_nr'], row['status'], row['contactgroups_nr'], row['muted']))

                    # wait for the prio checks to be finished first
                    if row['prio']:
                        # if a dependency depends on another dependency, then we need to wait for that one first
                        # but multiple level dependency has not been implemented yet
                        wait_for.append(cur_th)
                        cur_th.start()

                    else:
                        for th_id in wait_for:
                            th_id.join()

                        wait_for = []

                        # other checks can finish when they're ready
                        cur_th.daemon = True
                        cur_th.start()

                    any_started = True

                # calculate how long to wait
                ch.execute('SELECT MIN(DATE_ADD(last_check, INTERVAL `interval` SECOND)) - NOW() AS `interval` FROM checks WHERE enabled=1')

                row = ch.fetchone()
                sleep_n_in = row['interval']

                if not sleep_n_in is None:
                    sleep_n = float(sleep_n_in)

                    # allows re-configuration
                    if sleep_n > 5:
                        sleep_n = 5

                    if sleep_n > 0:
                        print(f'Sleep for {sleep_n} seconds')

                        time.sleep(sleep_n)

                ch.close()

                if any_started:
                    time.sleep(0.1)

            except Exception as e:
                print(e)

                time.sleep(0.1)

p = poller(db_host, db_user, db_pass, db_db, influx_host, influx_port, influx_db, email_sender_name, email_sender_address, email_smtp_server)

while True:
    time.sleep(86400.)
