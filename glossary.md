Norc Glossary
=============

_Task_: An abstract concept of some work to be done.

+   _CommandTask_: A Task that executes an arbitrary shell command.
+   _Job_: A Task which executes a group of other Tasks.  This is done by
    constructing a directed graph using task Nodes and Dependencies.
  
_Schedule_: A definition of when a Task is to run (i.e., start an Instance of it).

_Scheduler_: A process which uses schedules to create and enqueue Instances at the appropriate time.

_Instance_: An execution of a Task.

_Queue_: An abstract concept of a distributed queueing system to disperse instances with.

+   _DBQueue_: Queue implemented using the database.
+   _SQSQueue_: Queue implemented using SQS.

_Executor_: A process which continually pops instances off a specific queue and starts them.

Note: Norc requires at least one Scheduler and at least one Executor to be running in order to function.  Multiple Executors are key to scaling the system for heavy workloads.

A _Task_ has at least one _Schedule_ which is used by a _Scheduler_ to create _Instances_ which go in a _Queue_ and are then popped and executed by _Executors_.
