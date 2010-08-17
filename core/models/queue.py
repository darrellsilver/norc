
"""All queueing related models."""

import datetime, time

from django.db.models import (Model, Manager,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core import TimedoutException
from norc.norc_utils.django_extras import queryset_exists

from django.db.models.base import ModelBase

class MetaQueue(ModelBase):
    
    IMPLEMENTATIONS = []
    
    def __init__(self, name, bases, attrs):
        ModelBase.__init__(self, name, bases, attrs)
        if name != 'Queue':
            MetaQueue.IMPLEMENTATIONS.append(self)
    

class Queue(Model):
    """Abstract concept of a queue."""
    
    __metaclass__ = MetaQueue
    
    # Note: I don't know if this is actually going to be needed at all.
    @staticmethod
    def get(name):
        for QueueClass in MetaQueue.IMPLEMENTATIONS:
            try:
                return QueueClass.objects.get(name=name)
            except Exception:
                pass
            
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(unique=True, max_length=64)
    
    def peek(self):
        raise NotImplementedError
    
    def pop(self, timeout=None):
        raise NotImplementedError
    
    def push(self, item):
        raise NotImplementedError
    
    def __unicode__(self):
        return u"%s '%s'" % (self.__class__.__name__, self.name)
    
    __repr__ = __unicode__


class DBQueue(Queue):
    """A distributed queue implementation that uses the Norc database.
    
    In order to reduce database load, it is recommended to use an
    indepedent distributed queueing system, like Amazon's SQS.
    
    """
    
    # How frequently the database should be checked when waiting for an item.
    FREQUENCY = 1
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        try:
            return self.items.all()[0].item
        except IndexError:
            return None
    
    def pop(self, timeout=None):
        """Retrieves the next item and removes it from the queue.
        
        If the queue is empty, this will block until an item appears.
        
        """
        next = None
        waited = 0
        while next == None:
            try:
                next = self.items.all()[0]
            except IndexError:
                time.sleep(DBQueue.FREQUENCY)
                waited += DBQueue.FREQUENCY
                if timeout and waited > timeout:
                    return None
        next.delete()
        return next.item
    
    def push(self, item):
        """Adds an item to the queue."""
        DBQueueItem(dbqueue=self, item=item).save()
    
class DBQueueItem(Model):
    """An item in a DBQueue."""
    
    class Meta:
        app_label = 'core'
        ordering = ['enqueued']
    
    # The queue this item is a part of.
    dbqueue = ForeignKey(DBQueue, related_name='items')
    
    # The item being enqueued.
    item_type = ForeignKey(ContentType)
    item_id = PositiveIntegerField()
    item = GenericForeignKey('item_type', 'item_id')
    
    # The datetime at which this item was enqueued.
    enqueued = DateTimeField(default=datetime.datetime.utcnow)
    
