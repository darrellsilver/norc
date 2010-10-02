
"""External modules should access Norc data using these functions.

The main benefit currently is to prevent the occurence of a try block
everywhere data is needed, and to reduce the amount of code needed for
retrievals using consistent attributes.  Additionally, it prevents
external modules from having to query core classes directly.

"""

from django.contrib.contenttypes.models import ContentType

from norc.core.models import *
from norc.core.constants import Status, TASK_MODELS
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import untitle
from norc.norc_utils.django_extras import get_object

all = {}

def generate(data_set, report, params):
    ret_list = []
    for obj in data_set:
        obj_data = {}
        for key, func in report.data.iteritems():
            obj_data[key] = func(obj, **params)
        ret_list.append(obj_data)
    return ret_list

class Report(type):
    """A definition for the data of a status table on the frontend.
    
    Contains all the information needed for retrieving and organizing the
    data for displaying in a table on the status page.
    
    Required parameters:
    
    key         String which identifies this data.
    data        A dictionary whose keys represent columns in the table and
                whose values are functions which take an object and the GET
                dict from the AJAX request and return the desired data.
    
    Optional parameters:
    
    retrieve        Function which returns the basic set of data.  Needed
                    if the data is to have its own table.
    detail_key      String which identifies the type of data that expanding
                    a row in this table will reveal.
    details         Function which takes the ID of an object and the GET
                    params and returns the detail objects for that ID.
    since_filter    Function which takes data and a since date and filters
                    the data using that date.
    order_by        Function which takes data and an optional order string
                    and returns ordered data.
    
    """
    def __new__(cls, name, bases, dct):
        function = type(lambda: None)
        attr_getter = lambda a: lambda obj, **kws: getattr(obj, a)
        for k, v in dct.iteritems():
            if type(v) == function:
                dct[k] = staticmethod(v)
        for h in dct['headers']:
            k = untitle(h)
            if not k in dct['data']:
                dct['data'][k] = attr_getter(k)
        return type.__new__(cls, name, bases, dct)
    
    def __init__(self, name, bases, dct):
        type.__init__(self, name, bases, dct)
        if name != 'BaseReport':
            all[name] = self
        # if base:
        #     self = copy(REPORT[base])
        # for k, v in kwargs.iteritems():
        #     setattr(self, k, v)
        # DATA_DEFS[self.key] = self
    
    def __call__(self, id=None):
        return self.get(id) if id != None else self.get_all()
    
    # def __getattr__(self, *args, **kwargs):
    #     try:
    #         return super(Report, self).__getattr__(self, *args, **kwargs)
    #     except AttributeError:
    #         return None
    

def date_ended_since(query, since):
    if type(since) == str:
        since = parse_since(since)
    return query.exclude(ended__lt=since) if since else query

date_ended_order = lambda data, o: data.order_by(o if o else '-ended')
date_ended_getter = lambda obj, **kws: obj.ended if obj.ended else '-'

def _parse_content_ids(id_str):
    ct_id, obj_id = map(int, id_str.split('_'))
    ct = ContentType.objects.get(id=ct_id)
    return ct.get_object_for_this_type(id=obj_id)

def _find_ct(obj):
    return ContentType.objects.get_for_model(obj).id

class BaseReport(object):
    """Ideally, this would be replaced with a class decorator in 2.6."""
    __metaclass__ = Report
    get = lambda id: None
    get_all = lambda: None
    since_filter = lambda data, since: data
    order_by = lambda data, order: data
    details = {}
    headers = []
    data = {}

def _executor_instance_counter(executor, since, group):
    return executor.instances.since(since).status_in(group).count()

class executors(BaseReport):
    
    get = lambda id: get_object(Executor, id=id)
    get_all = lambda: Executor.objects.all()
    since_filter = date_ended_since
    order_by = date_ended_order
    
    details = {
        'instances': lambda id, since=None, status=None, **kws:
            executors.get(id).instances.since(since).status_in(status),
    }
    headers = ['ID', 'Queue', 'Queue Type', 'Host', 'PID', 'Running',
        'Succeeded', 'Failed', 'Started', 'Ended', 'Alive', 'Status']
    data = {
        'queue': lambda obj, **kws: obj.queue.name,
        'queue_type': lambda obj, **kws: obj.queue.__class__.__name__,
        'running': lambda obj, since, **kws:
            obj.instances.since(since).status_in('running').count(),
        'succeeded': lambda obj, since, **kws:
            obj.instances.since(since).status_in('succeeded').count(),
        'failed': lambda obj, since, **kws:
            obj.instances.since(since).status_in('failed').count(),
        'status': lambda obj, **kws: Status.NAME[obj.status],
        'ended': date_ended_getter,
        'alive': lambda obj, **kws: str(obj.alive),
    }
    

class schedulers(BaseReport):
    
    get = lambda id: get_object(Scheduler, id=id)
    get_all = lambda: Scheduler.objects.all()
    
    details = {
        'schedules': lambda id, **kws:
            Schedule.objects.filter(scheduler__id=id)
    }
    headers = ['ID', 'Active', 'Host', 'Heartbeat']
    data = {
        'active': lambda obj, **kws: str(bool(obj.active)),
    }

def _queue_failure_rate(obj, **kws):
    instances = Instance.objects.from_queue(obj)
    failed = instances.status_in('failed').count()
    total = instances.count()
    return '%.2f%%' % (100.0 * failed / total) if total > 0 else 'n/a'

class queues(BaseReport):
    
    get = Queue.get
    get_all = Queue.all_queues
    order_by = lambda data, o: sorted(data, key=lambda v: v.name)
    
    headers = ['Name', 'Type', 'Items', 'Executors', 'Failure Rate']
    data = {
        'type': lambda obj, **kws: type(obj).__name__,
        'items': lambda obj, **kws: obj.count(),
        'executors': lambda obj, **kws:
            Executor.objects.for_queue(obj).alive().count(),
        'failure_rate': _queue_failure_rate,
    }

class tasks(BaseReport):
    
    get_all = lambda: reduce(lambda a, b: a + b,
        [[t for t in TaskClass.objects.all()] for TaskClass in TASK_MODELS])
    
    details = {
        'instances': lambda id, **kws: _parse_content_ids(id).instances.all(),
    }
    headers = ['Name', 'Type', 'Description', 'Added', 'Timeout', 'Instances']
    data = {
        'id': lambda obj, **kws: '%s_%s' %
            (ContentType.objects.get_for_model(obj).id, obj.id),
        'type': lambda obj, **kws: type(obj).__name__,
        'added': lambda obj, **kws: obj.date_added,
        'instances': lambda obj, **kws: obj.instances.count(),
    }

class instances(BaseReport):
    
    get = lambda id: get_object(Instance, id=id)
    get_all = lambda: Instance.objects.all()
    since_filter = date_ended_since
    order_by = date_ended_order
    
    headers = ['ID', 'Task', 'Started', 'Ended', 'Status']
    data = {
        # 'task_type': lambda i, **kws: type(i.task),
        'status': lambda obj, **kws: Status.NAME[obj.status],
    }

class task_classes(BaseReport):
    
    get = lambda name: filter(lambda t: t.__name__ == name, TASK_MODELS)[0]
    get_all = lambda: TASK_MODELS
    
    headers = ['Task', 'Objects']
    data = {
        'task': lambda task, **kws: task.__name__,
        'objects': lambda task, **kws: task.objects.count(),
    }
