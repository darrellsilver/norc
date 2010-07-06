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

def index(request):
    """Returns the index.html template."""
    return render_to_response('index.html')

def get_daemons(request):
    """Returns a JSON object containing data on daemons.
    
    The data is filtered by GET parameters in the request.
    
    """
    since_str = request.GET.get('since', 'm10min')
    paginator = Paginator(report.ndss(parse_since(since_str)), 10)
    try:
        page_num = int(request.GET.get('page', 1))
    except ValueError:
        page_num = 1
    if 0 > page_num > paginator.num_pages:
        page_num = 1
    p = paginator.page(page_num)
    data = {
        'daemons' : {},
        'page' : {
            'next' : p.next_page_number() if p.has_next() else 0,
            'prev' : p.previous_page_number() if p.has_previous() else 0,
            'start' : p.start_index(),
            'end' : p.end_index(),
        },
    }
    for nds in p.object_list:
        data['daemons'][nds.id] = {
            'type' : nds.get_daemon_type(),
            'region' : nds.region.name,
            'host' : nds.host,
            'pid' : nds.pid,
            'running' : len(nds.get_task_statuses('running')),
            'success' : len(nds.get_task_statuses('success')),
            'errored' : len(nds.get_task_statuses('errored')),
            'status' : nds.status,
            'started' : nds.date_started,
            'ended' : nds.date_ended if nds.date_ended else '-',
        }
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")

def daemon_details(request, daemon_id):
    """Gets the details for tasks run by a specific daemon."""
    since_str = request.GET.get('since', 'm10min')
    nds = report.nds(daemon_id)
    if not nds:
        return
    data = {}
    for trs in nds.get_task_statuses():
        data[trs.id] = {
            'job' : trs.task.job.name,
            'task' : trs.task.get_name(),
            'status' : trs.status,
            'started' : trs.date_started,
            'ended' : trs.date_ended
        }
    json = simplejson.dumps(data, cls=JSONObjectEncoder)
    return http.HttpResponse(json, mimetype="json")
