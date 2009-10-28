#!/usr/bin/python

############################################
#
# Daemon that manages queue of Tasks allowed to run 
# across all of TMS
# 
# Provides monitoring for daemons that die unexpectedly.
#
#
#Darrell
#05/18/2009
############################################


from norc import settings

from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)


def refill_queue():
    pass

def main():
    parser = OptionParser("%prog [--debug]")
    #parser.add_option("--no_log_redirect", action="store_true"
    #    , help="print daemon logging to sys.stdout & sys.stderr instead of redirecting them to a TMS log file.")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    log.set_logging_debug(options.debug)
    
    


if __name__ == '__main__':
    main()

#
