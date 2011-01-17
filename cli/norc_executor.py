#!/usr/bin/python

"""A command-line script to run a Norc executor."""

import sys
from optparse import OptionParser

from norc.core.models import Executor, Queue, DBQueue
from norc.norc_utils.log import make_log

def main():
    usage = "norc_executor <queue_name> -c <n> [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-c", "--concurrent", type='int',
        help="How many instances can be run concurrently.")
    parser.add_option("-q", "--create_queue", action="store_true",
        default=False, help="Force creation of a DBQueue with this name.")
    parser.add_option("-e", "--echo", action="store_true", default=False,
        help="Echo log messages to stdout.")
    parser.add_option("-d", "--debug", action="store_true", default=False,
        help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 1:
        bad_args("A single queue name is required.")
    
    if options.concurrent == None:
        bad_args("You must give a maximum number of concurrent subprocesses.")
    
    queue = Queue.get(args[0])
    if not queue:
        if options.create_queue:
            queue = DBQueue.objects.create(name=args[0])
        else:
            bad_args("Invalid queue name '%s'." % args[0])
    
    executor = Executor.objects.create(queue=queue, concurrent=options.concurrent)
    executor.log = make_log(executor.log_path,
        echo=options.echo, debug=options.debug)
    executor.start()
    
if __name__ == '__main__':
    main()
