
from norc.core.models import *

def make_task():
    return CommandTask.objects.create(
        name='Test_Task', command="echo 'Testing, 1 2 3.'")
    
def make_queue():
    return DBQueue.objects.create(name='Test_Queue')
    
