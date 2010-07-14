
# Settings for Norc, including all Django configuration.

import os

from norc.settings_local import *

# Norc's directory (assumed to be the parent folder of this file).
NORC_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# The path to Norc on GitHub.
NORC_CODE_ROOT = 'git://github.com/darrellsilver/norc.git'

class Envs(type):
    
    ALL = {}
    
    def __init__(cls, name, bases, dct):
        super(Envs, cls).__init__(name, bases, dct)
        Envs.ALL[name] = cls
    
    def __getitem__(self, attr):
        """Allows dictionary-style lookup of attributes."""
        return getattr(self, attr)

class BaseEnv(object):
    """Basic Norc setting defaults.
    
    This serves as a base class from which specific environments
    classes can inherit default settings.  Not meant to be instantiated.
    
    """
    __metaclass__ = Envs
    
    # Norc settings.
    NORC_LOG_DIR = os.path.join(NORC_DIRECTORY, 'log/')
    NORC_TMP_DIR = os.path.join(NORC_DIRECTORY, 'tmp/')
    
    # Important Django settings.
    ADMINS = ((),)
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'norc.core',
        'norc.web',
    )
    
    # Database configuration.
    DATABASE_ENGINE = 'mysql'
    DATABASE_NAME = 'norc_db'
    DATABASE_USER = 'max'
    DATABASE_HOST = 'localhost'
    DATABASE_PORT = '3306'
    
    # Email configuration; commented out for future use.
    # EMAIL_HOST = 'smtp.gmail.com'
    # EMAIL_HOST_USER = ''
    # EMAIL_PORT = '587'
    # EMAIL_USE_TLS = 'True'
    
    # Debugging switches.
    DEBUG = False
    LOGGING_DEBUG = False
    TEMPLATE_DEBUG = False
    
    # Miscellaneous Django settings.
    INTERNAL_IPS = ('127.0.0.1',)
    MEDIA_ROOT = os.path.join(NORC_DIRECTORY, 'static/')
    ROOT_URLCONF = 'norc.urls'
    SITE_ID = 1
    TEMPLATE_DIRS = ()
    TIME_ZONE = 'America/New-York'

class MaxEnv(BaseEnv):
    DATABASE_NAME = 'norc_db'
    DATABASE_USER = 'max'
    DEBUG = True
    INSTALLED_APPS = BaseEnv.INSTALLED_APPS + ('norc.sqs',)
    INTERNAL_IPS = ('127.0.0.1',)
    TEMPLATE_DIRS = (
        '/Library/Python/2.6/site-packages/debug_toolbar/templates/',
    )

class darrell_env(BaseEnv):
    NORC_LOG_DIR = '/Users/darrell/projects/norc/logs'
    NORC_TMP_DIR = '/Users/darrell/projects/norc/tmp'
    DATABASE_NAME = 'norc'
    DATABASE_USER = 'norc_user'

# Find the user's environment.
env_str = os.environ.get('NORC_ENVIRONMENT')
if not env_str:
    env_str = 'BaseEnv'
try:
    cur_env = Envs.ALL[env_str]
except KeyError, ke:
    raise Exception("Unknown NORC_ENVIRONMENT '%s'." % env_str)

def is_constant(s):
    return 

# Use the settings from that environment.
for s in dir(cur_env):
    # If the setting name is a valid constant, add it to globals.
    VALID_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
    if not s.startswith('_') and all(map(lambda c: c in VALID_CHARS, s)):
        globals()[s] = cur_env[s]
