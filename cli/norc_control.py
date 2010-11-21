#!/usr/bin/python

"""A command-line tool to control various functions of Norc.

Presently, this means sending requests to Schedulers and Executors.

"""

import sys
from optparse import OptionParser

from norc.core.constants import Status, Request
from norc.core.models import Executor, Scheduler

def main():
    usage = "norc_control [e | executor | s | scheduler] <id> " + \
        "--[stop | kill | pause | resume]"
    
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
    parser.add_option("-f", "--force", action="store_true", default=False,
        help="Force the request to be made..")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        bad_args("A process type and id are required.")
    
    try:
        obj_id = int(args[1])
    except ValueError:
        bad_args("Invalid id '%s'; must be an integer." % args[1])
    
    # requests = ['stop', 'kill', 'pause', 'resume']
    requests = filter(lambda a: getattr(options, a.lower()),
        Request.NAMES.values())
    if len(requests) != 1:
        bad_args("Must only request one action at a time.")
    request = requests[0]
    
    cls = None
    if args[0] in ("e", "executor"):
        cls = Executor
    elif args[0] in ["s", "scheduler"]:
        cls = Scheduler
    else:
        print "Invalid keyword '%s'." % args[0]
    
    if cls:
        name = cls.__name__
        try:
            d = cls.objects.get(id=obj_id)
        except cls.DoesNotExist:
            print "Could not find a(n) %s with id=%s" % (name, obj_id)
        else:
            req = getattr(Request, request.upper())
            if Status.is_final(d.status) and not options.force:
                print "%s #%s is already in a final state." % (name, obj_id)
            elif d.request == None or options.force:
                d.make_request(req)
                print "%s was sent a %s request." % (d, request.upper())
            else:
                print "%s already has request %s." % \
                    (d, Request.name(d.request))
    
if __name__ == '__main__':
    main()
