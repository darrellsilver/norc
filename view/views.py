# Create your views here.
from django.shortcuts import render_to_response
from django.template import Context, Template
from norc.core.models import *
from datetime import timedelta

class TaskGroup:
    def __init__(self, date, task):
        self.date = date
        self.task = task
        self.runtime = timedelta()
        self.average = self.runtime
        self.count = 0
    def addTRS(self, trs):
        self.count += 1
        self.runtime += (trs.date_ended - trs.date_started)
        self.average = self.runtime // self.count

def index(request):
    regions = ResourceRegion.objects.all()
    rRange = range(0, len(regions))
    dataMap = {}
    for r in rRange:
        dataMap[r] = {}
        for trs in TaskRunStatus.objects.filter(
            controlling_daemon__region=regions[r] ).order_by('date_started'):

            d = trs.date_started.toordinal()
            t = trs.task.id
            if dataMap[r].keys().count(d) == 0:
                print "make", d
                dataMap[r][d] = {}
            if dataMap[r][d].keys().count(t) == 0:
                dataMap[r][d][t] = TaskGroup(trs.date_started.date(), trs.task)
            dataMap[r][d][t].addTRS(trs)
    
    return render_to_response('index.html',
        { 'dataMap' : dataMap,
          'regions' : regions,
          'rRange'  : rRange })

def notfound(request):
    return render_to_response('500.html', {})