# Create your views here.
from django.shortcuts import render_to_response
from django.template import Context, Template
from norc.core.models import *
from norc.core import reporter
from norc.utils import date_utils
from datetime import timedelta

def index(request):
    since = request.GET.get('since', 'm10min')
    if since == 'all':
        since_date = None
    else:
        since_date = date_utils.parse_date_relative(since)
    nds_data = []
    for nds in reporter.get_daemon_statuses(since_date):
        # counts[str(nds.id)] = dict(
        nds_data.append(dict(
            id=nds.id,
            region=nds.get_region(),
            host=nds.host,
            pid=nds.pid,
            running=len(nds.get_task_statuses('running')),
            success=len(nds.get_task_statuses('success')),
            errored=len(nds.get_task_statuses('errored')),
            status=nds.get_status(),
            date_started=nds.date_started,
            date_ended=nds.date_ended))
    return render_to_response('index.html', dict(nds_data=nds_data))

def notfound(request, *args):
    return render_to_response('500.html', {})

# def sandbox(request, *args):
#     class X():
#         def test(self): return "foo!"
#     x = X()
#     listTest = [1, 2, 3]
#     mapTest = dict(test="boo!",best="moo!",ex=x)
#     return render_to_response('sandbox.html', dict(list=listTest, map=mapTest))
