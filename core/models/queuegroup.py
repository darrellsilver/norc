
from django.db.models import Model, ForeignKey, PositiveIntegerField
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import \
    GenericRelation, GenericForeignKey

from norc.core.models.queue import Queue

class QueueGroup(Queue):
    """A group of Norc queues."""
    
    class Meta:
        app_label = "core"
        db_table = "norc_queuegroup"
    
    @property
    def queues(self):
        return [i.queue for i in self.items.all()]
    
    def peek(self):
        """Retrieves the next item but does not remove it from the queue.
        
        Returns None if the queue is empty.
        
        """
        for q in self.queues:
            try:
                i = q.pop()
                if i != None:
                    return i
            except:
                pass
        return None
    
    def pop(self):
        """Retrieves the next item and removes it from the queue."""
        for q in self.queues:
            try:
                i = q.pop()
                if i != None:
                    return i
            except:
                pass
        return None
    
    def count(self):
        return sum([q.count() for q in self.queues])
    

class QueueGroupItem(Model):
    """Maps queues to QueueGroups."""
    
    class Meta:
        app_label = "core"
        db_table = "norc_queuegroupitem"
        ordering = ["priority"]
        unique_together = [["queue_type", "queue_id"],
            ["queue_type", "queue_id", "priority"]]
    
    group = ForeignKey(QueueGroup, related_name="items")
    
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey("queue_type", "queue_id")
    
    priority = PositiveIntegerField()
    
    def __unicode__(self):
        return u'<G:%s Q:%s P:%s>' % (self.group, self.queue, self.priority)
    
