#!/usr/bin/python

"""A command-line script to run a Norc scheduler."""

import sys, time
from optparse import OptionParser

from norc.core import reports
from norc.norc_utils.parsing import parse_since
from norc.norc_utils.formatting import untitle, pprint_table

def main():
    usage = "norc_reporter [--executors] [--schedulers] [--queues]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    parser = OptionParser(usage)
    parser.add_option("-e", "--executors", action="store_true",
        help="Report on executors.")
    parser.add_option("-s", "--schedulers", action="store_true",
        help="Report on schedulers.")
    parser.add_option("-q", "--queues", action="store_true",
        help="Report on queues.")
    parser.add_option("-t", "--since", action="store",
        help="Report on queues.")
    
    (options, args) = parser.parse_args()
    since = parse_since(options.since)
    
    if not any([options.executors, options.schedulers, options.queues]):
        options.executors = True
    
    print time.strftime('[%Y/%m/%d %H:%M:%S]'),
    if since:
        print 'from the last %s.' % options.since,
    print ''
    
    def print_report(report):
        data_objects = report.get_all()
        data_objects = report.since_filter(data_objects, since)
        data_objects = report.order_by(data_objects, None)
        data_list = reports.generate(data_objects, report, dict(since=since))[:20]
        if len(data_list) > 0:
            table = [report.headers] + [[str(o[untitle(h)])
                for h in report.headers] for o in data_list]
            pprint_table(sys.stdout, table)
        else:
            print 'None found.'

    if options.executors:
        print '\n## Executors ##'
        print_report(reports.executors)
    if options.schedulers:
        print '\n## Schedulers ##'
        print_report(reports.schedulers)
    if options.queues:
        print '\n## Queues ##'
        print_report(reports.queues)
        
        
        

if __name__ == '__main__':
    main()
