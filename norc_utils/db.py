#!/usr/bin/python

###############################
#
# Set up initial data for Norc.
#
#
# Run these steps to go from no tables to full setup:
#  2) python norc/manage.py syncdb --noinput
#  3) python util/init_db.py
# 
# Now, turn on the archivin':
#  * norcd --region DEMO_REGION
#  * sqsd --queue SQSArchiveRequest-NORMAL --max 1
# 
# TODO call syncdb for permalink & norc here instead of expecting it
# TODO add a 'clear' option to clear all tables instead of
# 
# Monitor what's going on:
#  * See what's enqueued: sqsctl
#  * See running daemons: tmsdctl --status
#
###############################

import os, sys
import datetime

from django.contrib.auth.models import User

from norc import settings
from norc.core.models import *
from norc.norc_utils.log_new import FileLog
log = FileLog(os.devnull)

def make_superuser(username, password, email):
    assert User.objects.all().count() == 0, "User(s) already exist in the DB!"
    user = User.objects.create_user(username, email, password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user

def init_norc():
    
    log.info("Initializing Norc database...")
    
    job = Job.objects.create(name="DEMO_JOB", description="Demo Job.")
    iteration = Iteration.objects.create(
        job=job,
        iteration_type=Iteration.ITER_TYPE_PERSISTENT,
        status=Iteration.STATUS_RUNNING)
    
    resource_region = ResourceRegion.objects.create(name="DEMO_REGION")
    resource = Resource.objects.create(name="DATABASE_CONNECTION")
    rrr = RegionResourceRelationship.create(resource_region, resource, 10)
    
    log.info("Success! Norc database initialized.")

def init():
    init_norc()

def init_test_db():
    make_superuser('test', 'norc', 'test@norc.com')
    
    job = Job.objects.create(name='TEST', description='test',
        date_added=datetime.datetime.strptime(
            '2010/07/11 12:34:56', '%Y/%m/%d %H:%M:%S'))
    iteration = Iteration.objects.create(
        job=job,
        iteration_type=Iteration.ITER_TYPE_PERSISTENT,
        date_started=datetime.datetime.strptime(
            '2010/07/11 13:13:13', '%Y/%m/%d %H:%M:%S'))
    
    rr = ResourceRegion(name='TEST_REGION')
    rr.save()
    resource = Resource.objects.create(name='DATABASE_CONNECTION')
    RegionResourceRelationship.create(rr, resource, 10)
    
    daemon = NorcDaemonStatus.objects.create(
        region=rr, host='test.norc.com', pid=9001, status='ENDED',
        date_started=datetime.datetime.strptime('2010/06/07', '%Y/%m/%d'),
        date_ended=datetime.datetime.strptime('2010/08/27', '%Y/%m/%d'))
    
    task = RunCommand.objects.create(job=job, status=Task.STATUS_ACTIVE,
        cmd='echo "test"', timeout=300)
    trs = TaskRunStatus(task=task, iteration=iteration,
        status=TaskRunStatus.STATUS_SUCCESS, controlling_daemon=daemon,
        date_started=datetime.datetime.strptime(
            '2010/07/29 09:30:42', '%Y/%m/%d %H:%M:%S'),
        date_ended=datetime.datetime.strptime(
            '2010/07/29 16:46:42', '%Y/%m/%d %H:%M:%S'))
    trs.save()

if __name__ == '__main__':
    init()
