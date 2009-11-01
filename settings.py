# Django settings for NORC project.

#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#     * 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#



import os
from norc.settings_local import *


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
        , 'TMS_CODE_ROOT' : '/Users/darrell/projects/permalink/src/'
        , 'TMS_LOG_DIR' : '/Users/darrell/projects/permalink/tms_log'
        , 'TMS_TMP_DIR' : '/Users/darrell/projects/permalink/tms_tmp'
        
        # DB connection
        , 'DATABASE_ENGINE' : 'mysql'
        , 'DATABASE_NAME' : 'perpetually_dev'
        , 'DATABASE_USER' : 'permalink'
        , 'DATABASE_HOST' : ''
        , 'DATABASE_PORT' : ''
        
        # address to use for all outgoing emails (failure alerts, etc)
        # this account is the FROM address
        , 'EMAIL_USE_TLS' : True
        , 'EMAIL_HOST' : 'smtp.gmail.com'
        , 'EMAIL_HOST_USER' : 'support@perpetually.com'
        , 'EMAIL_PORT' : 587
        
        # TMS alert handling
        # send alerts?
        , 'TMS_EMAIL_ALERTS' : False
        # to whom should alerts be sent
        , 'TMS_EMAIL_ALERTS_TO' : ['darrellsilver@gmail.com']
    },
}

#
# Determine the environment
#

try:
    if not os.environ.get('NORC_ENVIRONMENT'):
        raise Exception("'NORC_ENVIRONMENT' Must be specified in your enviornment")
    ENV = ALL_ENVIRONMENTS[os.environ.get('NORC_ENVIRONMENT')]
except KeyError, ke:
    raise Exception("Unknown NORC_ENVIRONMENT '%s'" % (os.environ.get('NORC_ENVIRONMENT')))




# Debug creates small memory leaks, storing all SQL queries in memory
DEBUG = ENV['DEBUG']
TEMPLATE_DEBUG = ENV['TEMPLATE_DEBUG']

ADMINS = ENV['ADMINS']

MANAGERS = ADMINS

DATABASE_ENGINE = ENV['DATABASE_ENGINE']
DATABASE_NAME = ENV['DATABASE_NAME']
DATABASE_USER = ENV['DATABASE_USER']
DATABASE_HOST = ENV['DATABASE_HOST']
DATABASE_PORT = ENV['DATABASE_PORT']

EMAIL_USE_TLS = ENV['EMAIL_USE_TLS']
EMAIL_HOST = ENV['EMAIL_HOST']
EMAIL_HOST_USER = ENV['EMAIL_HOST_USER']
EMAIL_PORT = ENV['EMAIL_PORT']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = ENV['TIME_ZONE']

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.middleware.transaction.TransactionMiddleware',
)

ROOT_URLCONF = 'norc.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(ENV['TMS_CODE_ROOT'], 'permalink/django_html'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'norc.core',
    'norc.sqs',
)

#
# norc specific settings
#

# TMS alert handling
TMS_EMAIL_ALERTS = ENV['TMS_EMAIL_ALERTS']
TMS_EMAIL_ALERT_TO = ENV['TMS_EMAIL_ALERTS_TO']

LOGGING_DEBUG = ENV['LOGGING_DEBUG']
TMS_LOG_DIR = ENV['TMS_LOG_DIR']
TMS_TMP_DIR = ENV['TMS_TMP_DIR']

#
