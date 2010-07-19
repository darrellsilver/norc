
"""Data structures and how to retrieve that data.

The dicts in this file describe what data should be returned for each
content type, and how to retrieve that data from the appropriate object.

"""

from norc.core import report
from norc.norc_utils.parsing import parse_date_relative

def parse_since(since_str):
    """A utility function to help parse a since string."""
    if since_str == 'all':
        since_date = None
    else:
        try:
            since_date = parse_date_relative(since_str)
        except TypeError:
            since_date = None
    return since_date

def get_trss(nds, status_filter='all', since_date=None):
    """
    A hack fix so we can get the statuses for the proper daemon type.
    """
    if nds.daemon_type == 'NORC':
        task_statuses = nds.taskrunstatus_set.all()
    else:
        task_statuses = nds.sqstaskrunstatus_set.all()
    status_filter = status_filter.lower()
    from norc.core.models import TaskRunStatus
    TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
    #sqs_statuses = self.sqstaskrunstatus_set.filter(controlling_daemon=self)
    if not since_date == None:
        task_statuses = task_statuses.filter(date_started__gte=since_date)
        #sqs_statuses = sqs_statuses.filter(date_started__gte=since_date)
    if status_filter != 'all' and status_filter in TRS_CATS:
        only_statuses = TRS_CATS[status_filter.lower()]
        task_statuses = task_statuses.filter(status__in=only_statuses)
        #filtered.extend(sqs_statuses.filter(status__in=only_statuses))
    return task_statuses

# Provides a function to obtain the set
# of data objects for each content type.
RETRIEVE = {
    'daemons': lambda GET: filter(lambda nds: nds.daemon_type == 'NORC',
        report.ndss(parse_since(GET.get('since', '10m')))),
    'sqsdaemons': lambda GET: filter(lambda nds: nds.daemon_type == 'SQS',
        report.ndss(parse_since(GET.get('since', '10m')))),
    'jobs': lambda GET: report.jobs(),
}

RETRIEVE_DETAILS = {
    # 'daemons': ('tasks', lambda id: report.nds(id).get_task_statuses()),
    'daemons': ('tasks', lambda cid: get_trss(report.nds(cid))),
    'sqsdaemons': ('sqstasks', lambda cid: get_trss(report.nds(cid))),
    'jobs': ('iterations', lambda cid: report.iterations(cid)),
    'iterations': ('tasks', lambda cid: report.tasks_from_iter(cid)),
}

# Dictionary the simultaneously defines the data structure to be returned
# for each content type and how to retrieve that data from an object.
DATA = {
    'daemons': {
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
    'sqsdaemons': {
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
        'name': lambda job, _: job.name,
        'description': lambda job, _: job.description,
        'added': lambda job, _: job.date_added,
    },
    'tasks': {
        'job': lambda trs, _: trs.task.job.name,
        'task': lambda trs, _: trs.task.get_name(),
        'status': lambda trs, _: trs.status,
        'started': lambda trs, _: trs.date_started,
        'ended': lambda trs, _: trs.date_ended,
    },
    'sqstasks': {
        'task_id': lambda trs, _: str(trs.get_task_id()),
        'status': lambda trs, _: trs.get_status(),
        'started': lambda trs, _: trs.date_started,
        'ended': lambda trs, _: trs.date_ended,
    },
    'iterations': {
        'status': lambda i, _: i.status,
        'type': lambda i, _: i.iteration_type,
        'started': lambda i, _: i.date_started,
        'ended': lambda i, _: i.date_ended if i.date_ended else '-',
    },
}
