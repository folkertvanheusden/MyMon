CREATE TABLE `check_local` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `cmdline` text NOT NULL,
  `check_name` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);

INSERT INTO `check_local` VALUES (1,'/usr/lib/nagios/plugins/check_ping -H %host% -4 -p 5 -c 500,50% -w 400,20%','ping'),(2,'/usr/lib/nagios/plugins/check_http -H %host% -E -j HEAD','HTTP'),(3,'/usr/lib/nagios/plugins/check_tcp -H %host% -p %port% -4 -w 2.0 -c 5.0','IRC');

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
  `contact_nr` int(6) NOT NULL,
  `enabled` int(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`nr`),
  KEY `contact_nr` (`contact_nr`),
  KEY `host_nr` (`host_nr`),
  CONSTRAINT `checks_ibfk_1` FOREIGN KEY (`contact_nr`) REFERENCES `contacts` (`nr`),
  CONSTRAINT `checks_ibfk_2` FOREIGN KEY (`host_nr`) REFERENCES `hosts` (`nr`)
);

CREATE TABLE `contacts` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);

CREATE TABLE `hosts` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`)
);

CREATE TABLE `keyvalue` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host_nr` int(6) NOT NULL,
  `check_nr` int(6) NOT NULL,
  `key` varchar(255) NOT NULL,
  `value` text NOT NULL,
  PRIMARY KEY (`nr`)
);
