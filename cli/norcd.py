#!/usr/bin/python

"""A command-line script to run a Norc daemon."""

import sys
from optparse import OptionParser

from norc.core.models import Daemon, Queue
from norc.norc_utils.log import make_log

def main():
    usage = "norcd <queue_name> -c <n> [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-c", "--concurrent", type='int',
        help="How many instances can be run concurrently.")
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
        bad_args("Invalid queue name '%s'." % args[0])
    
    daemon = Daemon.objects.create(queue=queue, concurrent=options.concurrent)
    daemon.log = make_log(daemon.log_path,
        echo=options.echo, debug=options.debug)
    daemon.start()
    
if __name__ == '__main__':
    main()
