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


##################################
#
# Report on task history by self-defined groups:
# Provide some macro auditing of timings by group, 
# failure rates, etc.
#
#
###################################

import sys, math
import datetime
from optparse import OptionParser

# TODO hack attack!
from norc.bin import tmsdctl
from norc.core import models as norc_models
from norc.sqs import models as sqs

from permalink.core import models as core

from utils import formatting
from utils import log
log = log.Log()


def get_run_statuses(queue_name, statuses, start_date, end_date):
    log.info("Getting run statuses for:")
    log.info("  queue: '%s'" % (queue_name))
    log.info("  statuses: %s" % (statuses))
    log.info("  from %s - %s" % (start_date, end_date))
    rss = sqs.SQSTaskRunStatus.objects
    if queue_name:
        rss = rss.filter(queue_name=queue_name)
    if statuses:
        rss = rss.filter(status__in=statuses)
    if start_date:
        rss = rss.filter(date_started__gte=start_date)
    if end_date:
        rss = rss.filter(date_started__lte=end_date)
    return rss

def get_run_statuses_by_daemon(daemon_id, statuses):
    log.info("Getting run statuses for:")
    log.info("  daemon_id: '%s'" % (daemon_id))
    log.info("  statuses: %s" % (statuses))
    nds = tmsdctl.get_nds(daemon_id)
    tss = nds.get_task_statuses(only_statuses=statuses)
    return tss
    

def add_or_append(h, key, value):
    if not h.has_key(key):
        h[key] = []
    h[key].append(value)

def agg_statuses(run_statuses):
    log.info("Aggregating statuses")
    agged = {}
    for rs in run_statuses:
        a = core.Archives.objects.get(id=rs.task_id)
        add_or_append(agged, a.url.url, [rs, a])
    return agged

def _format_cell_max_size(d):
    if len(d) < 50:
        return d
    return d[:46] +" ..."

def _calc_agg_stats(l):
    """
    Calc min, max, avg timings
    """
    total_duration = 0
    min_duration = 0
    max_duration = 0
    
    for (rs, a) in l:
        one_duration = rs.date_ended - rs.date_started
        if one_duration.seconds > max_duration or max_duration == 0:
            max_duration = one_duration.seconds
        if one_duration.seconds < min_duration or min_duration == 0:
            min_duration = one_duration.seconds
        total_duration += one_duration.seconds
    
    avg = float(total_duration) / float(len(l))
    return (min_duration, max_duration, avg)

def _get_rand_keys(l, max_len):
    rand = []
    for (rs, a) in l[:max_len]:
        rand.append(int(a.id))
    return rand

def rpt_agg(agged):
    tabular = []
    header = ["Key", "Count", "Min (secs)", "Avg", "Max", "Random Subset"]
    for key in agged.keys():
        values = agged[key]
        one_row = []
        one_row.append(_format_cell_max_size(key))
        one_row.append(len(values))
        # use '_' to avoid confusion w/ built-in 'min', 'max'
        (min_, max_, avg_) = _calc_agg_stats(values)
        one_row.append(min_)
        one_row.append(avg_)
        one_row.append(max_)
        one_row.append(_get_rand_keys(values, 5))
        
        tabular.append(one_row)
    
    def sort(a, b):
        return cmp(b[1], a[1])
    
    tabular.sort(sort)
    tabular.insert(0, header)
    
    if len(agged.keys()) == 0:
        log.info("Nothing to aggregate")
    else:
        print >>sys.stdout, "Aggregate statistics for %s key(s):" % (len(agged.keys()))
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

def _parse_date(date_str):
    (m, d, y) = map(int, date_str.split("/"))
    date = datetime.datetime(year=y, month=m, day=d)
    return date
#
#
#

def main():
    parser = OptionParser("""%prog --queue_name <name> | --daemon_id <id>
[--filter_status <interesting>]
[--start_date <mm/dd/yyyy>] [--end_date <mm/dd/yyyy>] 
[--debug]""")
    parser.add_option("--daemon_id", action="store")
    parser.add_option("--queue_name", action="store")
    parser.add_option("--filter_status", action="store", default="interesting"
        , help="if showing status, limit to this set. Defaults to 'interesting', which is active+errored.")
    parser.add_option("--start_date", action="store")
    parser.add_option("--end_date", action="store")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    if not options.queue_name and not options.daemon_id:
        sys.exit(parser.get_usage())
    
    if options.debug:
        log.set_logging_debug(options.debug)
    
    if options.start_date:
        options.start_date = _parse_date(options.start_date)
    if options.end_date:
        options.end_date = _parse_date(options.end_date)
    
    #queue_name = "SQSArchiveRequest-DEV"
    #filter_status = "all"
    #queue_name = "SQSArchiveRequest-NORMAL"
    #filter_status = "errored"
    
    statuses = None
    if tmsdctl.TASK_STATUS_FILTER_2_STATUS_LIST.has_key(options.filter_status):
        statuses = tmsdctl.TASK_STATUS_FILTER_2_STATUS_LIST[options.filter_status]
    elif options.filter_status == norc_models.TaskRunStatus.STATUS_TIMEDOUT:
        statuses = [norc_models.TaskRunStatus.STATUS_TIMEDOUT]
    elif options.filter_status == norc_models.TaskRunStatus.STATUS_ERROR:
        statuses = [norc_models.TaskRunStatus.STATUS_ERROR]
    elif options.filter_status == norc_models.TaskRunStatus.STATUS_ERROR:
        statuses = [norc_models.TaskRunStatus.STATUS_ERROR]
    elif options.filter_status == norc_models.TaskRunStatus.STATUS_SUCCESS:
        statuses = [norc_models.TaskRunStatus.STATUS_SUCCESS]
    elif options.filter_status == norc_models.TaskRunStatus.STATUS_RUNNING:
        statuses = [norc_models.TaskRunStatus.STATUS_RUNNING]
    else:
        raise Exception("Unknown filter_status '%s'" % (options.filter_status))
    
    if options.daemon_id:
        run_statuses = get_run_statuses_by_daemon(options.daemon_id, statuses)
    else:
        run_statuses = get_run_statuses(options.queue_name, statuses
            , options.start_date, options.end_date)
    agged = agg_statuses(run_statuses)
    rpt_agg(agged)

if __name__ == '__main__':
    main()

#
