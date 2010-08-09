
from norc.core.constants import QUEUES

class Queue(Model):
    """Abstract concept of a queue to be used for """
    class Meta:
        app_label = 'core'
        abstract = True
    
    name = CharField()
    priority = PositiveIntegerField()
    
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
    
    next = property(_get_next)
    def _get_next(self):
        return self.items[0]
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        try:
            return self.items[0].item
        except IndexError:
            return None
    
    def pop(self):
        """Retrieves the next item and removes it from the queue.
        
        If the queue is empty, this will block until an item appears.
        
        """
        next = None
        while next == None:
            try:
                next = self.items[0]
            except IndexError:
                time.sleep(DBQueue.FREQUENCY)
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
    
