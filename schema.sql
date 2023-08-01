CREATE TABLE `check_local` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `cmdline` text NOT NULL,
  `check_name` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`),
  UNIQUE KEY `c_unique` (`cmdline`(255),`check_name`)
);

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
  `enabled` int(1) NOT NULL DEFAULT 0,
  `contactgroups_nr` int(6) NOT NULL,
  `muted` int(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`nr`),
  KEY `host_nr` (`host_nr`),
  KEY `contactgroups_nr` (`contactgroups_nr`),
  CONSTRAINT `checks_ibfk_2` FOREIGN KEY (`host_nr`) REFERENCES `hosts` (`nr`),
  CONSTRAINT `checks_ibfk_3` FOREIGN KEY (`contactgroups_nr`) REFERENCES `contactgroups` (`group_nr`)
);

CREATE TABLE `contactgroups` (
  `group_nr` int(6) NOT NULL,
  `contact_nr` int(6) NOT NULL,
  PRIMARY KEY (`group_nr`,`contact_nr`),
  KEY `contact_nr` (`contact_nr`),
  CONSTRAINT `contactgroups_ibfk_1` FOREIGN KEY (`contact_nr`) REFERENCES `contacts` (`nr`)
);

CREATE TABLE `contactgroupsnames` (
  `group_nr` int(6) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`group_nr`),
  UNIQUE KEY `name` (`name`)
);

CREATE TABLE `contacts` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`),
  KEY `inr` (`nr`)
);

CREATE TABLE `hosts` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host` varchar(255) NOT NULL,
  PRIMARY KEY (`nr`),
  UNIQUE KEY `host_unique` (`host`)
);

CREATE TABLE `keyvalue` (
  `nr` int(6) NOT NULL AUTO_INCREMENT,
  `host_nr` int(6) NOT NULL,
  `check_nr` int(6) NOT NULL,
  `key` varchar(255) NOT NULL,
  `value` text NOT NULL,
  PRIMARY KEY (`nr`),
  UNIQUE KEY `kv_unique` (`host_nr`,`check_nr`,`key`,`value`(255))
);
