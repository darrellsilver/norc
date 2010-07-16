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
from django.conf import settings

from norc.norc_utils.log_new import FileLog
log = FileLog(os.devnull)

def init_superuser():
    assert User.objects.all().count() == 0, "User(s) already exist in the DB!"
    
    # username=1@1.com, password=1
    user = User.objects.create_user('1@1.com', '1@1.com', '1')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    assert user.id == 1, "Created superuser but id is not 1! \
Are there users already defined in the DB?"
    return user

def _create_ResourceRegion(name):
    from norc.core.models import ResourceRegion
    from django.conf import settings
    
    rr, new_rr = ResourceRegion.objects.get_or_create(name=name)
    assert new_rr, "The resource region should not already exit."
    # log_dir = os.path.join(settings.NORC_LOG_DIR, name)
    # if not os.path.exists(log_dir):
    #     log.error("Log dir for '%s' should exist at '%s' but doesn't!" 
    #         % (name, log_dir))
    return rr

def init_norc():
    from norc.core.models import Job, Iteration
    from norc.core.models import Resource, RegionResourceRelationship
    from norc.core.models import TaskClassImplementation
    
    log.info("Initializing Norc database...")
    
    job = Job(name="DEMO_JOB", description="A demo Job.")
    job.save()
    
    iteration, new_iteration = Iteration.objects.get_or_create(
        job=job,
        iteration_type=Iteration.ITER_TYPE_PERSISTENT,
        defaults=dict(status=Iteration.STATUS_RUNNING))
    assert new_iteration, "An iteration should not already exist."
    
    resource_region = _create_ResourceRegion("DEMO_REGION")
    resource = Resource.create("DATABASE_CONNECTION")
    
    # SQS Regions don't have RegionResourceRelationships; 
    # they get only a --max at run time
    rrr = RegionResourceRelationship.create(resource_region, resource, 10)
    
    log.info("Success! Norc database initialized.")

def init():
    init_superuser()
    init_norc()

if __name__ == '__main__':
    init()
