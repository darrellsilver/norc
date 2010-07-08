import datetime, pdb

from django import http
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.template import Context, Template
from django.core.paginator import Paginator, InvalidPage

# from norc.core.models import *
from norc.core import report
from norc.utils.parsing import parse_date_relative
from norc.utils.web import JSONObjectEncoder

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

def paginate(request, data_set):
    try:
        per_page = int(request.GET.get('per_page', 20))
    except ValueError:
        per_page = 15
    paginator = Paginator(data_set, per_page)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    if 0 > page_num > paginator.num_pages:
        page_num = 1
    page = paginator.page(page_num)
    page_data = {
        'next': page.next_page_number() if page.has_next() else 0,
        'prev': page.previous_page_number() if page.has_previous() else 0,
        'start': page.start_index(),
        'end': page.end_index(),
    }
    return page, page_data

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html')

# Provides a function to obtain the set
# of data objects for each content type.
data_set_retrieval = {
    'daemons': lambda GET: report.ndss(
        parse_since(GET.get('since', 'm10min'))),
    'jobs': lambda GET: report.jobs(),
}

# Dictionary the simultaneously defines the data structure to be returned
# for each content type and how to retrieve that data from an object.
data_retrieval = {
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

def get_data(request, content_type):
    """Returns a JSON object containing data on daemons.
    
    The data is filtered by GET parameters in the request.
    
    """
    data_set = data_set_retrieval[content_type](request.GET);
    page, page_data = paginate(request, data_set)
    data = {content_type: {}, 'page': page_data}
    for obj in page.object_list:
        data[content_type][obj.id] = {}
        for k, f in data_retrieval[content_type].iteritems():
            data[content_type][obj.id][k] = f(obj)
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")


detail_set_retrieval = {
    'daemons': lambda did: report.nds(did).get_task_statuses(),
    'jobs': lambda jid: report.iterations(jid),
}
detail_retrieval = {
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
        'ended': lambda i: i.date_ended,
    }
}

def get_details(request, content_type, cid):
    """Gets the details for tasks run by a specific daemon."""
    data = {}
    for item in detail_set_retrieval[content_type](cid):
        data[item.id] = {}
        for k, f in detail_retrieval[content_type].iteritems():
            data[item.id][k] = f(item)
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")
