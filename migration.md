
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

SQL Statements
--------------
__Norc must be completely stopped before making these changes.__

    ALTER TABLE norc_scheduler DROP COLUMN active;
    ALTER TABLE norc_scheduler ADD COLUMN status SMALLINT(5) unsigned NOT NULL;
    ALTER TABLE norc_scheduler ADD COLUMN request SMALLINT(5) unsigned DEFAULT NULL;
    ALTER TABLE norc_scheduler ADD COLUMN pid INT(11) NOT NULL AFTER host;
    UPDATE norc_scheduler SET status=8;
    ALTER TABLE norc_schedule ADD COLUMN changed TINYINT(1) NOT NULL AFTER added;
    ALTER TABLE norc_schedule ADD COLUMN deleted TINYINT(1) NOT NULL AFTER changed;