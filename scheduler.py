#! /usr/bin/python3

# python3 -m pip install influxdb

import datetime
from influxdb import InfluxDBClient
import mysql.connector
import re
import subprocess
import threading
import time


class poller:
    def __init__(self, mysql_host, mysql_user, mysql_pass, mysql_db, influx_host, influx_port, influx_db):
        self.mysql_host = mysql_host
        self.mysql_user = mysql_user
        self.mysql_pass = mysql_pass
        self.mysql_db   = mysql_db

        self.influx_host = influx_host
        self.influx_port = influx_port
        self.influx_db   = influx_db

        self.th = threading.Thread(target=self._thread)
        self.th.start()

    # local are always nagios style checks
    def _do_local_check(self, cmdline):
        start_t = time.time()

        print(f'Invoking {cmdline}')

        result = subprocess.run(cmdline, capture_output=True, shell=True, timeout=15.0)

        end_t = time.time()

        rc_str = result.stdout.decode('utf-8').rstrip('\n')

        print(f'Reply: {rc_str}, return code: {result.returncode}')

        values = dict()

        if result.returncode <= 2:
            values['check-duration'] = end_t - start_t

            pipe = rc_str.find('|')

            if pipe != -1:
                perf_str = rc_str[pipe + 1:]
                rc_str = rc_str[0:pipe]

                if len(perf_str) > 0:
                    performance_pairs = perf_str.split(' ')

                    print(f'Performance data: {performance_pairs}')

                    for pair in performance_pairs:
                        try:
                            key, value = pair.split('=')

                            values[key] = value

                        except ValueError:
                            print(f'Invalid performance pair {pair}')

        return (rc_str, values, result.returncode)

    def _put_influx(self, host, name, data):
        iclient = InfluxDBClient(host=self.influx_host, port=self.influx_port)
        iclient.switch_database(self.influx_db)  # TODO

        record = dict()
        record['measurement'] = name

        record['tags'] = dict()
        record['tags']['host'] = host

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

        iclient.write_points([ record ])

        iclient.close()

    def do_escapes(self, work_on, parameters):
        for p in parameters:
            work_on = work_on.replace(f'%{p}%', parameters[p])

        return work_on

    def _do_poller(self, base_nr, type_, check_nr, host_nr):
        dbh = mysql.connector.connect(host=self.mysql_host, user=self.mysql_user, password=self.mysql_pass, database=self.mysql_db)

        # get cmdline, replace macros, invoke

        check_result = None

        check_name = None

        if type_ == 'local':
            ch = dbh.cursor(dictionary=True)

            ch.execute('SELECT host FROM hosts WHERE nr=%s' % host_nr)

            host_data = ch.fetchone()

            if host_data == None:
                print(f'Host {host_nr} missing')

            else:
                ch.execute('SELECT cmdline, check_name FROM check_local WHERE nr=%s' % check_nr)

                row = ch.fetchone()

                if row == None:
                    print(f'Error: local check missing')

                else:
                    check_name = row['check_name']

                    processed_cmdline = self.do_escapes(row['cmdline'], host_data)

                    print(f"Executing local check {check_nr}: {row['cmdline']}: {processed_cmdline}")

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
            print(f'Result: {check_result_data}')

            ch = dbh.cursor()
            ch.execute('UPDATE checks SET status=%(status)s, last_check_result_str=%(result_str)s WHERE nr=%(nr)s', check_result_data)
            ch.close()

            self._put_influx(host_data['host'], check_name, check_result[1])

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
                ch.execute("SELECT nr, type, check_nr, host_nr FROm checks WHERE now() >= DATE_ADD(last_check, INTERVAL `interval` SECOND) ORDER BY last_check ASC")

                for row in ch.fetchall():
                    print(f'Starting check {row["check_nr"]}')

                    # commit before invoking check so that it won't get executed too soon (e.g. when check_interval < check_execution_duration)
                    ch.execute("UPDATE checks SEt last_check = now() WHERE nr=%s" % row['nr'])
                    dbh.commit()

                    cur_th = threading.Thread(target=self._do_poller, args=(row['nr'], row['type'], row['check_nr'], row['host_nr']))
                    cur_th.daemon = True
                    cur_th.start()

                    any_started = True

                # calculate how long to wait
                ch.execute('SELECT MIN(DATE_ADD(last_check, INTERVAL `interval` SECOND)) - NOW() AS `interval` FROM checks')

                row = ch.fetchone()
                sleep_n_in = row['interval']

                if not sleep_n_in is None:
                    sleep_n = float(sleep_n_in)

                    # TODO work-around for a bug where sleep_n sometimes gets large
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

p = poller('localhost', 'mymon', 'mypass', 'mymon', 'localhost', 8086, 'mymon')
