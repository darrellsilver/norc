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
    def encode_datetime(self, obj):
        return obj.strftime("%m/%d/%Y %H:%M:%S")

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

def notfound(request, *args):
    return render_to_response('500.html', {})

def daemon_details(request):
    d_id = request.GET.get('id', None)
    since_str = request.GET.get('since', 'm10min')
    nds = report.nds(d_id)
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

