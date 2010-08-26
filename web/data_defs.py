
""" Data definitions for responding to AJAX requests for data.

The DataDefinition objects in this file describe what data should be
returned for each content type, and how to retrieve that data from
the appropriate object.

"""

from django.conf import settings

from norc.core import reports
from norc.core.models import TaskRunStatus
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import to_title

DATA_DEFS = {}

class DataDefinition(object):
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
    def __init__(self, key, data, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)
        if not 'title' in kwargs:
            self.title = to_title(self.key)
        DATA_DEFS[self.key] = self

date_ended_filter = lambda data, since: data.exclude(date_ended__lt=since)
date_ended_order = lambda data, o: data.order_by(o if o else '-date_ended')
date_ended_getter = lambda obj, _: obj.date_ended if obj.date_ended else '-'

DataDefinition(
    key='daemons',
    retrieve=lambda: report.ndss(),
    detail_key='tasks',
    details=lambda cid, GET: report.trss(
        report.nds(cid),GET.get('status', 'all')),
    since_filter=date_ended_filter,
    order_by=date_ended_order,
    data={
        'id': lambda nds, _: nds.id,
        'type': lambda nds, _: nds.get_daemon_type(),
        'region': lambda nds, _: nds.region.name,
        'host': lambda nds, _: nds.host,
        'pid': lambda nds, _: nds.pid,
        'running': lambda nds, _: len(report.trss(nds, 'running')),
        'success': lambda nds, GET: len(report.trss(nds, 'success',
                                        parse_since(GET.get('since')))),
        'errored': lambda nds, GET: len(report.trss(nds, 'errored',
                                        parse_since(GET.get('since')))),
        'status': lambda nds, _: nds.status,
        'started': lambda nds, _: nds.date_started,
        'ended': date_ended_getter,
    },
)

DataDefinition(
    key='tasks',
    since_filter=date_ended_filter,
    order_by=date_ended_order,
    data={
        'id': lambda trs, _: trs.id,
        'job': lambda trs, _: trs.task.job.name,
        'task': lambda trs, _: trs.task.get_name(),
        'status': lambda trs, _: trs.status,
        'started': lambda trs, _: trs.date_started,
        'ended': date_ended_getter,
    },
)

tasks = DataDefinition(
    key='tasks',
    since_filter=date_ended_filter,
    order_by=date_ended_order,
    data={
        'id': lambda trs, _: trs.id,
        'job': lambda trs, _: trs.task.job.name,
        'iteration': lambda trs, _: trs.iteration.id,
        'task': lambda trs, _: trs.task.get_name(),
        'status': lambda trs, _: trs.status,
        'started': lambda trs, _: trs.date_started,
        'ended': date_ended_getter,
    },
)

DataDefinition(
    key='failedtasks',
    retrieve=lambda: TaskRunStatus.objects.filter(
        status__in=TaskRunStatus.STATUS_CATEGORIES['errored']),
    since_filter=tasks.since_filter,
    order_by=tasks.order_by,
    data=tasks.data,
)

DataDefinition(
    key='jobs',
    retrieve=lambda: report.jobs(),
    detail_key='iterations',
    details=lambda cid, _: report.iterations(cid),
    data={
        'id': lambda job, _: job.id,
        'name': lambda job, _: job.name,
        'description': lambda job, _: job.description,
        'added': lambda job, _: job.date_added,
    },
)

DataDefinition(
    key='iterations',
    detail_key='tasks',
    details=lambda cid, _: report.tasks_from_iter(cid),
    order_by=date_ended_order,
    data={
        'id': lambda i, _: i.id,
        'status': lambda i, _: i.status,
        'type': lambda i, _: i.iteration_type,
        'started': lambda i, _: i.date_started,
        'ended': date_ended_getter,
    },
)
