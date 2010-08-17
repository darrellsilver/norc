
import pickle

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from django.contrib.contenttypes.models import ContentType

from norc.core.models import Queue
from norc.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class SQSQueue(Queue):
    
    class Meta(Queue.Meta):
        app_label = 'sqs'
    
    def __init__(self, *args, **kwargs):
        Queue.__init__(self, *args, **kwargs)
        c = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = c.lookup(self.name)
        if not self.queue:
            self.queue = c.create_queue(self.name, 1)
    
    def get_item(content_type, content_id):
        model = ContentType.objects.get(id=content_type)
        return model.objects.get(id=content_id)
    
    def peek(self):
        message = self.queue.read()
        if message:
            return self.get_item(*pickle.loads(message.get_body()))
    
    def pop(self, timeout=None):
        message = self.queue.read()
        if message:
            self.queue.delete_message(message)
            return self.get_item(*pickle.loads(m.get_body()))
    
    def push(self, item):
        content_type = ContentType.objects.get(
            name=item.__class__.__name__)
        print content_type
        body = pickle.dumps((content_type, item.id))
        message = self.queue.new_message(body)
        # self.queue.write(message)
    
