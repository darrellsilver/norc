
"""Data structures and how to retrieve that data.

The dicts in this file describe what data should be returned for each
content type, and how to retrieve that data from the appropriate object.

"""

from django.conf import settings

from norc.core import report
from norc.norc_utils.parsing import parse_since

def get_trss(nds, status_filter='all', since_date=None):
    """
    A hack fix so we can get the statuses for the proper daemon type.
    """
    status_filter = status_filter.lower()
    if nds.get_daemon_type() == 'NORC':
        task_statuses = nds.taskrunstatus_set.all()
    else:
        task_statuses = nds.sqstaskrunstatus_set.all()
    status_filter = status_filter.lower()
    from norc.core.models import TaskRunStatus
    TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
    if not since_date == None:
        task_statuses = task_statuses.exclude(date_ended__lt=since_date)
    if status_filter != 'all' and status_filter in TRS_CATS:
        only_statuses = TRS_CATS[status_filter]
        task_statuses = task_statuses.filter(status__in=only_statuses)
    return task_statuses

def get_sqsqueues():
    if 'norc.sqs' in settings.INSTALLED_APPS:
        from boto.sqs.connection import SQSConnection
        c = SQSConnection(settings.AWS_ACCESS_KEY_ID,
                          settings.AWS_SECRET_ACCESS_KEY)
        return c.get_all_queues()
    else:
        return []

# Provides a function to obtain the set of objects for each content type.
RETRIEVE = dict(
    daemons=lambda: report.ndss(),
    jobs=lambda: report.jobs(),
    sqsqueues=lambda: get_sqsqueues(),
)

RETRIEVE_DETAILS = {
    'daemons': ('tasks', lambda cid, GET:
        get_trss(report.nds(cid),GET.get('status', 'all'))),
    'jobs': ('iterations', lambda cid, _: report.iterations(cid)),
    'iterations': ('tasks', lambda cid, _: report.tasks_from_iter(cid)),
}
SINCE_FILTER = dict(
    daemons=lambda data, since: data.exclude(date_ended__lt=since),
    tasks=lambda data, since: data.exclude(date_ended__lt=since),
)

ORDER = dict(
    daemons=lambda data, o: data.order_by(o if o else '-date_ended'),
    tasks=lambda data, o: data.order_by(o if o else '-date_ended'),
)
# Dictionary the simultaneously defines the data structure to be returned
# for each content type and how to retrieve that data from an object.
DATA = {
    'daemons': {
        'id': lambda nds, _: nds.id,
        'type': lambda nds, _: nds.get_daemon_type(),
        'region': lambda nds, _: nds.region.name,
        'host': lambda nds, _: nds.host,
        'pid': lambda nds, _: nds.pid,
        'running': lambda nds, _: len(get_trss(nds, 'running')),
        'success': lambda nds, GET: len(get_trss(nds, 'success',
                                        parse_since(GET.get('since')))),
        'errored': lambda nds, GET: len(get_trss(nds, 'errored',
                                        parse_since(GET.get('since')))),
        'status': lambda nds, _: nds.status,
        'started': lambda nds, _: nds.date_started,
        'ended': lambda nds, _: nds.date_ended if nds.date_ended else '-',
    },
    'jobs': {
        'id': lambda job, _: job.id,
        'name': lambda job, _: job.name,
        'description': lambda job, _: job.description,
        'added': lambda job, _: job.date_added,
    },
    'tasks': {
        'id': lambda trs, _: trs.id,
        'job': lambda trs, _: trs.task.job.name,
        'task': lambda trs, _: trs.task.get_name(),
        'status': lambda trs, _: trs.status,
        'started': lambda trs, _: trs.date_started,
        'ended': lambda trs, _: trs.date_ended,
    },
    'sqstasks': {
        'id': lambda trs, _: trs.id,
        'task_id': lambda trs, _: str(trs.get_task_id()),
        'status': lambda trs, _: trs.get_status(),
        'started': lambda trs, _: trs.date_started,
        'ended': lambda trs, _: trs.date_ended,
    },
    'iterations': {
        'id': lambda i, _: i.id,
        'status': lambda i, _: i.status,
        'type': lambda i, _: i.iteration_type,
        'started': lambda i, _: i.date_started,
        'ended': lambda i, _: i.date_ended if i.date_ended else '-',
    },
    'sqsqueues': {
        'id': lambda q, _: q.url.split('/')[-1],
        'num_items': lambda q, _: q.count(),
        'timeout': lambda q, _: q.get_timeout(),
    },
}
