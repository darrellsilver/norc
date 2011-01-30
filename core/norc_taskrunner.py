#!/usr/bin/env python

"""Script to run a Norc instance for 2.5 compatibility."""

import sys
from optparse import OptionParser

from django.contrib.contenttypes.models import ContentType

def main():
    usage = "norc_taskrunner --ct_pk <pk> --content_pk <pk>" # [-e] [-d]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("--ct_pk",
        help="The ContentType primary key for the object to start().")
    parser.add_option("--target_pk",
        help="The primary key of the object to start().")
    # parser.add_option("-e", "--echo", action="store_true", default=False,
    #     help="Echo log messages to stdout.")
    # parser.add_option("-d", "--debug", action="store_true", default=False,
    #     help="Enable debug messages.")
    
    (options, args) = parser.parse_args()
    
    if not hasattr(options, 'ct_pk') or not hasattr(options, 'target_pk'):
        bad_args("You must give the ContentType and target primary keys.")
    
    try:
        ct = ContentType.objects.get(pk=options.ct_pk)
    except ContentType.DoesNotExist:
        bad_args("Invalid ContentType primary key '%s'." % options.ct_pk)
    
    try:
        target = ct.get_object_for_this_type(pk=options.target_pk)
    except ct.model_class().DoesNotExist:
        bad_args("Target object not found for pk='%s'" % options.target_pk)
    
    target.start()

if __name__ == '__main__':
    main()
