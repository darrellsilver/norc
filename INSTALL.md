# Installing Norc

The goal of this install script is to setup a simple Norc environment that can run a sample Task.  Much of the power of Norc is in its extensibility beyond simple Task management, so the more hack-happy you are, the better!


## Environments tested for this example.
Other environments will probably work, but we've not tested too many different configurations.

 * Python 2.4.x, 2.5.x or 2.6.x.   We've tested on all these versions, 
 * Linux (Redhat Fedora 4) or OS X (Tiger, Leopard or Snow Leopard).
 * Django 1.0.  We haven't tested on Django 1.1, and it may just work. We're not doing anything tricky.
 * A semi-recent version of MySQL (5.x or greater).  If you're not using MySQL everything should still work.  You'll just have to replace the mysql steps with whatever database backend your using and change the configuration in Django's settings.py as necessary.


## Download:

        $ git clone git://github.com/darrellsilver/norc.git
        Initialized empty Git repository in /Users/darrell/projects/norc/install/norc/.git/
        remote: Counting objects: 90, done.
        remote: Compressing objects: 100% (88/88), done.
        remote: Total 90 (delta 40), reused 0 (delta 0)
        Receiving objects: 100% (90/90), 59.70 KiB, done.
        Resolving deltas: 100% (40/40), done.
        $

We'll be inside the norc/ directory for the rest of the tutorial.

        $ cd norc/


## Prepare the Database

We're creating a new account & database for this demo.  We've only tested on MySQL, but Norc should work on anything that Django supports.

Credentials:

        User: 'norc_demo'
        Password: 'norc'
        Schema: 'norc_demo_db'

## Configure settings.py & settings_local.py

settings_local.py contains private settings that should not be shared, and thus are kept in a file outside of Git.

Create settings_local.py by copying settings_local.py.example:

        $ cp -p settings_local.py.example settings_local.py

Edit the file to contains the proper credentials.  In this case:

        # Make this unique, and don't share it with anybody.
        SECRET_KEY = '-e_#)ou%u!et$d^*&40t4f2s3jdl@57g%*&h)'

        # Database password
        DATABASE_PASSWORD = 'norc'

        # Email password for account used to send TMS alerts
        EMAIL_HOST_PASSWORD = 'my_password_is_super_secure!'

        # Amazon *secret* S3 login info
        AWS_ACCESS_KEY_ID = '...'
        AWS_SECRET_ACCESS_KEY = '...'

Edit settings.py, which is stored in Git, with other settings.  Bold items are crucial and explained below:

 * **ADMINS**: This is Django's admins list. See the django docs for more details.
 * **TMS_CODE_ROOT**: The full path where you downloaded norc from GitHub
 * **TMS_LOG_DIR**: The full path where all logs of all Tasks in Norc should be stored
 * **TMS_TMP_DIR**: The full path to a directory used for any temp files created by Norc Tasks.  This variable is available in the environment to any command run in Norc.
 * **DATABASE_NAME**: Your DB schema
 * **DATABASE_USER**: Your DB login user
 * **EMAIL_{USE_TLS, HOST, HOST_USER, PORT}**: Service from which all email alerts in Norc will be sent.
 * **TMS_EMAIL_{ALERTS, ALERTS_TO}**: Send alerts on Task failure, and to whom.

The full config file:

        ALL_ENVIRONMENTS = {
            #
            # Environment settings that aren't private go here.
            #
            # This structure replaces Django's default settings.py with this
            # because it allows us to more easily support multiple environments
            #
            # This variable must be defined in the shell environment as 'norc_ENVIRONMENT'
            'darrell-dsmbp' : {
                # Basic Django config
                'DEBUG' : os.environ.get('NORC_DEBUG', False) in ('True', 'true')
                , 'TEMPLATE_DEBUG' : os.environ.get('NORC_TEMPLATE_DEBUG', False) in ('True', 'true')
                , 'LOGGING_DEBUG' : os.environ.get('NORC_LOGGING_DEBUG', False) in ('True', 'true')
                , 'ADMINS' : (('Darrell', 'contact@darrellsilver.com'),)
                , 'TIME_ZONE' : 'America/New-York'
                , 'TMS_CODE_ROOT' : '/Users/darrell/projects/norc/demo/norc'
                , 'TMS_LOG_DIR' : '/Users/darrell/projects/norc/demo/norc_log'
                , 'TMS_TMP_DIR' : '/Users/darrell/projects/norc/demo/norc_tmp'
        
                # DB connection
                , 'DATABASE_ENGINE' : 'mysql'
                , 'DATABASE_NAME' : 'norc_demo_db'
                , 'DATABASE_USER' : 'norc_demo'
                , 'DATABASE_HOST' : ''
                , 'DATABASE_PORT' : ''
        
                # address to use for all outgoing emails (failure alerts, etc)
                # this account is the FROM address
                , 'EMAIL_USE_TLS' : True
                , 'EMAIL_HOST' : 'smtp.gmail.com'
                , 'EMAIL_HOST_USER' : 'darrell@perpetually.com'
                , 'EMAIL_PORT' : 587
        
                # TMS alert handling
                # send alerts?
                , 'TMS_EMAIL_ALERTS' : True
                # to whom should alerts be sent
                , 'TMS_EMAIL_ALERTS_TO' : ['support@example.com']
            },
        }


## Setup the run environment

In your shell environment, Django & Norc require a few variables:

        # The environment used in the settings.py file, as defined above.
        export NORC_ENVIRONMENT='darrell-dsmbp'
        # Import path to the settings.py file
        export DJANGO_SETTINGS_MODULE='norc.settings'
        # Norc source code must be in your PYTHONPATH
        export PYTHONPATH=$PYTHONPATH:/Users/darrell/projects/norc/demo
        # Norc has a few binaries that need to be in your PATH
        # As shipped, these are symbolic links, and can thus can be moved from 
        # this location if you wish.
        export PATH=$PATH:/Users/darrell/projects/norc/demo/norc/bin

## Sync Django models to the DB

This is also the first time you'll be running the full app, so any errors in configuration so far will show up here.

This is the output log of Django creating the tables in MySQL.  Because we've also never setup an admin account, Django also prompts us to setup an admin user.

        $ python manage.py syncdb
        Creating table django_admin_log
        Creating table auth_permission
        Creating table auth_group
        Creating table auth_user
        Creating table auth_message
        Creating table django_content_type
        Creating table django_session
        Creating table django_site
        Creating table norc_job
        Creating table norc_taskdependency
        Creating table norc_iteration
        Creating table norc_taskrunstatus
        Creating table norc_taskclassimplementation
        Creating table norc_resourceregion
        Creating table norc_resource
        Creating table norc_resourcereservation
        Creating table norc_taskresourcerelationship
        Creating table norc_regionresourcerelationship
        Creating table norc_daemonstatus
        Creating table norc_startiteration
        Creating table norc_generic_runcommand
        Creating table norc_generic_scheduledruncommand
        Creating table norc_sqstaskrunstatus

        You just installed Django's auth system, which means you don't have any superusers defined.
        Would you like to create one now? (yes/no): yes
        Username (Leave blank to use 'darrell'): 
        E-mail address: darrell@perpetually.com
        Password: 
        Password (again): 
        Superuser created successfully.
        Installing index for admin.LogEntry model
        Installing index for auth.Permission model
        Installing index for auth.Message model
        Installing index for core.TaskDependency model
        Installing index for core.Iteration model
        Installing index for core.TaskRunStatus model
        Installing index for core.ResourceReservation model
        Installing index for core.TaskResourceRelationship model
        Installing index for core.RegionResourceRelationship model
        Installing index for core.NorcDaemonStatus model
        Installing index for core.StartIteration model
        Installing index for core.RunCommand model
        Installing index for core.ScheduledRunCommand model
        Installing index for sqs.SQSTaskRunStatus model


## Start up Django development enviroment

Now that we've created the tables in the DB, we can start the Django development server:

        $ python manage.py runserver  
        Validating models...
        0 errors found

        Django version 1.0-rc_1-SVN-unknown, using settings 'norc.settings'
        Development server is running at http://127.0.0.1:8000/
        Quit the server with CONTROL-C.

When you go to

        http://localhost:8000/

you should see the "Django administration" login screen, on which you can login using your Django admin password.


## Add some basic data to the DB

* Home > Core > Jobs > Add: **DEMO_JOB**
* Home > Core > Resource regions > Add: **MY_REGION**
* Home > Core > Resources > Add: **DATABASE_CONNECTION**

We want MY_REGION to offer 10 DATABASE_CONNECTION Resources

* Home > Core > Region resource relationships > Add:
   * Region: MY_REGION, Resource: DATABASE_CONNECTION, Units in Existence: 10
* Home > Core > Task class implementations > Add:
   * Status: **ACTIVE**
   * Library name: **norc.core.models**
   * Class name: **RunCommand**

(In the future this should be automated as part of an install process)


## Start a Daemon

Now we're ready to start a Norc Daemon!  In a new terminal session, or the same one if you want to quit the Django dev server, run 

        $ tmsdctl --status
        Status as of 10/28/2009 22:25:56
        No INTERESTING tms daemons

This indicates that no Daemons are running, which should be obvious because we haven't started any.  So, let's start one:

        $ tmsd --region MY_REGION
        [10/28/2009 22:27:14.059850] (info) TMSD stderr & stdout will be in '/Users/darrell/projects/norc/demo/norc_log/_tmsd/tmsd.1'

Output for this daemon, starting of each task and errors, will be sent to the file indicated.  "Ctl-C" will exit the daemon.  But before exiting, rerun tmsdctl.py and you'll see:

        $ tmsdctl --status
        Status as of 10/28/2009 22:27:23
        1 INTERESTING tms daemon(s):
        ID    Type      Region          Host     PID   Running   Success   Error    Status               Started   Ended
        1      TMS   MY_REGION   DSmbp.local   12084         0         0       0   RUNNING   2009-10-28 22:27:14       -


## Define A New Task

We'll define a simple Task that executes on the command line and prints out the current time:

* Home > Core > Run commands > Add: 
   * Task Type: **PERSISTENT** (This Task will be run again and again, rather than a one-off)
   * Job: **DEMO_JOB** (As we defined earlier)
   * Status: **ACTIVE**
   * Cmd: **echo "Hello, Norc! Local time is $LOCAL_MM/DD/YYYY"**
   * Nice: **3** (We'll arbitrarily 'nice' this process to 3.
   * Timeout: **60** (We'll timeout after 1 minute, though this Task should be almost instant)

Because Norc uses the database, it automatically adds itself as consuming 1 DATABASE_CONNECTION Resource.  After adding this Task, this can be seen (or changed, I suppose) in 

 * Home > Core > Task resource relationships

## Run A Task

In order to run our Task, we must have

 1. A running Daemon
 2. A Task that is due to run
 3. A running Iteration

We've set up 1 & 2, so we now have to do 3.  The simplest way to do this is to manually add a new Iteration from the Django admin system:

 * Home > Core > Iterations > Add:
    * Job: **DEMO_JOB**
    * Status: **RUNNING**
    * Iteration type: **EPHEMERAL** (this Iteration of this Job will run once and end)

Once this is done, our new Task will run.  So, rerun tmsdctl shows:

        $ tmsdctl --status
        Status as of 10/28/2009 23:05:02
        1 INTERESTING tms daemon(s):
        ID    Type      Region          Host     PID   Running   Success   Error    Status               Started   Ended
        1      TMS   MY_REGION   DSmbp.local   12084         0         1       0   RUNNING   2009-10-28 22:27:14       -

And if we show details for this Daemon, we'll see a bit more detail:

        $ tmsdctl --status --details 1 --filter ALL
        Status as of 10/28/2009 23:05:02
        1 INTERESTING tms daemon(s):
        ID    Type      Region          Host     PID   Running   Success   Error    Status               Started   Ended
        1      TMS   MY_REGION   DSmbp.local   12084         0         1       0   RUNNING   2009-10-28 22:27:14       -
        
        TMS Daemon 3 (ENDED) manages 1 task(s):

        Job:Task                  Status               Started                 Ended
        DEMO_JOB:RunCommand.1    SUCCESS   2009-10-28 23:03:41   2009-10-28 23:03:41


And we can see the log file for this Task:

        $ cat ../norc_log/DEMO_JOB/RunCommand.1
        [10/28/2009 23:03:41.104560] (info) Running Task 'RunCommand.1'
        [10/28/2009 23:03:41.104689] (info) Running command 'nice -n 3 echo "Hello, Norc! Local time is 10/28/2009"'
        Hello, Norc! Local time is 10/28/2009
        [10/28/2009 23:03:41.211730] (info) Task 'RunCommand.1' succeeded.


This log shows some basic info in the header & footer about the Task, generated by Norc.  Our Task was very simple, it just printed out a line:

        Hello, Norc! Local time is 10/28/2009

As a special bonus we used Norc's variable substitution feature to replace the hard coded string

        $LOCAL_MM/DD/YYYY

with 

        10/28/2009

at run-time.

The full list of these variables, which could be easily expanded, can be seen direclty in Norc's source code:

        norc/core/models.py > RunCommand() > interpret_vars()

Now we shut off our daemon:

        $ tmsdctl --status --stop 1
        Status as of 10/28/2009 23:05:02
        1 INTERESTING tms daemon(s):
        ID    Type      Region          Host     PID   Running   Success   Error          Status               Started   Ended
        1      TMS   MY_REGION   DSmbp.local   12084         0         1       0   STOPREQUESTED   2009-10-28 22:27:14       -

After which our daemon stops, and the process ends:

        $ tmsdctl --status --det 1 --filter all
        Status as of 10/28/2009 23:15:37
        1 ALL tms daemon(s):
        ID    Type      Region          Host     PID   Running   Success   Error   Status               Started                 Ended
        4      TMS   MY_REGION   DSmbp.local   12671         0         0       0    ENDED   2009-10-28 22:27:14   2009-10-28 23:14:49


Fin!
