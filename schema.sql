CREATE TABLE `check_local` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `cmdline` text NOT NULL,
  `check_name` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);

INSERT INTO `check_local` VALUES (1,'/usr/lib/nagios/plugins/check_ping -H %host% -4 -p 5 -c 500,50% -w 400,20%','ping');
INSERT INTO `check_local` VALUES (2,'/usr/lib/nagios/plugins/check_http -H %host% -E -j HEAD','HTTP');

CREATE TABLE `check_remote` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host` varchar(256) NOT NULL,
  `port` int(5) NOT NULL,
  `type` enum('nrpe') NOT NULL,
  `check_name` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);

CREATE TABLE `checks` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `type` enum('local','remote') NOT NULL,
  `check_nr` int(6) NOT NULL,
  `last_check` datetime(3) NOT NULL,
  `interval` int(6) NOT NULL,
  `status` enum('ok','warning','fatal','unknown') NOT NULL,
  `host_nr` int(6) NOT NULL,
  `last_check_result_str` text NOT NULL,
  PRIMARY KEY (`nr`)
);

CREATE TABLE `hosts` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);
