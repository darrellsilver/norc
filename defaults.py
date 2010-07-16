
import os

# Norc's directory (assumed to be the parent folder of this file).
NORC_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
# The path to Norc on GitHub.
NORC_CODE_ROOT = 'git://github.com/darrellsilver/norc.git'

class Envs(type):
    """Meta class that collects a list of all implementations of BaseEnv."""
    
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
    # Lets you switch the prefix on the model tables easily.
    DB_TABLE_PREFIX = 'norc'
    
    # Important Django settings.
    ADMINS = ()
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
    # Name and user MUST be overwritten by a local environment!
    DATABASE_NAME = ''
    DATABASE_USER = ''
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
