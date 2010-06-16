import pickle, datetime
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message
from norc import settings, sqs
from task_impls import *

def init_sqs():
    task = SQSTaskTest(datetime.datetime.utcnow())
    
    c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    q = c.create_queue('testq')
    m = Message()
    m.set_body(pickle.dumps(task))
    print m
    print q.write(m)
    
    print q.get_messages()


if __name__ == '__main__':
    init_sqs()

