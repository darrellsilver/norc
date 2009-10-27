
# Norc
Norc is a task management system that replaces Unix cron.  It allows Tasks to be created, managed and audited in a flexible, user-friendly way.  Norc was first developed by Darrell Silver for use as the scheduling system for Perpetually.com, the web archiving company.  It was open-sourced in October, 2009.

## MAJOR FEATURES

 * **Dependency Management**: Norc allows you to define a specific run-order for Tasks, ensuring that Task 'C' only runs after 'A' and 'B' have completed successfully.
 * **Resource Management**: Norc can throttle resource usage by tasks, preventing too many tasks from simultaneously using a single resource.
 * **Error Reporting**: Exit statuses (or return values) of tasks can generate alerts over email, or through a monitoring tool
 * **Log Management**: Output from Tasks (stdin & stderr) are centrally managed and available.
 * **Scheduling**: Tasks in Norc can be scheduled with the same flexibility as any cron task
 * **Decentralized (-ish)**: Unlike cron, tasks in Norc are not tied to a single host. Rather, all state and task information is stored in a database.
 * **Auditing**: All task exit statuses, run times and durations are stored allowing historical analysis of expected compute time for repetitive tasks, error rates, etc.
 * **Timeouts**: Norc supports Task-specific timeouts.
 * **Web/Terminal Administration**: Norc's state is entirely database driven, allowing Tasks to be fully and externally controlled.  Currently this is limited to a command-line interface and Django's built-in admin console.  There is a huge opportunity to improve this area to make a fully-functional web interface for Norc.
 * **SQS Plugin**: Use Amazon's Simple Queue Service as an alternative source of Tasks, employing the rest of Norc's monitoring, daemon and management infrastructure.


## ARCHITECTURE & TERMINOLOGY OVERVIEW:

Norc is written entirely in Python/Django.  It has been tested and rolled for Perpetually.com, running on OS X and Linux, using MySQL, Python 2.4, 2.5, 2.6 and Django-1.0.


Tasks:
 A Task is a runnable unit of work. It is exactly analogous to a Unix 'cronjob'.  In Norc, Tasks are implemented by subclassing either the Task or ScheduleableTask interfaces.  There are several pre-built subclasses in Norc that cover common use cases:
 * **RunCommand**: allows running a single command.
 * **ScheduledRunCommand**: allows running a single command on a schedule

  These classes are Django models, and as such each map to a table in the databse. All these base interfaces and subclasses are defined norc.core.models.py
  Subclasses of Task & SchedulableTask must implement a few methods, and can safely override others:
   * run(): Mandatory: Action taken when this Task is run. Main processing happens here.
   * get_library_name(): Mandatory: The string path to this Task class name. This shouldn't be necessary, but it currently is.
   * has_timeout(): Mandatory boolean; True if this Task should timeout. False otherwise.
   * get_timeout(): Mandatory integer (seconds); return the number of seconds before this Task times out.  Must be defined if has_timeout() returns True.
   * is_due_to_run(): Boolean; defaults to True but can be overridden.  SchedulableTask has its own time-based implementation of this method.
   * alert_on_failure(): Boolean; defaults to True.

  Most Tasks are designed to be run multiple times, such as on a daily our hourly basis. However, Norc provides flexibility on this:
   * PERSISTENT: Run each time it is due_to_run().  This applies to most tasks.
   * EPHEMERAL: Run once, and never again.  This is similar to an @ job, and is often paired with PERSISTENT Iterations (see below).

  Task Statuses define the status of a single run of a single Task.  They are
   * 

Jobs:
 * Each Task in Norc belongs to exactly 1 Job.  Dependencies between Tasks can only be defined within a single Job.
 * Jobs may be started on a schedule, such as midnight.  Norc uses a Job (TMS_ADMIN) to start all Jobs in Norc.


Iterations:
 * Each run of each Job does so as a distinct Iteration.  Iterations can either be RUNNING (Tasks will be run as they become available), PAUSED (The iteration has not completed but new Tasks will not be started) or 'DONE' (No more tasks will be run for this job).  Iterations have a few options:
   * Iteration Type defines whether an Iteration is 
     * EPHEMERAL: The Iteration should run as long as Tasks in that Job for that iteration are incomplete.  Once all Tasks are complete (see Task Statuses below for details), the Iteration is marked as 'DONE'.  This is best used for a series of Tasks that run once a day, such as a data download Task followed by a data processes Task.  This is the most common type of Iteration.
     * PERSISTENT: The Iteration will remain running indefinitely, starting Tasks as they become available.  This is best used for Tasks that run once, such as EPHEMERAL Tasks.


Resources & Resource Relationships:
 * Norc allows usage of shared resources to be throttled, preventing too many Tasks from accessing a single resource, such as a web site or database with limited available connections.  Tasks can only be run in any Region that offers sufficient resources available at run time.
 * In addition to throttling limited resources, Resources are often used to target certain environments.  For example, if you have Tasks that can only run on Linux, then you should define a 'Linux' Resource, define a TaskResourceRelationship between this Task and 'Linux'.  This Task will then never run on any non-Linux host (see section on Daemons & Regions for how this works).
 * By default, each Task consumes 1 DATABASE_CONNECTION Resource.

Daemons:
 * Daemons in Norc (called TMSDaemons for no good reason) are responsible for kicking off all Tasks in Norc.  A daemon is a unix process running on a specific host running as tmsd.py.


Regions:
 * Regions are islands of Resource availability.  Each Daemon runs within a single Region.


Dependency Types:
 * Tasks in the same Job can define Dependencies that create a parent -> child relationship between Tasks.  Child Tasks will only run once all their Parent's have satisfactorily completed.
 * Typically a child Task only runs once its parents have completed successfully, but this can be altered using Dependency Types:
   * DEP_TYPE_STRICT: Child Tasks only run when the parent has completed successfully.  This is the most common type of dependency.
   * DEP_TYPE_FLOW: Child Tasks run as soon as the parent has completed, regardless of the parent's exit status.


## INTERACTING & MONITORING NORC:

 * Norc could support a web front end that allows full administration of the entire system, but none currently exists. Instead, Norc makes use of Django's excellent Admin interface.
 * Norc has three primary command line tools that let you control and view Tasks, Jobs and Daemons in Norc:
   * tmsdctl.py: Allows stopping, killing, viewing of all Daemons in Norc.  It also allows an overview of Tasks run by each Daemon.  Here's some sample output:

    $ tmsdctl 
    Status as of 10/27/2009 19:47:27
    6 INTERESTING tms daemon(s):
    ID     Type     Region    Host          PID     Running   Success   Error    Status               Started   Ended
    409     TMS     perp1     perpetually   14031         6       120       3   RUNNING   2009-10-24 18:52:52       -
    413     TMS     perp3     perp3         15159         2      2283       0   RUNNING   2009-10-24 19:01:26       -

    $ tmsdctl --det 410
    Status as of 10/27/2009 19:50:00
    1 INTERESTING tms daemon(s):
    ID     Type     Region    Host          PID     Running   Success   Error    Status               Started   Ended
    409     TMS     perp1     perpetually   14031         6       120       3   RUNNING   2009-10-24 18:52:52       -

    TMS Daemon perp1:410 (RUNNING) manages 3 task(s):

    Task ID      Status               Started                 Ended
    7546134    TIMEDOUT   2009-10-25 00:05:30   2009-10-25 00:20:30
    7546188       ERROR   2009-10-25 00:08:55   2009-10-25 00:10:05
    7546048       ERROR   2009-10-25 00:09:48   2009-10-25 00:09:48
    7546205     RUNNING   2009-10-25 00:18:54   2009-10-25 00:18:55



## CODE BASE & DEVELOPMENT STATUS:

Norc is stable, but there are known issues & limitations:
 * Log files are currently stored only on the host on which the Task ran.
   This limits their accessibility, and could be remedied through pushing them to S3, or other central service. They're just text files.
 * Processes instead of threading
   Tasks
 * No configurable environments

Norc was first developed by Darrell Silver (darrell@perpetually.com) to be the archiving scheduling system for Perpetually.com's archiving system, and is currently in production.   Perpetually.com lets you capture and archive any web site with a single click. It's the history of the internet made useful.  A core feature of Perpetually's offering is repeated, scheduled archives, a Task for which Norc has proven a good fit.


## INSTALL:



## EXAMPLE:



## CURRENT DEVELOPMENT STATUS:



## VERSION:



## LICENSE:


