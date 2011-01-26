
# ATTN: THIS IS SUPER OUT OF DATE #

# Norc

Norc is a task management and scheduling system that replaces the Unix cron utility.  Its goal is to allow tasks to be created, managed and tracked in a flexible, user-friendly way.  Norc was first developed by [Darrell Silver](http://darrellsilver.com/) for use as the scheduling system for [Perpetually](http://www.perpetually.com/), the web archiving company.  It is currently used in production, and was open-sourced in October, 2009 at [NYC Python](http://www.nycpython.org/) at the suggestion of [David Christian](http://twitter.com/duganesque).  It has since undergone a major overhaul at the hands of Max Bogue, under Perpetually's employ.

Norc was first developed by [Darrell Silver](http://darrellsilver.com/) as the archiving scheduling system for [Perpetually.com's](http://www.perpetually.com/) archiving system, and is currently in production.   [Perpetually.com](http://www.perpetually.com/) lets you capture and archive any web site with a single click. It's the history of the internet made useful.  A core feature of [Perpetually's](http://www.perpetually.com/) offering is repeated, scheduled archives, a task for which Norc has proven a good fit.


## Features

 * Define **groups of Tasks** as Jobs with **Task dependencies**, ensuring that Task 'C' only runs after 'A' and 'B' have completed successfully.
 * All output for Tasks is managed in **normalized logs**, with support for uploading to an **external location** (Amazon S3 support built in).
 * **Schedule** Tasks, just like Cron. 
 * Run Tasks on **any number of hosts**.  Task state is shared in a single DB, making Norc as **scalable** as its underlying database.
 * Set **timeouts** for any Task, catching errors and prevent runaway processing.
 * Because all state is stored in a DB, it can be **administered through a web interface**.  In addition to Django's administration tools, Norc provides a powerful web reporting layer.


## Design & Terminology ##

Norc is written entirely in Python/Django.  It has been tested and rolled out by Perpetually, running on OS X and Linux, using MySQL, Python 2.5/2.6 and Django-1.1.

Each of these concepts are represented by Django models, mapping to a table in the database unless they are abstract.  Subclasses of the abstract models will produce their own tables.

See ./glossary.md for a quick overview of the Norc design.


### Tasks ###

A Norc Task is an **abstract description** of work to be done.  A Task class is implemented by subclassing norc.core.models.Task, and objects of that class represent different variations of that abstract type of work.  For example, Norc comes with the CommandTask class, of which specific objects represent different shell commands to execute.


### Jobs ###

A Job is an extension of a Norc task.  It contains JobNodes (which wrap other Tasks) and Dependencies (Node A must run after Node B, and uses those to execute the tasks in proper sequence.


### Instances ###

An Instance in Norc represents an **execution** of some work.  This generally means a run of a Task, but in some cases other subclasses of AbstractInstance are handy (for example, JobNodeInstances allow for the custom behavior that drives Jobs).  Instances store data about the execution, including start/end times, status, and the Executor that ran them.


### Schedules ###

In order for a Task to run, a schedule must be made to tell Norc when to run it.  There are two schedule classes: a simple Schedule which allows any number of repetitions with a set period between them, and a more complex CronSchedule which allows the user to choose the months, days, weekdays, hours, minutes, and seconds on which the Task should run.  More than one schedule may be created for a single Task.


### Scheduler ###

A process that reads schedules and uses them to create and enqueue instances at the appropriate time.  Norc **requires** at least one Scheduler to be running in order to function.  Schedulers can be run using the norc_scheduler script.


### Queues ###

Queues double as the way that instances are prioritized in Norc and as the means for distributing them to Executors.  Queues are an abstract concept; Norc comes with two implementations, DBQueue (the default) and SQSQueue.


### Executors ###

The workhorse of the Norc design flow, an Executor is a process that is designated for a specific queue, pulls instances from that queue, and then runs them.  Scalability of processing power for Norc is achieved by changing the number of Executors running for a given queue.  Since distribution is achieved through the queue implementation, Executors for a queue can be run on any number of different machines.  The norc_executor script is provided for starting Executors.


## Interacting & Monitoring ##

Norc has a web front end that allows for easy monitoring of the system, as well as controlling of Executors and Schedulers.  Paired with the Django admin interface, this creates a powerful web-based toolset.  In the future, the two should be merged to create an admin interface that conforms to Norc's design somewhat better.

On top of the web front end, there are various command line tools for interacting with Norc.

### norc_control ###

Allows stopping, killing, pausing and resuming for any single Executor or Scheduler at a time, or on a host-wide basis.

### norc_reporter ###

Displays similar status tables as the web front end.

### norc_log_viewer ###

Can be used to easily retrieve logs, both locally and from a remote backup location (e.g., Amazon S3).


## Installation ##

See ./INSTALL.md for a walkthrough.

