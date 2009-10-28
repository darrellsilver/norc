#!/usr/bin/python

##############################################
#
# Some utilities to manage Amazon SQS
#
#
#
#Darrell
#05/25/2009
##############################################

import sys, datetime, pickle, time
from optparse import OptionParser

from permalink import settings# not exactly normalized, but a shortcut addressable later
from permalink.tms_impl import models

from boto.sqs.connection import SQSConnection
from boto.exception import SQSError

from norc.utils import formatting
from norc.utils import log
log = log.Log(settings.LOGGING_DEBUG)


def get_name(q):
    name = q.url.split('/')[-1]
    return name

def delete_queue(c, queue_name):
    q = c.get_queue(queue_name)
    if q == None:
        raise Exception("No queue exists by name '%s'" % (queue_name))
    log.info("Deleting q '%s' (had %s messages)" % (queue_name, q.count()))
    q.delete()

def clear_queue(c, queue_name, use_api):
    q = c.get_queue(queue_name)
    if q == None:
        raise Exception("No queue exists by name '%s'" % (queue_name))
    if use_api:
        log.info("Clearing q '%s' using method recommended in API (had %s messages)" % (queue_name, q.count()))
        q.clear()
    else:
        # clearing is slow & unreliable for some reason.  Just delete it and recreate it.
        log.info("Clearing q using deletion '%s' (had %s messages)" % (queue_name, q.count()))
        visibility_timeout = q.get_timeout()
        delete_queue(c, queue_name)
        wait = 65
        log.info("Waiting %s seconds before recreating queue" % (wait))
        time.sleep(wait)# amazon forces us to wait 1 minute before creating a queue by the same name
        create_queue(c, queue_name, visibility_timeout=visibility_timeout)

def create_queue(c, queue_name, visibility_timeout=None):
    q = c.get_queue(queue_name)
    if not q == None:
        raise Exception("Queue by name '%s' already exists!" % (queue_name))
    log.info("Creating queue '%s' with visibility timeout %s" % (queue_name, visibility_timeout))
    c.create_queue(queue_name, visibility_timeout=visibility_timeout)

def rpt_queues(c):
    all_queues = c.get_all_queues()
    print "%s AWS SQS Queue(s) as of %s" % (len(all_queues), datetime.datetime.now())
    sys.stdout.write('\n')
    
    table_data = []
    header1 = ['Name', '~ #', 'Timeout']
    header2 = ['-','-','-']
    table_data.append(header1)
    table_data.append(header2)
    for q in all_queues:
        try:
            row = [get_name(q), q.count(), q.get_timeout()]
            table_data.append(row)
        except SQSError, sqse:
            log.error("Internal SQS error (it generates ignorable errors sometimes)"+ str(sqse))
    
    if len(table_data) > 2:
        formatting.pprint_table(sys.stdout, table_data)
    sys.stdout.write('\n')

#
#
#

def main():
    parser = OptionParser("%prog [--create_queue <name> [--visibility_timeout <seconds>]] \
[--clear_queue <name> [--use_api]] [--delete_queue <name>] [--debug]")
    parser.add_option("--create_queue", action="store")
    parser.add_option("--visibility_timeout", action="store", type="int")
    parser.add_option("--delete_queue", action="store")
    parser.add_option("--clear_queue", action="store")
    parser.add_option("--use_api", action="store_true")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    c = SQSConnection(settings.AWS_ACCESS_KEY_ID, settings.AWS_SECRET_ACCESS_KEY)
    
    if options.create_queue:
        create_queue(c, options.create_queue, options.visibility_timeout)
    if options.clear_queue:
        clear_queue(c, options.clear_queue, options.use_api)
    if options.delete_queue:
        delete_queue(c, options.delete_queue)
    
    rpt_queues(c)
    
    #for q in c.get_all_queues():
    #    test_read(q)
    

if __name__ == '__main__':
    main()

#
