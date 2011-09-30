#!/usr/bin/env python

"""A command-line tool to clear various parts of Norc."""

from os import mkdir
from shutil import rmtree
import sys

from norc.core import controls
from norc.core.constants import Status, Request, INSTANCE_MODELS
from norc.core.models import Executor, Scheduler, Queue
from norc.norc_utils import wait_until
from norc.norc_utils.django_extras import MultiQuerySet, queryset_exists
from norc.settings import NORC_LOG_DIR

def shutdown_daemons():
    daemons = MultiQuerySet(Executor, Scheduler).objects.all()
    count = 0
    for d in daemons.alive():
        print "Sending KILL request to %s..." % d
        d.make_request(Request.KILL)
        count += 1
    wait_until(lambda: not queryset_exists(daemons.alive()), 5)
    print "%s daemons shut down." % count

def handle_errors():
    objs = MultiQuerySet(Executor, Scheduler, *INSTANCE_MODELS).objects.all()
    count = 0
    for obj in objs.status_in(Status.GROUPS("error")):
        print "Handling %s..." % obj
        controls.handle(obj)
        count += 1
    print "%s objects marked as HANDLED." % count

def clear_queues():    
    queue_count = 0
    item_count = 0
    for q in Queue.all_queues():
        c = q.count()
        if c > 0:
            print "Clearing %s items from %s..." % (c, q)
            q.clear()
            queue_count += 1
            item_count += c
    print "%s items cleared from %s queues." % (item_count, queue_count)

def wipe_logs():
    rmtree(NORC_LOG_DIR)
    mkdir(NORC_LOG_DIR)
    print "Log directory '%s' has been wiped and remade." % NORC_LOG_DIR

def main(args):
    if len(args) != 1:
        "Usage: norc_clean [daemons | errors | queues | logs | all]"
        sys.exit(2)
    
    arg = args[0]
    
    if arg == "daemons":
        shutdown_daemons()
    elif arg == "errors":
        handle_errors()
    elif arg == "queues":
        clear_queues()
    elif arg == "logs":
        wipe_logs()
    elif arg == "all":
        shutdown_daemons()
        handle_errors()
        clear_queues()
        wipe_logs()
    else:
        "Usage: norc_clean [daemons | errors | queues | logs | all]"
        sys.exit(2)

if __name__ == '__main__':
    main(sys.argv[1:])
