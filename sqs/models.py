
import pickle

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from django.contrib.contenttypes.models import ContentType

from norc.core.models import Queue
from norc.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class SQSQueue(Queue):
    
    class Meta:
        app_label = 'sqs'
    
    def __init__(self, *args, **kwargs):
        Queue.__init__(self, *args, **kwargs)
        c = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = c.lookup(self.name)
        if not self.queue:
            self.queue = c.create_queue(self.name, 1)
        self.connection = c
    
    @staticmethod
    def get_item(content_type_id, content_id):
        ct = ContentType.objects.get(id=content_type_id)
        return ct.get_object_for_this_type(id=content_id)
    
    def peek(self):
        message = self.queue.read(0)
        if message:
            return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def pop(self):
        message = self.queue.read()
        if message:
            self.queue.delete_message(message)
            return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def push(self, item):
        content_type = ContentType.objects.get(
            model=item.__class__.__name__.lower(),
            app_label=item.__class__._meta.app_label)
        body = (content_type.id, item.id)
        message = self.queue.new_message(pickle.dumps(body))
        self.queue.write(message)
    
    def count(self):
        return self.queue.count()
    
