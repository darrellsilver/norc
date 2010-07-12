
#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


class Envies(object): #for some reason the word Environments caused trouble
    class BaseEnvironment(object):
        def __getitem__(self, attr):
            #makes this class respond to BaseEnvironment['key_name']
            return getattr(self,attr)
        DATABASE_ENGINE = 'mysql'
        NORC_CODE_ROOT = 'git://github.com/darrellsilver/norc.git'
        NORC_EMAIL_ALERTS_TO = []
        NORC_EMAIL_ALERTS = False
        DATABASE_HOST = 'localhost'
        DATABASE_PORT = '3306'
        EMAIL_HOST_USER = ''
        EMAIL_USE_TLS = 'True'
        EMAIL_PORT = '587'
        EMAIL_HOST = 'smtp.gmail.com'
        DEBUG = False
        TEMPLATE_DEBUG = False
        LOGGING_DEBUG = False
    class max_env(BaseEnvironment):
        ADMINS = (('Max', 'max@perpetually.com'),)
        NORC_LOG_DIR = '/usr/local/norc/log'
        NORC_TMP_DIR = '/usr/local/norc/tmp'
        TIME_ZONE = 'America/New-York'
        DATABASE_NAME = 'norc_db'
        DATABASE_USER = 'max'
        DEBUG = False
    class darrell_env(BaseEnvironment):
        ADMINS = ((),)
        NORC_LOG_DIR = '/Users/darrell/projects/norc/logs'
        NORC_TMP_DIR = '/Users/darrell/projects/norc/tmp'
        TIME_ZONE = 'America/New-York'
        DATABASE_NAME = 'norc'
        DATABASE_USER = 'norc_user'

# bad hack code duplication from permalink/all_environments,
# but this is somewhat better.
import os

# Determine the environment.
try:
    if not os.environ.get('NORC_ENVIRONMENT'):
        raise Exception("'NORC_ENVIRONMENT' Must be specified in your enviornment")
    ENV =  Envies.__dict__[os.environ.get('NORC_ENVIRONMENT')]()
except KeyError, ke:
    raise Exception("Unknown NORC_ENVIRONMENT '%s'" % (os.environ.get('NORC_ENVIRONMENT')))

