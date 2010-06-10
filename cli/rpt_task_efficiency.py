#!/usr/bin/python

#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#     * 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


#######################################
#
# Report on how long Tasks run, wait to run, etc
#
#
#
#Darrell
#05/19/2009
#######################################


import sys
import datetime, time
from optparse import OptionParser

from norc.core import models as core
from norc.sqs import models as sqs

from norc.utils import formatting
from norc.utils.reporting import round_datetime, round_2_delta, calc_avg \
    , ensure_hash_depth, ensure_list, mod_timedelta
from norc.utils import log
log = log.Log()

#
# biz logic
#

def compile_timings(data_to_compile, one_row_compiler, save_stream=None):
    task_timings = []# [[task_name, date_added, date_started, date_ended]...]
    #print matches.query.as_sql()
    need_newline = False
    for row in data_to_compile.all():
        one_row = one_row_compiler(row)
        if one_row == None:
            continue
        task_timings.append(one_row)
        if not save_stream == None:
            save_stream.write(','.join(map(str, one_row)))
            save_stream.write('\n')
        if not save_stream == None and len(task_timings) % 10 == 0:
            save_stream.flush()
        if len(task_timings) % 50 == 0:
            sys.stderr.write('.')
            need_newline = True
    if need_newline:
        sys.stderr.write('\n')
    return task_timings

def __norc_compile_one_row__(row):
    task = row.get_task()
    if task == None:# crappy data in statuses table
        return None
    one_row = [task.__class__.__name__, row.status, task.date_added, row.date_started, row.date_ended]
    return one_row
    
def compile_task_timings(save_stream=None):
    log.info("Compilin' Task Timin's")
    matches = core.TaskRunStatus.objects
    #matches = matches.filter(status=core.TaskRunStatus.STATUS_SUCCESS)
    matches = matches.filter(date_started__gte=datetime.datetime(2009, 5, 18, 20))
    #matches = matches.filter(date_started__lte=datetime.datetime(2009, 5, 18, 14))
    matches = matches.order_by('date_started')
    return compile_timings(matches, __norc_compile_one_row__, save_stream)

def __sqs_compile_one_row__(row):
    if not row.queue_name or not row.status or not row.date_enqueued or not row.date_started or not row.date_ended:
        return None# crap data, probably still running
    one_row = [row.queue_name, row.status, row.date_enqueued, row.date_started, row.date_ended]
    return one_row
    
def compile_sqs_timings(save_stream=None):
    log.info("Compilin' SQS Timin's")
    matches = sqs.SQSTaskRunStatus.objects
    #matches = matches.filter(status=core.TaskRunStatus.STATUS_SUCCESS)
    matches = matches.filter(date_started__gte=datetime.datetime(2009, 5, 18, 20))
    matches = matches.order_by('date_started')
    return compile_timings(matches, __sqs_compile_one_row__, save_stream)

def agg_by_task(task_timings, round_to):
    log.info("Aggin' by Task")
    
    agg = {}
    for (task_name, status, date_added, date_started, date_ended) in task_timings:
        #date_agg = round_datetime(date_added, round_to)# TODO what to do here that'd be correct?
        date_agg = round_datetime(date_started, round_to)
        task_delay = date_started - date_added
        task_duration = date_ended - date_started
        
        ensure_hash_depth(agg, task_name, status, date_agg)
        ensure_list(agg[task_name][status][date_agg], 'delay', task_delay)
        ensure_list(agg[task_name][status][date_agg], 'duration', task_duration)
    return agg

def calc_distribution(data, bucket_size, row_prefixes, max_bucket):
    data = sorted(data)
    i = 0
    buckets = []# [[bucket, #, %]...]
    curr_bucket = data[0] - mod_timedelta(data[0], bucket_size)
    last_bucket = data[-1] - mod_timedelta(data[-1], bucket_size)
    if last_bucket >= max_bucket:
        last_bucket = max_bucket
    #print 'last_bucket', last_bucket
    while curr_bucket <= last_bucket:
        end_curr_bucket = curr_bucket + bucket_size
        curr_bucket_data = []
        for i in range(i, len(data)):
            if curr_bucket <= data[i] and data[i] < end_curr_bucket:
                # this data point is in this bucket!
                curr_bucket_data.append(data[i])
            elif end_curr_bucket > last_bucket:
                i -= 1
                break
            else:
                break
        row = []
        row.extend(row_prefixes)
        row.extend([curr_bucket, len(curr_bucket_data), (float(len(curr_bucket_data)) / float(len(data)))*100])
        #print i, curr_bucket, '-', end_curr_bucket, map(str, curr_bucket_data)
        buckets.append(row)
        curr_bucket = end_curr_bucket
    
    curr_bucket_data = []
    #print i, len(data), data
    for i in range(i+1, len(data)):
        # for data beyond last bucket
        curr_bucket_data.append(data[i])
    if len(curr_bucket_data) > 0:
        raw_last_bucket = data[-1] - mod_timedelta(data[-1], bucket_size)
        row = []
        row.extend(row_prefixes)
        row.extend(['... '+str(raw_last_bucket), len(curr_bucket_data), (float(len(curr_bucket_data)) / float(len(data)))*100])
        buckets.append(row)
    
    return buckets

#
# Report
#

def rpt_avgs(timings_agg, date_delta, square_dateline):
    log.info("Reportin'")
    
    table_data = []
    header = ['Date', 'Task Name', 'Status', '#', 'Avg Delay (secs)', 'Avg Duration (secs)']
    #header2 = ['-','-','-','-','-','-']
    table_data.append(header)
    #table_data.append(header2)
    for task_name in timings_agg.keys():
        for status in timings_agg[task_name].keys():
            prev_date_agg = None
            for date_agg in sorted(timings_agg[task_name][status].keys()):
                while square_dateline \
                    and not prev_date_agg == None \
                    and prev_date_agg + date_delta < date_agg:
                    # square the date dimension
                    row = [str(prev_date_agg + date_delta), task_name, status, str(0), str(0), str(0)]
                    table_data.append(row)
                    prev_date_agg += date_delta
                delays = timings_agg[task_name][status][date_agg]['delay']
                durations = timings_agg[task_name][status][date_agg]['duration']
                row = [str(date_agg), task_name, status, len(delays), calc_avg(delays), calc_avg(durations)]
                table_data.append(row)
                prev_date_agg = date_agg
    print >>sys.stdout, ""
    formatting.pprint_table(sys.stdout, table_data)

def get_distribution_rpt(timings_agg, dist_type, bucket_size, max_bucket):
    table_data = []
    for task_name in timings_agg.keys():
        dist_input = []
        for date_agg in timings_agg[task_name].values():
            dist_input.extend(date_agg[dist_type])
        dist = calc_distribution(dist_input, bucket_size, [task_name, dist_type], max_bucket)
        table_data.extend(dist)
    return table_data

def rpt_distribution(distribution_data):
    header = ['Task Name', 'Type', 'Bucket', '#', '%']
    header2 = ['-','-','-','-','-']
    table_data = []
    table_data.append(header)
    table_data.append(header2)
    table_data.extend(distribution_data)
    print >>sys.stdout, ""
    formatting.pprint_table(sys.stdout, table_data)

def parse_timings_cache_file(fn):
    log.info("Parsing timings cache from '%s'" % (fn))
    task_timings = []
    fh = open(fn, 'r')
    for line in fh.readlines():
        parts = line.strip().split(',')
        if len(parts) == 4:
            # before status was used, it was always SUCCESS
            parts = [parts[0], 'SUCCESS', parts[1], parts[2], parts[3]]
        task_name = parts[0]
        if task_name == 'EnqueuedArchiveRequest':
            # mask different naming before SQS
            task_name = 'SQSArchiveRequest'
        elif task_name.startswith('SQSArchiveRequest'):
            # mask version
            task_name = 'SQSArchiveRequest'
        dates = [datetime.datetime(*time.strptime(date_str, "%Y-%m-%d %H:%M:%S")[:6]) for date_str in parts[2:]]
        row = [task_name, parts[1]]
        row.extend(dates)
        task_timings.append(row)
    return task_timings

#
# Main
#

def main():
    parser = OptionParser("%prog [--debug]")
    parser.add_option("--round_dates", action="store", default="10MIN"
        , help="round dates to this granularity")
    parser.add_option("--delay_bucket_size", action="store", type="int", default=60)# 1 minute
    parser.add_option("--duration_bucket_size", action="store", type="int", default=10)# 10 seconds
    parser.add_option("--max_delay", action="store", type="int", default=60*90)# 1.5 hours
    parser.add_option("--max_duration", action="store", type="int", default=60*20)# 20 minutes
    parser.add_option("--save_timings", action="store", default="./task_timings_raw.csv"
        , help="save the raw task timings data b/c querying the db is sloooow.")
    parser.add_option("--timings_cache_file", action="store"
        , help="use timings from this file")
    parser.add_option("--avg", action="store_true")
    parser.add_option("--distribution", action="store_true")
    parser.add_option("--square_dateline", action="store_true")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    log.set_logging_debug(options.debug)
    
    options.delay_bucket_size = datetime.timedelta(seconds=options.delay_bucket_size)
    options.duration_bucket_size = datetime.timedelta(seconds=options.duration_bucket_size)
    options.max_delay = datetime.timedelta(seconds=options.max_delay)
    options.max_duration = datetime.timedelta(seconds=options.max_duration)
    
    if options.timings_cache_file:
        task_timings = []
        for tcf in options.timings_cache_file.split(','):
            task_timings.extend(parse_timings_cache_file(tcf))
        log.info("Parsed %s Task Timings from cached files" % (len(task_timings)))
    elif options.save_timings:
        save_stream = open(options.save_timings, 'w')
        task_timings = []
        task_timings.extend(compile_task_timings(save_stream))
        task_timings.extend(compile_sqs_timings(save_stream))
        save_stream.close()
    else:
        task_timings = []
        task_timings.extend(compile_task_timings())
        task_timings.extend(compile_sqs_timings())
    timings_agg = agg_by_task(task_timings, options.round_dates)
    
    if options.avg:
        rpt_avgs(timings_agg, round_2_delta(options.round_dates), options.square_dateline)
    if options.distribution:
        table_data = []
        table_data.extend(get_distribution_rpt(timings_agg, 'delay', options.delay_bucket_size, options.max_delay))
        table_data.extend(get_distribution_rpt(timings_agg, 'duration', options.duration_bucket_size, options.max_duration))
        rpt_distribution(table_data)
    
    log.info("Done!")

if __name__ == '__main__':
    main()

#
