
## The goal of this install script is to setup a simple Norc environment that can run a sample Task.

### Environments tested for this example.
Other environments will probably work, but we've not tested too many different configurations.

 * Python 2.4.x, 2.5.x or 2.6.x.   We've tested on all these versions, 
 * Linux (Redhat Fedora 4) or OS X (Tiger, Leopard or Snow Leopard).
 * Django 1.0.  We haven't tested on Django 1.1, and it may just work. We're not doing anything tricky.
 * A semi-recent version of MySQL (5.x or greater).  If you're not using MySQL everything should still work.  You'll just have to replace the mysql steps with whatever database backend your using and change the configuration in Django's settings.py as necessary.

### Download:

        $ git clone git://github.com/darrellsilver/norc.git
        Initialized empty Git repository in /Users/darrell/projects/norc/install/norc/.git/
        remote: Counting objects: 90, done.
        remote: Compressing objects: 100% (88/88), done.
        remote: Total 90 (delta 40), reused 0 (delta 0)
        Receiving objects: 100% (90/90), 59.70 KiB, done.
        Resolving deltas: 100% (40/40), done.
        
        # we'll be inside the norc/ directory for the rest of the tutorial.
        $ cd norc/
        $ cp -p settings_local.py.example settings_local.py         


# Prepare the Database

We've only tested on MySQL, but Norc should work on anything that Django supports.

We're creating a new account & database for this demo:

        User: 'norc_demo'
        Password: 'norc'
        Schema: 'norc_demo_db'

# Configure settings.py & settings_local.py

settings_local.py contains private settings that should not be shared, and thus are kept in a file outside of source control.

Create settings_local.py by copying settings_local.py.example:

        $ cp -p settings_local.py.example settings_local.py


