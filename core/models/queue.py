
"""All queueing related models."""

import datetime, time

from django.db.models import (Model, Manager,
    BooleanField,
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
    """This metaclass is used to create a list of Queue implementations."""
    
    IMPLEMENTATIONS = []
    
    def __init__(self, name, bases, attrs):
        ModelBase.__init__(self, name, bases, attrs)
        if not self._meta.abstract:
            MetaQueue.IMPLEMENTATIONS.append(self)
    

class Queue(Model):
    """Abstract concept of a queue."""
    
    __metaclass__ = MetaQueue
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(unique=True, max_length=64)
    
    @staticmethod
    def get(name):
        for QueueClass in MetaQueue.IMPLEMENTATIONS:
            try:
                return QueueClass.objects.get(name=name)
            except Exception:
                pass
    
    # TODO: Unique names for queues should be enforced somehow around here.
    # def __init__(self, *args, **kwargs):
    #     print type(self)
    #     if type(self) == Queue:
    #         raise NotImplementedError("Can't instantiate Queue directly!")
    #     Model.__init__(self, *args, **kwargs)
    
    def peek(self):
        raise NotImplementedError
    
    def pop(self, timeout=None):
        raise NotImplementedError
    
    def push(self, item):
        raise NotImplementedError
    
    def count(self):
        raise NotImplementedError
    
    def __unicode__(self):
        return u"%s '%s'" % (self.__class__.__name__, self.name)
    
    __repr__ = __unicode__


class DBQueue(Queue):
    """A distributed queue implementation that uses the Norc database.
    
    In order to reduce database load, it is recommended to use an
    indepedent distributed queueing system, like Amazon's SQS.
    
    """
    class Meta:
        app_label = 'core'
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        try:
            return self.items.all()[0].item
        except IndexError:
            return None
    
    def pop(self):
        """Retrieves the next item and removes it from the queue."""
        try:
            next = self.items.all()[0]
        except IndexError:
            return None
        next.delete()
        return next.item
    
    def push(self, item):
        """Adds an item to the queue."""
        DBQueueItem.objects.create(dbqueue=self, item=item)
    
    def count(self):
        return self.items.count()


class DBQueueItem(Model):
    """An item in a DBQueue."""
    
    class Meta:
        app_label = 'core'
        ordering = ['id']
    
    # The queue this item is a part of.
    dbqueue = ForeignKey(DBQueue, related_name='items')
    
    # The item being enqueued.
    item_type = ForeignKey(ContentType)
    item_id = PositiveIntegerField()
    item = GenericForeignKey('item_type', 'item_id')
    
    # The datetime at which this item was enqueued.
    enqueued = DateTimeField(default=datetime.datetime.utcnow, db_index=True)
    
    def __unicode__(self):
        return u'DBQueueItem #%s, %s' % (self.id, self.enqueued)
        
