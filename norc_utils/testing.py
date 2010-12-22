
from norc.core.models import *

def make_task(name='TestTask'):
    return CommandTask.objects.create(
        name=name, command="echo 'Running: %s'" % name)

def make_instance():
    return Instance.objects.create(task=make_task())

def make_queue():
    return DBQueue.objects.create(name='Test_Queue')
    
