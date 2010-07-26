
"""Settings for Norc, including all Django configuration.

Defaults are stored in defaults.py, and local environments are stored in
settings_local.py to avoid version control.  This file merely pulls in
settings from those other files.

"""

import os

from norc.settings_local import *
from norc.defaults import Envs

# Find the user's environment.
env_str = os.environ.get('NORC_ENVIRONMENT')
if not env_str:
    raise Exception('You must set the NORC_ENVIRONMENT shell variable.')
try:
    cur_env = Envs.ALL[env_str]
except KeyError, ke:
    raise Exception("Unknown NORC_ENVIRONMENT '%s'." % env_str)

# Use the settings from that environment.
for s in dir(cur_env):
    # If the setting name is a valid constant, add it to globals.
    VALID_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ_'
    if not s.startswith('_') and all(map(lambda c: c in VALID_CHARS, s)):
        globals()[s] = cur_env[s]
