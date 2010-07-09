
"""Data structures and how to retrieve that data.

The dicts in this file describe what data should be returned for each
content type, and how to retrieve that data from the appropriate object.

"""

from norc.core import report

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


# Provides a function to obtain the set
# of data objects for each content type.
RETRIEVE = {
    'daemons': lambda GET: report.ndss(
        parse_since(GET.get('since', 'm10min'))),
    'jobs': lambda GET: report.jobs(),
}

# Dictionary the simultaneously defines the data structure to be returned
# for each content type and how to retrieve that data from an object.
DATA = {
    'daemons': {
        'type': lambda nds: nds.get_daemon_type(),
        'region': lambda nds: nds.region.name,
        'host': lambda nds: nds.host,
        'pid': lambda nds: nds.pid,
        'running': lambda nds: len(nds.get_task_statuses('running')),
        'success': lambda nds: len(nds.get_task_statuses('success')),
        'errored': lambda nds: len(nds.get_task_statuses('errored')),
        'status': lambda nds: nds.status,
        'started': lambda nds: nds.date_started,
        'ended': lambda nds: nds.date_ended if nds.date_ended else '-',
    },
    'jobs': {
        'name': lambda job: job.name,
        'description': lambda job: job.description,
        'added': lambda job: job.date_added,
    },
}

RETRIEVE_DETAILS = {
    'daemons': lambda did: report.nds(did).get_task_statuses(),
    'jobs': lambda jid: report.iterations(jid),
}

DETAIL_DATA = {
    'daemons': {
        'job': lambda trs: trs.task.job.name,
        'task': lambda trs: trs.task.get_name(),
        'status': lambda trs: trs.status,
        'started': lambda trs: trs.date_started,
        'ended': lambda trs: trs.date_ended,
    },
    'jobs': {
        'status': lambda i: i.status,
        'type': lambda i: i.iteration_type,
        'started': lambda i: i.date_started,
        'ended': lambda i: i.date_ended if i.date_ended else '-',
    }
}

