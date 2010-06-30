import datetime, pdb
from django import http
from django.shortcuts import render_to_response
from django.template import Context, Template
from django.utils import simplejson
from norc.core.models import *
from norc.core import report
from norc.utils import parsing
from datetime import timedelta

class JSONObjectEncoder(simplejson.JSONEncoder):
    """
    simplejson doesn't handle complex objects (like datetime()).
    Handle encoding of those here
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return self.encode_datetime(obj)
        return simplejson.JSONEncoder.default(self, obj)
    def encode_datetime(self, dt):
        return dt.strftime("%m/%d/%Y %H:%M:%S")

def get_nds_set(since_str):
    if since_str == 'all':
        since_date = None
    else:
        try:
            since_date = parsing.parse_date_relative(since_str)
        except:
            since_date = None
    return report.ndss(since_date)

def index(request):
    # Default to the last ten minutes.
    since_str = request.GET.get('since', 'm10min')
    nds_set = get_nds_set(since_str)
    return render_to_response('index.html', dict(nds_set=nds_set))

def get_daemons(request):
    """Returns a JSON object containing data on all the daemons statuses."""
    since_str = request.GET.get('since', 'all')
    nds_set = get_nds_set(since_str)
    data = {}
    for nds in nds_set:
        data[nds.id] = {
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
    # d_id = request.GET.get('id', None)
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
    
# def sandbox(request, *args):
#     class X():
#         def test(self): return "foo!"
#     x = X()
#     listTest = [1, 2, 3]
#     mapTest = dict(test="boo!",best="moo!",ex=x)
#     return render_to_response('sandbox.html', dict(
#         list=listTest, map=mapTest))

