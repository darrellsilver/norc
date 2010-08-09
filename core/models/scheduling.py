
from datetime import datetime, timedelta

from django.db.models import (Model,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    SmallPositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status

class Schedule(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    queue = ForeignKey('Queue')
    next = DateTimeField(null=True)
    repetitions = PositiveIntegerField()
    reps_left = PositiveIntegerField()
    delay = PositiveIntegerField()
    
    def __init__(self, task, queue, start=0, reps=1, delay=0):
        if not type(start) == datetime:
            start = datetime.utcnow() + timedelta(seconds=start)
        Model.__init__(self, task=task, queue=queue, next=start,
            repetitions=reps, reps_left=reps, delay=delay)
    

class Scheduler(object):
    
    class Meta:
        app_label = 'core'
    
    def __init__(self):
        
        pass
    
    def start(self):
        pass
    
