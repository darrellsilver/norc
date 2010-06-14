#!/usr/bin/python

#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
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



def report_daemon_statuses(status_filter, norc_list=None, since_date=None):
    tabular = []
    tabular.append(["ID", "Type", "Region", "Host", "PID", "Running",
        "Success", "Error", "Status", "Started", "Ended"])
    for nds in reporter.get_daemon_statuses(status_filter.lower()):
        one_row = []
        one_row.append(str(nds.id))
        one_row.append(nds.get_daemon_type())
        one_row.append(nds.get_region().get_name())
        one_row.append(nds.host)
        one_row.append(nds.pid)
        # don't apply start_date to running tasks; showing all gives better monitoring
        one_row.append(len(nds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['running'])))
        one_row.append(len(nds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['success'],
            since_date=since_date)))
        one_row.append(len(nds.get_task_statuses(
            only_statuses=TASK_STATUS_FILTER_2_STATUS_LIST['errored'],
            since_date=since_date)))
        one_row.append(nds.get_status())
        one_row.append(nds.date_started)
        if nds.is_done():
            one_row.append(nds.date_ended)
        else:
            one_row.append("-")
        tabular.append(one_row)
    
    if since_date == None:
        print >>sys.stdout, "Status as of %s" % \
            time.strftime("%m/%d/%Y %H:%M:%S")
    else:
        print >>sys.stdout, "Status from %s to %s" % \
            (since_date.strftime("%m/%d/%Y %H:%M:%S"), time.strftime("%m/%d/%Y %H:%M:%S"))
    
    # if not max_tasks_due_to_run in (None, 0):
    #         # This call is currently super expensive when there's lots of Tasks; limit it!
    #         to_run = reporter.get_tasks_allowed_to_run(max_to_return=max_tasks_due_to_run)
    #         if len(to_run) < max_tasks_due_to_run:
    #             print >>sys.stdout, "%s Task(s) due to run.\n" % (len(to_run))
    #         else:
    #             print >>sys.stdout, "At least %s Task(s) due to run.\n" % (len(to_run))
    
    if len(tabular) == 1:
        print >>sys.stdout, "No %s Norc daemons." % (status_filter.upper())
    else:
        print >>sys.stdout, "%s %s Norc daemon(s):" % (len(tabular)-1, status_filter.upper())
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

def report_daemon_details(status_filter, tmsd, date_started=None):
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


def get_nds(id):
    try:
        assert not id == None, "ID Cannot be None"
        nds = NorcDaemonStatus.objects.get(id=id)
        return nds
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



def main():
    global WAIT_POLL_SECONDS
    
    def usage():
    #    return "%prog [--status [--filter <all|running|active|errored|interesting>] | --details <id>] \
    #[--started_since <m1d|m1h|m3min|...>] \
    #[--salvage <id> | --delete <id> | \
    #[--pause <id> | --stop <id> | --kill <id> [--wait_seconds <0>] [--force]]] [--debug]"
        return "%prog [-f all|running|active|errored|interesting] " + \
               "[--started_since <m1d|m1h|m3min|...>] [--details <id>]\n" + \
               "%prog --pause|stop|salvage|kill|delete <id> " + \
               "[-s] [--wait <seconds>] [--force] [--debug]"
    
    parser = OptionParser(usage=usage(), description="")
    
    # Status report mode options.
    
    parser.add_option("-f", "--filter", action="store",
        default="interesting", help="if showing status, limit to this set. Defaults to 'interesting', which is active+errored.")
    parser.add_option("--started_since", action="store",
        help="limit statuses to those since relative start date. Format is 'm{num}{d|h|min}'.")
    parser.add_option("--details", action="store", type="int",
        help="Show details for the Norc daemon with the given ID.")
    parser.add_option("--due_to_run", action="store", type="int",
        help="show a max # of Tasks due to run (currently an expensive DB call)")
    
    # Administration mode options.
    
    parser.add_option("--salvage", action="store", type="int",
        help="don't exit tms daemon as requested; leave it running.")
    parser.add_option("--pause", action="store", type="int",
        help="pause the tms daemon of given ID so no more tasks are run")
    parser.add_option("--stop", action="store", type="int",
        help="stop the tms daemon of given ID after all currently running tasks have finished")
    parser.add_option("--kill", action="store", type="int",
        help="immediately kill the tms daemon of given ID")
    parser.add_option("--delete", action="store", type="int",
        help="mark tms daemon of given ID as deleted for convenience. Only changes DB.")
    parser.add_option("-s", "--status", action="store_true",
        help="Force a status report after performing an action.")
    parser.add_option("--wait", action="store", default=0, type="int",
        help="wait for N seconds for tmsd to stop after kill or stop is issued. Default is 0")
    parser.add_option("--force", action="store_true",
        help="overrides some safety checks. Use carefully by trying not to use it first.")
    parser.add_option("--debug", action="store_true",
        help="Turns on debugging.")
    (options, args) = parser.parse_args()
    
    if options.debug:
        log.set_logging_debug(options.debug)
    
    #if not options.status and not options.details \
    #    and not options.pause and not options.stop and not options.kill \
    #    and not options.salvage and not options.delete:
    #    raise Exception(usage())
    #if options.stop and (options.kill or options.salvage or options.details or options.pause) \
    #    or options.kill and (options.stop or options.salvage or options.details or options.pause) \
    #    or options.details and (options.kill or options.stop or options.salvage or options.pause) \
    #    or options.pause and (options.kill or options.stop or options.salvage or options.details):
    #    raise Exception(usage())
    
    if options.started_since:
        options.started_since = _parse_date_relative(datetime.datetime.utcnow(), options.started_since)
    
    # Perform an action on a Norc daemon.
    flags = ['pause', 'stop', 'kill', 'salvage', 'delete']
    selected_flags = filter(lambda a: bool(getattr(options, a)), flags)
    if len(selected_flags) > 1:
        print "Conflicting flags; only one action may be performed at a time."
        sys.exit(2)
    
    # TODO: Review all option logic from here on to match with above changes.
    if len(selected_flags) == 1:
        nds_id = getattr(options, selected_flags[0])
        nds = reporter.get_nds(nds_id)
        
        if not nds_id == None:
            nds = reporter.get_nds(nds_id)
            if options.pause and nds.is_paused() or nds.is_pause_requested():
                raise Exception("tmsd %s is already paused or pause has been \
                                 requested." % (nds.id))
            if options.stop and nds.is_stop_requested():
                raise Exception("tmsd %s is already scheduled to stop. You can \
                                 also try --kill <id>." % (nds.id))
            elif options.kill and nds.is_kill_requested():
                raise Exception("tmsd %s is already scheduled to be killed. The only thing more severe is $kill -9 %s." % (nds.id, nds.pid))
            elif options.salvage and (not nds.is_stop_requested() and not nds.is_kill_requested() and not nds.is_paused()):
                raise Exception("tmsd %s cannot be salvaged.  Its status is not paused, stop- or kill- requested" % (nds.id))

        if options.delete:
            if not options.force and not nds.is_done_with_error():
                raise Exception("tmsd %s cannot be deleted because it has status %s. Use --force to override." % (nds.id, nds.get_status()))
            log.info("Deleting tmsd %s" % (nds))
            nds.set_status(NorcDaemonStatus.STATUS_DELETED)
        elif options.salvage:
            log.info("Salvaging tmsd %s" % (nds))
            nds.set_status(NorcDaemonStatus.STATUS_RUNNING)
        elif options.pause or options.stop or options.kill:
            if nds.is_done():
                raise Exception("tmsd %s is not running.  It cannot be shutdown or paused." % (nds.id))
            if options.pause:
                log.info("Sending pause request to tmsd %s" % (nds))
                nds.set_status(NorcDaemonStatus.STATUS_PAUSEREQUESTED)
            elif options.stop:
                log.info("Sending stop request to tmsd %s" % (nds))
                nds.set_status(NorcDaemonStatus.STATUS_STOPREQUESTED)
            elif options.kill:
                log.info("Sending kill request to tmsd %s" % (nds))
                nds.set_status(NorcDaemonStatus.STATUS_KILLREQUESTED)
            #
            if options.wait_seconds:
                seconds_waited = 0
                timeout = False
                while True:
                    if seconds_waited >= options.wait_seconds:
                        timeout = True
                        break
                    nds = get_nds(nds_id)
                    if nds.is_shutting_down():
                        log.info("Waiting for shutdown of tmsd %s.  It's been %s seconds." % (nds.id, seconds_waited), indent_chars=4)
                    elif nds.is_done():
                        log.info("tmsd %s is done with status '%s'" % (nds.id, nds.get_status()))
                        break
                    else:
                        raise Exception("tmsd %s shutdown was requested but not honored or was overwritten in DB. This is bad, but try \"kill <pid>\" directly." % (tms.id))
                    time.sleep(WAIT_POLL_SECONDS)
                    seconds_waited += WAIT_POLL_SECONDS
                if timeout:
                    log.info("Timeout reached waiting for tmsd %s to finish.  Check process id %s on host '%s'" % (nds.id, nds.pid, nds.host))
                    sys.exit(1)    
    
    #if options.status or len(selected_flags) == 0:
        
    #
    # report on status
    #
    
    report_daemon_statuses(options.filter, since_date=options.started_since)
    if options.details:
        nds_id = getattr(options, options.details)
        nds = reporter.get_nds(nds_id)
        daemon_type = nds.get_daemon_type()
        if daemon_type == NorcDaemonStatus.DAEMON_TYPE_TMS:
            report_tmsd_details(options.filter, nds, date_started=options.started_since)
        elif daemon_type == NorcDaemonStatus.DAEMON_TYPE_SQS:
            report_sqsd_details(options.filter, nds, date_started=options.started_since)
        else:
            raise Exception("Unknown daemon_type '%s'" % (daemon_type))


if __name__ == '__main__':
    main()
#
