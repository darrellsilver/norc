#!/usr/bin/python

"""A command-line tool to control various functions of Norc.

Presently, this means sending requests to Schedulers and Executors.

"""

import sys
from optparse import OptionParser

from norc.core.constants import Status
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
    parser.add_option("-u", "--unpause", action="store_true", default=False,
        help="Send an unpause request.")
    parser.add_option("-f", "--force", action="store_true", default=False,
        help="Force the request to be made..")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        bad_args("A process type and id are required.")
    
    try:
        obj_id = int(args[1])
    except ValueError:
        bad_args("Invalid id '%s'; must be an integer." % args[1])
    
    requests = ['stop', 'kill', 'pause', 'unpause']
    requests = filter(lambda a: getattr(options, a), requests)
    if len(requests) != 1:
        bad_args("Must request one action at a time.")
    request = requests[0]
    
    if args[0] in ("e", "executor"):
        try:
            e = Executor.objects.get(id=obj_id)
        except Executor.DoesNotExist:
            print "Could not find an Executor with id=%s" % obj_id
        else:
            req = {
                "stop": Executor.REQUEST_STOP,
                "kill": Executor.REQUEST_KILL,
                "pause": Executor.REQUEST_PAUSE,
                "unpause": Executor.REQUEST_UNPAUSE,
            }[request]
            if Status.is_final(e.status) and not options.force:
                print "Executor #%s is already in a final state." % obj_id
            elif e.request == None or options.force:
                e.make_request(req)
                print "Executor #%s was sent a %s request." % \
                    (args[1], request.upper())
            else:
                print "Executor #%s already has request %s." % \
                    (args[1], Executor.REQUEST[e.request])
    elif args[0] in ["s", "scheduler"]:
        try:
            s = Scheduler.objects.get(id=obj_id)
        except Executor.DoesNotExist:
            print "Could not find a Scheduler with id=%s." % obj_id
        else:
            if not s.is_alive():
                print "Scheduler #%s is already dead." % obj_id
            elif request == "stop":
                s.stop()
                print "Scheduler #%s has been deactivated." % obj_id
            else:
                print "Invalid request; Schedulers can only be stopped."
    else:
        print "Invalid keyword '%s'." % args[0]
    
if __name__ == '__main__':
    main()
