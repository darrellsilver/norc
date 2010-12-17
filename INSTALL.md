
# ATTN: THIS IS SUPER OUT OF DATE #

TODO:
    django must be in python path
    setting up an environment
    making a log directory
    set the norc environment shell variable
    

# Installing Norc

The goal of this walkthrough is to set up the basic Norc environment, and run a sample Task.  Much of the power of Norc is in its extensibility beyond simple Task management, so the more hack-happy you are, the better!


## Environment

Other environments will probably work, but we've not tested too many different configurations.

 * Python 2.5.x or 2.6.x.   We've tested on all these versions, 
 * Linux (Redhat Fedora 4) or OS X (Tiger, Leopard or Snow Leopard).
 * Django 1.1; later versions have not been tested yet.
 * A semi-recent version of MySQL (5.x or greater).  If you're not using MySQL everything should still work.  You'll just have to replace the mysql steps with whatever database backend you're using and change the configuration in settings.py as necessary.


## Download

    $ git clone git://github.com/darrellsilver/norc.git
    Cloning into norc...
    remote: Counting objects: 2600, done.
    remote: Compressing objects: 100% (725/725), done.
    remote: Total 2600 (delta 1867), reused 2509 (delta 1802)
    Receiving objects: 100% (2600/2600), 573.53 KiB | 1.07 MiB/s, done.
    Resolving deltas: 100% (1867/1867), done.

We'll be inside the norc/ directory for the rest of the tutorial.

    $ cd norc/


## Prepare the Database

This step depends on what database you're using; MySQL is recommended as it is the only DB that has been tested with Norc.  You need to have a username and password for Django's settings.


## Configuration

All user settings are stored in the settings_local.py file, which is not contained in Git.  Therefore, create it by copying the example file:

    $ cp -p settings_local.py.example settings_local.py

Norc uses a class structure to easily allow for multiple environments with common settings.  Create your own class that inherits from BaseEnv by renaming and editing DemoEnv to have the proper credentials.  Then, set the NORC_ENVIRONMENT shell variable to the name of that class (see below).  Crucial items are in the example file, but see defaults.py for more options that can be set.


## Run Environment

In your shell environment, Django & Norc require a few variables.  These should be set in your shell's configuration file (e.g., ~/.bashrc or ~/.zshrc).  In the following code, replace <norc_path> with the full path to the folder **containing** the norc directory.
    
    # Norc source code must be in your PYTHONPATH.
    export PYTHONPATH=$PYTHONPATH:**<norc_path>**
    # The settings environment to be used by Norc.
    export NORC_ENVIRONMENT='BaseEnv'
    # Python import path to the settings.py file.
    export DJANGO_SETTINGS_MODULE='norc.settings'
    # Norc has a few executables that need to be in your PATH.
    export PATH=$PATH:**<norc_path>**/norc/bin


## Initialize Django

This is the first time you'll be running the full app, so any errors in configuration so far will show up here.

The manage.py is a Django idiom used for controlling the app.  The command syncdb for it will synchronize the models of Norc with the database, which in this case means creating them all.  This is the output log of Django creating the tables in MySQL.  Because we've also never setup an admin account, Django also prompts us to setup an admin user; you should do this and remember the credentials for the next step.

    $ python manage.py syncdb
    Creating table django_admin_log
    Creating table auth_permission
    Creating table auth_group
    Creating table auth_user
    Creating table auth_message
    Creating table django_content_type
    Creating table django_session
    Creating table django_site
    Creating table norc_instance
    Creating table norc_commandtask
    Creating table norc_job
    Creating table norc_jobnode
    Creating table norc_jobnodeinstance
    Creating table norc_dependency
    Creating table norc_schedule
    Creating table norc_cronschedule
    Creating table norc_scheduler
    Creating table norc_dbqueue
    Creating table norc_dbqueueitem
    Creating table norc_executor
    
    You just installed Django's auth system, which means you don't have any superusers defined.
    Would you like to create one now? (yes/no): yes
    Username (Leave blank to use 'norc_demo'): 
    E-mail address: demo@norcproject.com
    Password: 
    Password (again): 
    Superuser created successfully.
    Installing index for admin.LogEntry model
    Installing index for auth.Permission model
    Installing index for auth.Message model
    Installing index for core.Instance model
    Installing index for core.JobNode model
    Installing index for core.JobNodeInstance model
    Installing index for core.Dependency model
    Installing index for core.Schedule model
    Installing index for core.CronSchedule model
    Installing index for core.DBQueueItem model
    Installing index for core.Executor model


## Unit Tests

Ok, at this point, you should be able to run the unit tests successfully.

    $ python manage.py test
    Creating test database...
    Creating table django_admin_log
    Creating table auth_permission
    Creating table auth_group
    Creating table auth_user
    Creating table auth_message
    Creating table django_content_type
    Creating table django_session
    Creating table django_site
    Creating table norc_instance
    Creating table norc_commandtask
    Creating table norc_job
    Creating table norc_jobnode
    Creating table norc_jobnodeinstance
    Creating table norc_dependency
    Creating table norc_schedule
    Creating table norc_cronschedule
    Creating table norc_scheduler
    Creating table norc_dbqueue
    Creating table norc_dbqueueitem
    Creating table norc_executor
    Creating table norc_sqsqueue
    Installing index for admin.LogEntry model
    Installing index for auth.Permission model
    Installing index for auth.Message model
    Installing index for core.Instance model
    Installing index for core.JobNode model
    Installing index for core.JobNodeInstance model
    Installing index for core.Dependency model
    Installing index for core.Schedule model
    Installing index for core.CronSchedule model
    Installing index for core.DBQueueItem model
    Installing index for core.Executor model
    ..................................................
    ----------------------------------------------------------------------
    Ran 50 tests in 47.740s

    OK
    Destroying test database...


## Demo Data

To run the system, a pieces of data are needed.  These you can currently either create via the Django admin screen or a Python shell.  For now, we'll stick to the shell because the admin screen isn't fully customized for Norc.

    $ python manage.py shell
    Python 2.6.1 (r261:67515, Jun 24 2010, 21:47:49) 
    [GCC 4.2.1 (Apple Inc. build 5646)] on darwin
    Type "help", "copyright", "credits" or "license" for more information.
    (InteractiveConsole)
    >>> from norc.core.models import *
    >>> q = DBQueue.objects.create(name="DemoQueue")
    >>> t = CommandTask.objects.create(name="DemoTask", command="echo 'Demo successful!'")
    >>> 
    
Now leave this open until after the next step.


## Starting the Daemons

Norc relies on two separate daemons to function: norc_scheduler and norc_executor.  Only one Scheduler should ever be needed at a time, but multiple Executors is how Norc is designed to scale across systems.  To see the current status, the norc_reporter command exists:

    norc_reporter -esq
    [2010/12/17 05:17:49] 

    ## Executors ##
    None found.

    ## Schedulers ##
    None found.

    ## Queues ##
    None found.

Now open two new terminal sessions and start both a Scheduler and an Executor:

    $ norc_scheduler -e
    [2010/12/17 05:19:20.715991] INFO: Scheduler #1 on host Zaraki.local initialized; starting...

The -e tells the daemon to echo its log output back to the console.

    $ norc_executor DemoQueue -c 5 -e
    [2010/12/17 05:28:15.823928] INFO: <Executor #1 on Zaraki.local> initialized; starting...
    [2010/12/17 05:28:15.828948] INFO: <Executor #1 on Zaraki.local> is now running on host Zaraki.local.

DemoQueue is the name of the queue this Executor will pull from, and -c 5 means it can run up to 5 things concurrently.


## Adding a Schedule

You now have all the pieces set up for a task to run except one: when to run it?  Go back to the Python shell you were working with earlier and create a basic Schedule:

    >>> Schedule.create(task=t, queue=q, period=5, reps=5)
    <Schedule #1, CommandTask DemoTask:5s>
    >>> 

That tells Norc to run the task every 5 seconds, 5 times total, starting now.  You should see something like this in the Scheduler:

    [2010/12/17 05:38:20.326725] INFO: Claiming <Schedule #1, CommandTask DemoTask:5s>.
    [2010/12/17 05:38:20.340241] INFO: Enqueuing <Instance #1 of CommandTask DemoTask>.
    [2010/12/17 05:38:25.008153] INFO: Enqueuing <Instance #2 of CommandTask DemoTask>.
    [2010/12/17 05:38:30.007917] INFO: Enqueuing <Instance #3 of CommandTask DemoTask>.
    [2010/12/17 05:38:35.006390] INFO: Enqueuing <Instance #4 of CommandTask DemoTask>.
    [2010/12/17 05:38:40.004968] INFO: Enqueuing <Instance #5 of CommandTask DemoTask>.

And something like this in the Executor:

    [2010/12/17 05:38:20.702097] INFO: Starting instance '<Instance #1 of CommandTask DemoTask>'...
    [2010/12/17 05:38:21.722821] INFO: Instance '<Instance #1 of CommandTask DemoTask>' ended with status SUCCESS.
    [2010/12/17 05:38:25.260937] INFO: Starting instance '<Instance #2 of CommandTask DemoTask>'...
    [2010/12/17 05:38:26.278038] INFO: Instance '<Instance #2 of CommandTask DemoTask>' ended with status SUCCESS.
    [2010/12/17 05:38:30.317053] INFO: Starting instance '<Instance #3 of CommandTask DemoTask>'...
    [2010/12/17 05:38:31.336631] INFO: Instance '<Instance #3 of CommandTask DemoTask>' ended with status SUCCESS.
    [2010/12/17 05:38:35.374896] INFO: Starting instance '<Instance #4 of CommandTask DemoTask>'...
    [2010/12/17 05:38:36.392472] INFO: Instance '<Instance #4 of CommandTask DemoTask>' ended with status SUCCESS.
    [2010/12/17 05:38:40.431078] INFO: Starting instance '<Instance #5 of CommandTask DemoTask>'...
    [2010/12/17 05:38:41.454383] INFO: Instance '<Instance #5 of CommandTask DemoTask>' ended with status SUCCESS.

Congratulations, you've run your first task!  To see the output, look at the log file in norc/logs/tasks/CommandTask/DemoTask/DemoTask-1, which should look like this:

    [2010/12/17 05:38:21.391439] INFO: Starting <Instance #1 of CommandTask DemoTask>.
    Executing command...
    $ echo 'Demo successful!'
    Demo successful!
    [2010/12/17 05:38:21.404867] INFO: Task ended with status SUCCESS.

Fin!
