#!/usr/bin/python

###############################
#
# Set up initial data for Perpetually & norc
#
#
# Run these exact steps to go from no tables to full setup:
#  2) python norc/manage.py syncdb --noinput
#  3) python bin/init_db.py
# 
# Now, turn on the archivin':
#  * tmsd --region QA
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
from optparse import OptionParser
from django.contrib.auth.models import User
from utils import log
log = log.Log()

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
    from norc import settings
    
    rr, new_rr = ResourceRegion.objects.get_or_create(name=name)
    assert new_rr, "The resource region should not already exit."
    log_dir = os.path.join(settings.NORC_LOG_DIR, name)
    if not os.path.exists(log_dir):
        log.error("Log dir for '%s' should exist at '%s' but doesn't!" 
            % (name, log_dir))
    return rr

def init_norc():
    from norc.core.models import Job, Iteration
    from norc.core.models import Resource, RegionResourceRelationship
    from norc.core.models import TaskClassImplementation
    
    log.info("Initializing Norc...")
    
    job = Job(name="DEMO_JOB", description="A demo Job.")
    job.save()
    
    iteration, new_iteration = Iteration.objects.get_or_create(
        job=job,
        iteration_type=Iteration.ITER_TYPE_PERSISTENT,
        defaults=dict(status=Iteration.STATUS_RUNNING))
    assert new_iteration, "An iteration should not already exist."
    
    resource_region = _create_ResourceRegion("MY_REGION")
    resource = Resource.create("DATABASE_CONNECTION")
    
    # SQS Regions don't have RegionResourceRelationships; 
    # they get only a --max at run time
    rrr = RegionResourceRelationship.create(resource_region, resource, 10)
    
    log.info("Success! Norc initialized.")

def init_static():
    user = init_superuser()
    init_norc()
    return user

def main():
    parser = OptionParser("%prog")
    # parser.add_option("--init", action="store_true"
    #     , help="setup static data to the DBs")
    (options, args) = parser.parse_args()
    
    user = init_static()

if __name__ == '__main__':
    main()
