
from norc.core.models.task import *
from norc.core.models.job import *
from norc.core.models.schedules import *
from norc.core.models.scheduler import *
from norc.core.models.queue import *
from norc.core.models.executor import *

# __all__ = ['Task', 'Instance', 'JobInstance', 'Schedule', 'Scheduler',
#     'Queue', 'DBQueue', 'Executor']
from norc import settings

# map(__import__, settings.EXTERNAL_CLASSES)

for s in settings.EXTERNAL_CLASSES:
    try:
        __import__(s)
    except:
        print "Failed to import %s." % s
