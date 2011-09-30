
"""All queueing related models."""

import datetime, time

from django.db.models.base import ModelBase
from django.db.models import (Model, Manager,
    BooleanField,
    CharField,
    DateTimeField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.models.task import AbstractInstance

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
            except QueueClass.DoesNotExist:
                pass
    
    @staticmethod
    def all_queues():
        return reduce(lambda a, b: a + b,
            [list(Q.objects.all()) for Q in MetaQueue.IMPLEMENTATIONS])
    
    @staticmethod
    def validate(item):
        assert isinstance(item, AbstractInstance), "Invalid queue item."
    
    def save(self, *args, **kwargs):
        """Performs a name uniqueness check before saving a new queue."""
        if not self.pk and Queue.get(self.name) != None:
            raise ValueError(
                "A queue with name %s already exists." % self.name)
        return super(Queue, self).save(*args, **kwargs)
    
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
        return u'<%s %s>' % (type(self).__name__, self.name)
    
    __repr__ = __unicode__


class DBQueue(Queue):
    """A distributed queue implementation that uses the Norc database.
    
    In order to reduce database load, it is recommended to use an
    indepedent distributed queueing system, like Amazon's SQS.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_dbqueue'
    
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
        Queue.validate(item)
        DBQueueItem.objects.create(dbqueue=self, item=item)
    
    def count(self):
        return self.items.count()


class DBQueueItem(Model):
    """An item in a DBQueue."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_dbqueueitem'
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
        return u'<DBQueueItem #%s, %s>' % (self.id, self.enqueued)
        
