
v2.1 -> v2.2
============

  - Task "name" field is now nullable.
  - New table norc_revisions

### SQL Statements
__Norc must be completely stopped before making these changes.__

This must be run for each task implementation:

    ALTER TABLE norc_commandtask MODIFY name VARCHAR(128);
    ALTER TABLE norc_job MODIFY name VARCHAR(128);
    ...

This must be run for each instance implementation:
    
    ALTER TABLE norc_instance ADD COLUMN revision_id INT(11) DEFAULT NULL;
    ALTER TABLE norc_jobnodeinstance ADD COLUMN revision_id INT(11) DEFAULT NULL;
    ...

Create the new tables:

    CREATE TABLE `norc_revision` (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `info` varchar(64) NOT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `info` (`info`)
    );
    CREATE TABLE `norc_queuegroup` (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `name` varchar(64) NOT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `name` (`name`)
    );
    CREATE TABLE `norc_queuegroupitem` (
      `id` int(11) NOT NULL AUTO_INCREMENT,
      `group_id` int(11) NOT NULL,
      `queue_type_id` int(11) NOT NULL,
      `queue_id` int(10) unsigned NOT NULL,
      `priority` int(10) unsigned NOT NULL,
      PRIMARY KEY (`id`),
      UNIQUE KEY `queue_type_id` (`queue_type_id`,`queue_id`),
      UNIQUE KEY `queue_type_id_2` (`queue_type_id`,`queue_id`,`priority`),
      KEY `norc_queuegroupitem_group_id` (`group_id`),
      KEY `norc_queuegroupitem_queue_type_id` (`queue_type_id`)
    );

v2.0 -> v2.1
============

  - BaseInstance and BaseSchedule are renamed to AbstractInstance and
    AbstractSchedule.
  - Scheduler loses "active" column (BooleanField), gains "status",
    "request" (both PositiveSmallIntegerField, request is nullable), and
    "pid" (IntegerField) columns.  Old Schedulers should have status set
    to 8 (Status.ENDED).
  - Schedule and CronSchedule both gain "changed" and "deleted"
    (BooleanField) columns.
  - Deleting of schedules should now be done using the .soft_delete() method.

### SQL Statements
__Norc must be completely stopped before making these changes.__

    ALTER TABLE norc_scheduler DROP COLUMN active;
    ALTER TABLE norc_scheduler ADD COLUMN status SMALLINT(5) unsigned NOT NULL;
    ALTER TABLE norc_scheduler ADD COLUMN request SMALLINT(5) unsigned DEFAULT NULL;
    ALTER TABLE norc_scheduler ADD COLUMN pid INT(11) NOT NULL AFTER host;
    UPDATE norc_scheduler SET status=8;
    ALTER TABLE norc_schedule ADD COLUMN changed TINYINT(1) NOT NULL AFTER added;
    ALTER TABLE norc_schedule ADD COLUMN deleted TINYINT(1) NOT NULL AFTER changed;
    ALTER TABLE norc_cronschedule ADD COLUMN changed TINYINT(1) NOT NULL AFTER added;
    ALTER TABLE norc_cronschedule ADD COLUMN deleted TINYINT(1) NOT NULL AFTER changed;
    ALTER TABLE norc_executor MODIFY heartbeat datetime;
    ALTER TABLE norc_executor MODIFY started datetime;
