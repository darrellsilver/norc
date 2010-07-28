
"""

Contains some functions useful throughout the sqs module as well as the
data definitions for the SQS portions of the web status page.

"""

import pickle
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message

from norc.norc_utils import parsing
from norc.web.data_defs import DataDefinition, DATA_DEFS
from norc.settings import AWS_ACCESS_KEY_ID as AWS_ID, \
                          AWS_SECRET_ACCESS_KEY as AWS_KEY

# for st in SQSTASK_IMPLEMENTATIONS:
#     path = st.split('.')
#     name = path.pop()
#     path = '.'.join(path)
#     setattr(pickle, name, __import__(path, fromlist=name))

def push_task(task, queue):
    """Pushes a task into an SQS queue.
    
    task should be an SQSTask object.
    queue can be either a boto queue object or a string with the queue name.
    
    """
    if type(queue) == str:
        queue = SQSConnection(AWS_ID, AWS_KEY).lookup(queue)
    m = Message()
    # m.set_body(pickle.dumps(task))
    m.set_body(pickle.dumps(task.__dict__))
    queue.write(m)

def pop_task(queue):
    """Retrieves an SQSTask from the given SQS queue.
    
    queue can be either a boto queue object or a string with the queue name.
    Returns None if no message is found in the given queue.
    
    """
    # from norc.sqs.push_task import DemoSQSTask
    # globals()['DemoSQSTask'] = DemoSQSTask
    if type(queue) == str:
        queue = SQSConnection(AWS_ID, AWS_KEY).lookup(queue)
    m = queue.read()
    if not m:
        return None
    queue.delete_message(m)
    # return pickle.loads(m.get_body())
    dict_ = pickle.loads(m.get_body())
    path = dict_.pop('LIBRARY_PATH')
    class_ = parsing.parse_class(path)
    task = class_(**dict_)
    return task

# Data definitions for the web status display.

tasks_def = DATA_DEFS['tasks']

DataDefinition(
    key='sqstasks',
    since_filter=tasks_def.since_filter,
    order_by=tasks_def.order_by,
    data={
        'id': lambda trs, _: trs.id,
        'task_id': lambda trs, _: str(trs.get_task_id()),
        'status': lambda trs, _: trs.get_status(),
        'started': lambda trs, _: trs.date_started,
        'ended': lambda trs, _: trs.date_ended if trs.date_ended else '-',
    },
)

DataDefinition(
    key='sqsqueues',
    retrieve=lambda: SQSConnection(AWS_ID, AWS_KEY).get_all_queues(),
    data={
        'id': lambda q, _: q.url.split('/')[-1],
        'num_items': lambda q, _: q.count(),
        'timeout': lambda q, _: q.get_timeout(),
    },
)
