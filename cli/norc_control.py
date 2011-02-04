#!/usr/bin/env python

"""A command-line tool to control various functions of Norc.

Presently, this means sending requests to Schedulers and Executors.

"""

import sys
import time
from optparse import OptionParser

from norc.core import controls
from norc.core.constants import Status, Request
from norc.core.models import Executor, Scheduler
from norc.norc_utils.django_extras import update_obj, MultiQuerySet

EXECUTOR_KEYWORDS = ["e", "executor"]
SCHEDULER_KEYWORDS = ["s", "scheduler"]
HOST_KEYWORDS = ["h", "host"]

REQ_TO_STAT = {
    Request.STOP: Status.ENDED,
    Request.KILL: Status.KILLED,
    Request.PAUSE: Status.PAUSED,
    Request.RESUME: Status.RUNNING,
}

def _wait(ds, req):
    print "Waiting for request(s) to take effect..."
    status = REQ_TO_STAT.get(req)
    if status:
        fin = lambda: all(map(lambda d: update_obj(d).status == status, ds))
    else:
        fin = lambda: all(map(lambda d: update_obj(d).request == None, ds))
    while not fin():
        time.sleep(0.5)

def main():
    usage = "norc_control [executor | scheduler | host] <id | host> " + \
        "--[stop | kill | pause | resume | reload] [--wait]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-s", "--stop", action="store_true", default=False,
        help="Send a stop request.")
    parser.add_option("-k", "--kill", action="store_true", default=False,
        help="Send a kill request.")
    parser.add_option("-p", "--pause", action="store_true", default=False,
        help="Send a pause request.")
    parser.add_option("-u", "--resume", action="store_true", default=False,
        help="Send an resume request.")
    parser.add_option("-r", "--reload", action="store_true", default=False,
        help="Send an reload request to a Scheduler.")
    parser.add_option("--handle", action="store_true", default=False,
        help="Change the object's status to HANDLED.")
    parser.add_option("-f", "--force", action="store_true", default=False,
        help="Force the request to be made..")
    parser.add_option("-w", "--wait", action="store_true", default=False,
        help="Wait until the request has been responded to.")
    
    options, args = parser.parse_args()
    
    if len(args) != 2:
        bad_args("Invalid number of arguments.")
    
    
    requests = filter(lambda a: getattr(options, a.lower()),
        Request.NAMES.values())
    if len(requests) != 1 or (len(requests) == 1 and options.handle):
        bad_args("Must request exactly one action.")
    if not options.handle:
        request = requests[0]
        req = getattr(Request, request)
    
    cls = None
    if args[0] in EXECUTOR_KEYWORDS:
        cls = Executor
    elif args[0] in SCHEDULER_KEYWORDS:
        cls = Scheduler
    elif args[0] in HOST_KEYWORDS:
        if options.handle:
            bad_args("Can't perform handle operation on multiple daemons.")
        daemons = MultiQuerySet(Executor, Scheduler).objects.all()
        daemons = daemons.filter(host=args[1]).status_in("active")
        if not options.force:
            daemons = daemons.filter(request=None)
        for d in daemons:
            if req in d.VALID_REQUESTS:
                d.make_request(req)
                print "%s was sent a %s request." % (d, request)
        if options.wait:
            _wait(daemons, req)
    else:
        bad_args("Invalid keyword '%s'." % args[0])
    
    if cls:
        name = cls.__name__
        try:
            obj_id = int(args[1])
        except ValueError:
            bad_args("Invalid id '%s'; must be an integer." % args[1])
        try:
            d = cls.objects.get(id=obj_id)
        except cls.DoesNotExist:
            print "Could not find a(n) %s with id=%s" % (name, obj_id)
        else:
            if options.handle:
                if controls.handle(d):
                    print "The error state of %s was marked as handled." % d
                else:
                    print "%s isn't in an error state." % d
            elif Status.is_final(d.status) and not options.force:
                print "%s is already in a final state." % d
            elif d.request == None or options.force:
                d.make_request(req)
                print "%s was sent a %s request." % (d, request)
                if options.wait:
                    _wait([d], req)
            else:
                print "%s already has request %s." % \
                    (d, Request.name(d.request))
    
if __name__ == '__main__':
    main()
