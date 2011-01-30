Norc Glossary
=============

__Task__: An abstract concept of some work to be done.

+   __CommandTask__: A Task that executes an arbitrary shell command.
+   __Job__: A Task which executes a group of other Tasks.  This is done by
    constructing a directed graph using task Nodes and Dependencies.
  
__Schedule__: A definition of when a Task is to run (i.e., start an Instance of it).

__Scheduler__: A process which uses schedules to create and enqueue Instances at the appropriate time.

__Instance__: An execution of a Task.

__Queue__: An abstract concept of a distributed queueing system to disperse instances with.

+   __DBQueue__: Queue implemented using the database.
+   __SQSQueue__: Queue implemented using SQS.

__Executor__: A process which continually pops instances off a specific queue and starts them.

Note: Norc requires at least one Scheduler total and at least one Executor per queue to be running in order to function.  Multiple Executors are key to scaling the system for heavy workloads.

A __Task__ has at least one __Schedule__ which is used by a __Scheduler__ to create __Instances__ which go in a __Queue__ and are then popped and executed by __Executors__.
