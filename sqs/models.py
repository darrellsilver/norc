
import pickle

from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from django.contrib.contenttypes.models import ContentType

from norc.core.models import Queue
from norc.settings import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY

class SQSQueue(Queue):
    
    class Meta:
        app_label = 'sqs'
        db_table = 'norc_sqsqueue'
    
    def __init__(self, *args, **kwargs):
        Queue.__init__(self, *args, **kwargs)
        c = SQSConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        self.queue = c.lookup(self.name)
        if not self.queue:
            self.queue = c.create_queue(self.name, 1)
        self.connection = c
    
    @staticmethod
    def get_item(content_type_pk, content_pk):
        ct = ContentType.objects.get(pk=content_type_pk)
        return ct.get_object_for_this_type(pk=content_pk)
    
    # This has weird effects because SQS is crap.
    # def peek(self):
    #     message = self.queue.read(0)
    #     if message:
    #         return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def pop(self):
        message = self.queue.read()
        if message:
            self.queue.delete_message(message)
            return SQSQueue.get_item(*pickle.loads(message.get_body()))
    
    def push(self, item):
        Queue.validate(item)
        content_type = ContentType.objects.get_for_model(item)
        body = (content_type.pk, item.pk)
        message = self.queue.new_message(pickle.dumps(body))
        self.queue.write(message)
    
    def count(self):
        return self.queue.count()
    
