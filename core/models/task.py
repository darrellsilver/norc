
"""The core data model"""

from django.db.models import (Model,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    SmallPositiveIntegerField)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)
from django.conf import settings

from norc.norc_utils.log import make_log

class Task(Model):
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(max_length=128, unique=True)
    description = CharField(max_length=512, blank=True, default='')
    date_added = DateTimeField(auto_now_add=True)
    timeout = IntegerField(default=0)
    

class Iteration(Model):
    
    STATUSES = {
        1: 'RUNNING',
        2: 'SUCCESS',
        3: 'ERROR',
        4: 'TIMEDOUT',
        # 5: 'RETRY',
        # 6: 'CONTINUE',
        # 7: 'SKIPPED',
    }
    
    task = GenericForeignKey(...)
    status = SmallPositiveIntegerField(default=1,
        choices=[(k, v.title()) for k, v in Iteration.STATUSES.iteritems()])
    date_started = DateTimeField(default=datetime.datetime.utcnow)
    date_ended = DateTimeField(null=True)
    daemon = ForeignKey()
    # status = property...
    

class Schedule(Model):
    
    STATUSES = {
        1: 'ACTIVE',
        2: 'COMPLETE',
    }
    
    next = DateTimeField(null=True)
    repetitions = PositiveIntegerField()
    delay = PositiveIntegerField()
    
