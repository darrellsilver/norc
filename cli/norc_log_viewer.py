#!/usr/bin/python

"""A command-line script to retrieve a Norc log file."""

import sys, os
from optparse import OptionParser

from django.contrib.contenttypes.models import ContentType

from norc import settings
from norc.core.models import Executor, Queue
from norc.norc_utils.log import make_log

if settings.BACKUP_SYSTEM == "AmazonS3":
    from norc.norc_utils.aws import get_s3_key

def main():
    usage = "norc_log_viewer <class_name> <id> [-r]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-r", "--remote", action="store_true", default=False,
        help="Forces log retrieval from the remote source.")
    
    (options, args) = parser.parse_args()
    
    if len(args) != 2:
        bad_args("A class name and id are required.")
    
    model_name = args[0].lower()  
    try:
        obj_id = int(args[1])
    except ValueError:
        bad_args("Invalid id '%s', must be an integer." % args[1])
    
    ctypes = ContentType.objects.filter(model=model_name)
    ct_count = ctypes.count()
    
    if ct_count == 0:
        print "No model found matching '%s'." % model_name
        return
    
    i = 0
    if ct_count > 1:
        i = -1
        while i < 0 or i >= ct_count:
            print 
            for i, ct in enumerate(ctypes):
                print "%s: %s.%s" % \
                    (i, ct.app_label, ct.model_class().__name__)
            try:
                i = int(raw_input(
                    "Please enter the number of the correct model: "))
            except ValueError:
                pass
    
    Model = ctypes[i].model_class()
    try:
        obj = Model.objects.get(id=obj_id)
    except Model.DoesNotExist:
        print "No %s found with id=%s." % (Model.__name__, obj_id)
        return
    
    if hasattr(obj, "log_path"):
        local_path = os.path.join(settings.NORC_LOG_DIR, obj.log_path)
        if os.path.isfile(local_path) and not options.remote:
            f = open(local_path, 'r')
            log = ''.join(f.readlines())
            f.close()
        elif settings.BACKUP_SYSTEM == "AmazonS3":
            print "Retreiving log from S3..."
            try:
                key = 'norc_logs/' + obj.log_path
                log = get_s3_key(key)
            except:
                log = 'Could not retrieve log file from local machine or S3.'
        print log,
    else:
        print "Object does not support a log file."
        
if __name__ == '__main__':
    main()
