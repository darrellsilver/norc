

class Queue(Model):
    
    class Meta:
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
    
    next = property(_get_next)
    def _get_next(self):
        return self.items[0]
    
    

class DBQueueItem(Model):
    
    class Meta:
        ordering = ['enqueued']
    
    dbqueue = ForeignKey(DBQueue, related_name='items')
    iter_type = ForeignKey(ContentType)
    iter_id = PositiveIntegerField()
    iteration = GenericForeignKey('iter_type', 'iter_id')
    enqueued = DateTimeField(defaiult=datetime.datetime.now)