# Norc Install

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

We'll be inside the norc/ directory for the rest of the tutorial.

        $ cd norc/
        $ cp -p settings_local.py.example settings_local.py         


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
 * **DATABASE_{USE_TLS, HOST, HOST_USER, PORT}**: Service from which all email alerts in Norc will be sent.
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
                , 'TMS_CODE_ROOT' : '/Users/darrell/projects/norc/demo/norc/'
                , 'TMS_LOG_DIR' : '/Users/darrell/projects/norc/demo/norc/'
                , 'TMS_TMP_DIR' : '/Users/darrell/projects/norc/demo/norc/'
        
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


