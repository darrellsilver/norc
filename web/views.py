

from django.shortcuts import render_to_response
from django.template import Context, Template
from norc.core.models import *
from norc.core import reporter
from norc.utils import parsing
from datetime import timedelta

def index(request):
    since = request.GET.get('since', 'm10min')
    if since == 'all':
        since_date = None
    else:
        try:
            since_date = parsing.parse_date_relative(since)
        except:
            since_date = None
    nds_set = reporter.get_daemon_statuses(since_date)
    return render_to_response('index.html', dict(nds_set=nds_set))

def notfound(request, *args):
    return render_to_response('500.html', {})

# def sandbox(request, *args):
#     class X():
#         def test(self): return "foo!"
#     x = X()
#     listTest = [1, 2, 3]
#     mapTest = dict(test="boo!",best="moo!",ex=x)
#     return render_to_response('sandbox.html', dict(list=listTest, map=mapTest))

