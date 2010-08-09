
"""All queueing related models."""

import datetime, time

from norc.core import TimedoutException
from norc.core.constants import QUEUES

class QueueName(Model):
    """Name of a queue and a link to its implementation.
    
    Used to enforce all queues having unique names; should never
    need to be known about from outside this file.
    
    """
    class Meta:
        app_label = 'core'
    
    name = CharField(unique=true)
    impl_type = ForeignKey(ContentType)
    impl_id = PositiveIntegerField()
    impl = GenericForeignKey('impl_type', 'impl_id')
    

class Queue(Model):
    """Abstract concept of a queue."""
    
    @staticmethod
    def get(name):
        try:
            return QueueName.objects.get(name=name)
        except QueueName.DoesNotExist:
            return None
    
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField(unique=true)
    
    def __init__(self, name):
        Model.__init__(name=name)
        QueueName(name=name, impl=self).save()
        self.save()
    
    def peek(self):
        raise NotImplementedError
    
    def pop(self):
        raise NotImplementedError
    
    def push(self, item):
        raise NotImplementedError
    

class DBQueue(Queue):
    """A distributed queue implementation that uses the Norc database.
    
    In order to reduce database load, it is recommended to use an
    indepedent distributed queueing system, like Amazon's SQS.
    
    """
    class Meta:
        app_label = 'core'
    
    # How frequently the database should be checked when waiting for an item.
    FREQUENCY = 1
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        try:
            return self.items[0].item
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
                next = self.items[0]
            except IndexError:
                time.sleep(DBQueue.FREQUENCY)
                waited += DBQueue.FREQUENCY
                if timeout and waited > timeout:
                    raise TimeoutException()
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
    
