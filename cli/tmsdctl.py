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



############################################
#
#
# Monitor and control running Norc daemons (tmsd)
#
#
#
#
#Darrell
#04/13/2009
############################################

import re, sys, time, datetime
from optparse import OptionParser

from norc.core import reporter
from norc.core.models import NorcDaemonStatus, TaskRunStatus
from norc import settings

from utils import formatting
from utils import log
log = log.Log(settings.LOGGING_DEBUG)

#
#
#

DAEMON_STATUS_FILTER_2_STATUS_LIST = {}
DAEMON_STATUS_FILTER_2_STATUS_LIST['running'] = [NorcDaemonStatus.STATUS_RUNNING]
DAEMON_STATUS_FILTER_2_STATUS_LIST['active'] = [NorcDaemonStatus.STATUS_STARTING
                                            , NorcDaemonStatus.STATUS_RUNNING
                                            , NorcDaemonStatus.STATUS_PAUSEREQUESTED
                                            , NorcDaemonStatus.STATUS_STOPREQUESTED
                                            , NorcDaemonStatus.STATUS_KILLREQUESTED
                                            , NorcDaemonStatus.STATUS_PAUSED
                                            , NorcDaemonStatus.STATUS_STOPINPROGRESS
                                            , NorcDaemonStatus.STATUS_KILLINPROGRESS]
DAEMON_STATUS_FILTER_2_STATUS_LIST['errored'] = [NorcDaemonStatus.STATUS_ERROR]
DAEMON_STATUS_FILTER_2_STATUS_LIST['interesting'] = []
DAEMON_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(DAEMON_STATUS_FILTER_2_STATUS_LIST['active'])
DAEMON_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(DAEMON_STATUS_FILTER_2_STATUS_LIST['errored'])
DAEMON_STATUS_FILTER_2_STATUS_LIST['all'] = None# meaning all of them

TASK_STATUS_FILTER_2_STATUS_LIST = {}
TASK_STATUS_FILTER_2_STATUS_LIST['running'] = [TaskRunStatus.STATUS_RUNNING]
TASK_STATUS_FILTER_2_STATUS_LIST['active'] = [TaskRunStatus.STATUS_RUNNING]
TASK_STATUS_FILTER_2_STATUS_LIST['errored'] = [TaskRunStatus.STATUS_ERROR
                                            , TaskRunStatus.STATUS_TIMEDOUT]
TASK_STATUS_FILTER_2_STATUS_LIST['success'] = [TaskRunStatus.STATUS_SUCCESS
                                            , TaskRunStatus.STATUS_CONTINUE]
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'] = []
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(TASK_STATUS_FILTER_2_STATUS_LIST['active'])
TASK_STATUS_FILTER_2_STATUS_LIST['interesting'].extend(TASK_STATUS_FILTER_2_STATUS_LIST['errored'])
TASK_STATUS_FILTER_2_STATUS_LIST['all'] = None# meaning all of them


def report_tmsd_status(status_filter, norc_list=None, max_tasks_due_to_run=None, date_started=None):
    include_statuses = DAEMON_STATUS_FILTER_2_STATUS_LIST[status_filter.lower()]
    if norc_list == None:
        matches = NorcDaemonStatus.objects.filter()
        norc_list = matches.all()
    tabular = []
    tabular.append(["ID", "Type", "Region", "Host", "PID", "Running", "Success", "Error", "Status", "Started", "Ended"])
    for tds in norc_list:
        if not include_statuses == None and not tds.get_status() in include_statuses:
            continue
        one_row = []
        one_row.append(str(tds.id))
        one_row.append(tds.get_daemon_type())
        one_row.append(tds.get_region().get_name())
        one_row.append(tds.host)
        one_row.append(tds.pid)
        # don't apply start_date to running tasks; showing all gives better monitoring
        one_row.append(len(tds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['running'])))
        one_row.append(len(tds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['success'] \
            , date_started=date_started)))
        one_row.append(len(tds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['errored'] \
            , date_started=date_started)))
        one_row.append(tds.get_status())
        one_row.append(tds.date_started)
        if tds.is_done():
            one_row.append(tds.date_ended)
        else:
            one_row.append("-")
        tabular.append(one_row)
    
    print >>sys.stdout, "Status as of %s" % (time.strftime("%m/%d/%Y %H:%M:%S"))
    if not date_started == None:
        print >>sys.stdout, "From %s to Now" % (date_started.strftime("%m/%d/%Y %H:%M:%S"))
    if not max_tasks_due_to_run in (None, 0):
        # This call is currently super expensive when there's lots of Tasks; limit it!
        to_run = reporter.get_tasks_allowed_to_run(max_to_return=max_tasks_due_to_run)
        if len(to_run) < max_tasks_due_to_run:
            print >>sys.stdout, "%s Task(s) due to run.\n" % (len(to_run))
        else:
            print >>sys.stdout, "At least %s Task(s) due to run.\n" % (len(to_run))
    
    if len(tabular) == 1:
        print >>sys.stdout, "No %s tms daemons" % (status_filter.upper())
    else:
        print >>sys.stdout, "%s %s tms daemon(s):" % (len(tabular)-1, status_filter.upper())
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

def report_tmsd_details(status_filter, tmsd, date_started=None):
    """report details for given tmsd"""
    include_statuses = TASK_STATUS_FILTER_2_STATUS_LIST[status_filter.lower()]
    tabular = []
    tabular.append(["Job:Task", "Status", "Started", "Ended"])
    for run_status in tmsd.get_task_statuses(only_statuses=include_statuses \
        , date_started=date_started):
        one_row = []
        one_row.append(run_status.task.get_job().get_name() +":"+ run_status.task.get_name())
        one_row.append(run_status.get_status())
        one_row.append(run_status.date_started)
        if run_status.date_ended == None:
            one_row.append("-")
        else:
            one_row.append(run_status.date_ended)
        tabular.append(one_row)
    if not date_started == None:
        print >>sys.stdout, "From %s - Now" % (date_started.strftime("%m/%d/%Y %H:%M:%S"))
    if len(tabular) == 1:
        print >>sys.stdout, "TMS Daemon %s (%s) hasn't run any tasks\n" % (tmsd.id, tmsd.get_status())
    else:
        print >>sys.stdout, "TMS Daemon %s (%s) manages %s task(s):\n" % (tmsd.id, tmsd.get_status(), len(tabular)-1)
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

def report_sqsd_details(status_filter, sqsd, date_started=None):
    """report details for given sqsd"""
    include_statuses = TASK_STATUS_FILTER_2_STATUS_LIST[status_filter.lower()]
    tabular = []
    tabular.append(["Task ID", "Status", "Started", "Ended"])
    for run_status in sqsd.get_task_statuses(only_statuses=include_statuses \
        , date_started=date_started):
        one_row = []
        one_row.append(str(run_status.get_task_id()))
        one_row.append(run_status.get_status())
        one_row.append(run_status.date_started)
        if run_status.date_ended == None:
            one_row.append("-")
        else:
            one_row.append(run_status.date_ended)
        tabular.append(one_row)
    
    if not date_started == None:
        print >>sys.stdout, "From %s - Now" % (date_started.strftime("%m/%d/%Y %H:%M:%S"))
    if len(tabular) == 1:
        print >>sys.stdout, "SQS Daemon %s:%s (%s) hasn't run any tasks\n" % (sqsd.get_region().get_name(), sqsd.get_id(), sqsd.get_status())
    else:
        print >>sys.stdout, "SQS Daemon %s:%s (%s) manages %s task(s):\n" % (sqsd.get_region().get_name(), sqsd.get_id(), sqsd.get_status(), len(tabular)-1)
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""


def get_tds(id):
    try:
        assert not id == None, "ID Cannot be None"
        tds = NorcDaemonStatus.objects.get(id=id)
        return tds
    except NorcDaemonStatus.DoesNotExist:
        raise Exception("tmsd %s does not exist" % (id))

#
# Main
#

def _parse_date_relative(date, back):
    parser = re.compile("([mp])([0-9]*)(d|h|min)")
    parsed = parser.findall(back)
    if not len(parsed) == 1:
        raise TypeError("Could not parse '%s'" % (back))
    (sign, num, units) = parsed[0]
    if sign == 'm':
        sign = -1
    else:
        sign = 1
    num = int(num)
    if units == 'd':
        td = datetime.timedelta(days=sign*num)
    elif units == 'h':
        td = datetime.timedelta(hours=sign*num)
    elif units == 'min':
        td = datetime.timedelta(minutes=sign*num)
    
    return date + td

WAIT_POLL_SECONDS = 3

def usage():
    return "%prog [--status [--filter_status <all|running|active|errored|interesting>] | --details <id>] \
[--started_since <m1d|m1h|m3min|...>] \
[--salvage <id> | --delete <id> | \
[--pause <id> | --stop <id> | --kill <id> [--wait_seconds <0>] [--force]]] [--debug]"

def main():
    global WAIT_POLL_SECONDS
    
    parser = OptionParser(usage())
    parser.add_option("--status", action="store_true"
        , help="show status of all running norc daemons.")
    parser.add_option("--started_since", action="store"
        , help="limit statuses to those since relative start date. Format is 'm{num}{d|h|min}'.")
    parser.add_option("--details", action="store", type="int"
        , help="show details for tmsd given by id.")
    parser.add_option("--filter_status", action="store", default="interesting"
        , help="if showing status, limit to this set. Defaults to 'interesting', which is active+errored.")
    parser.add_option("--salvage", action="store"
        , type="int", help="don't exit tms daemon as requested; leave it running.")
    parser.add_option("--pause", action="store", type="int"
        , help="pause the tms daemon of given ID so no more tasks are run")
    parser.add_option("--stop", action="store", type="int"
        , help="stop the tms daemon of given ID after all currently running tasks have finished")
    parser.add_option("--kill", action="store"
        , type="int", help="immediately kill the tms daemon of given ID")
    parser.add_option("--delete", action="store"
        , type="int", help="mark tms daemon of given ID as deleted for convenience. Only changes DB.")
    parser.add_option("--wait_seconds", action="store", default=0
        , type="int", help="wait for N seconds for tmsd to stop after kill or stop is issued. Default is 0")
    parser.add_option("--force", action="store_true", help="overrides some safety checks. Use carefully by trying not to use it first.")
    parser.add_option("--due_to_run", action="store", type="int"
        , help="show a max # of Tasks due to run (currently an expensive DB call)")
    parser.add_option("--debug", action="store_true", help="more messages")
    (options, args) = parser.parse_args()
    
    if options.debug:
        log.set_logging_debug(options.debug)
    
    if not options.status and not options.details \
        and not options.pause and not options.stop and not options.kill \
        and not options.salvage and not options.delete:
        raise Exception(usage())
    if options.stop and (options.kill or options.salvage or options.details or options.pause) \
        or options.kill and (options.stop or options.salvage or options.details or options.pause) \
        or options.details and (options.kill or options.stop or options.salvage or options.pause) \
        or options.pause and (options.kill or options.stop or options.salvage or options.details):
        raise Exception(usage())
    
    if options.started_since:
        options.started_since = _parse_date_relative(datetime.datetime.utcnow(), options.started_since)
    
    #
    # edit a tmsd
    #
    tds_id = None; tds = None
    if options.pause:
        tds_id = options.pause
    elif options.stop:
        tds_id = options.stop
    elif options.kill:
        tds_id = options.kill
    elif options.salvage:
        tds_id = options.salvage
    elif options.delete:
        tds_id = options.delete
    elif options.details:
        tds_id = options.details
    
    if not tds_id == None:
        tds = get_tds(tds_id)
        if options.pause and tds.is_paused() or tds.is_pause_requested():
            raise Exception("tmsd %s is already paused or pause has been \
                             requested." % (tds.id))
        if options.stop and tds.is_stop_requested():
            raise Exception("tmsd %s is already scheduled to stop. You can \
                             also try --kill <id>." % (tds.id))
        elif options.kill and tds.is_kill_requested():
            raise Exception("tmsd %s is already scheduled to be killed. The only thing more severe is $kill -9 %s." % (tds.id, tds.pid))
        elif options.salvage and (not tds.is_stop_requested() and not tds.is_kill_requested() and not tds.is_paused()):
            raise Exception("tmsd %s cannot be salvaged.  Its status is not paused, stop- or kill- requested" % (tds.id))
    
    if options.delete:
        if not options.force and not tds.is_done_with_error():
            raise Exception("tmsd %s cannot be deleted because it has status %s. Use --force to override." % (tds.id, tds.get_status()))
        log.info("Deleting tmsd %s" % (tds))
        tds.set_status(NorcDaemonStatus.STATUS_DELETED)
    elif options.salvage:
        log.info("Salvaging tmsd %s" % (tds))
        tds.set_status(NorcDaemonStatus.STATUS_RUNNING)
    elif options.pause or options.stop or options.kill:
        if tds.is_done():
            raise Exception("tmsd %s is not running.  It cannot be shutdown or paused." % (tds.id))
        if options.pause:
            log.info("Sending pause request to tmsd %s" % (tds))
            tds.set_status(NorcDaemonStatus.STATUS_PAUSEREQUESTED)
        elif options.stop:
            log.info("Sending stop request to tmsd %s" % (tds))
            tds.set_status(NorcDaemonStatus.STATUS_STOPREQUESTED)
        elif options.kill:
            log.info("Sending kill request to tmsd %s" % (tds))
            tds.set_status(NorcDaemonStatus.STATUS_KILLREQUESTED)
        #
        if options.wait_seconds:
            seconds_waited = 0
            timeout = False
            while True:
                if seconds_waited >= options.wait_seconds:
                    timeout = True
                    break
                tds = get_tds(tds_id)
                if tds.is_shutting_down():
                    log.info("Waiting for shutdown of tmsd %s.  It's been %s seconds." % (tds.id, seconds_waited), indent_chars=4)
                elif tds.is_done():
                    log.info("tmsd %s is done with status '%s'" % (tds.id, tds.get_status()))
                    break
                else:
                    raise Exception("tmsd %s shutdown was requested but not honored or was overwritten in DB. This is bad, but try \"kill <pid>\" directly." % (tms.id))
                time.sleep(WAIT_POLL_SECONDS)
                seconds_waited += WAIT_POLL_SECONDS
            if timeout:
                log.info("Timeout reached waiting for tmsd %s to finish.  Check process id %s on host '%s'" % (tds.id, tds.pid, tds.host))
                sys.exit(1)
    
    #
    # report on status
    #
    
    if options.status and not tds == None:
        report_tmsd_status(options.filter_status, [tds] \
            , max_tasks_due_to_run=options.due_to_run, date_started=options.started_since)
    elif options.status:
        report_tmsd_status(options.filter_status \
            , max_tasks_due_to_run=options.due_to_run, date_started=options.started_since)
    if options.details:
        daemon_type = tds.get_daemon_type()
        if daemon_type == NorcDaemonStatus.DAEMON_TYPE_TMS:
            report_tmsd_details(options.filter_status, tds, date_started=options.started_since)
        elif daemon_type == NorcDaemonStatus.DAEMON_TYPE_SQS:
            report_sqsd_details(options.filter_status, tds, date_started=options.started_since)
        else:
            raise Exception("Unknown daemon_type '%s'" % (daemon_type))


if __name__ == '__main__':
    main()
#
