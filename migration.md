
v2.0 -> v2.1
============

  - Scheduler loses "active" column (BooleanField), gains "status",
    "request" (both PositiveSmallIntegerField, request is nullable), and
    "pid" (IntegerField) columns.  Old Schedulers should have status set
    to 8 (Status.ENDED).
  - Schedule and CronSchedule both gain "changed" and "deleted"
    (BooleanField) columns.