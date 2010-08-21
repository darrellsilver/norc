#!/usr/bin/python

"""A command-line script to run a Norc scheduler."""

import sys
from optparse import OptionParser

from norc.core.models import Scheduler
from norc.norc_utils.log import make_log

def main():
    usage = "norcs [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-e", "--echo", action="store_true", default=False,
        help="Echo log messages to stdout.")
    parser.add_option("-d", "--debug", action="store_true", default=False,
        help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    scheduler = Scheduler.objects.create()
    # daemon.log = make_log(daemon.log_path,
        # echo=options.echo, debug=options.debug)
    scheduler.start()
    
if __name__ == '__main__':
    main()
