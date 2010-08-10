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
# Monitor and control running Norc daemons (norcd)
#
#
#
#
#Darrell
#04/13/2009
############################################

import sys, time
from optparse import OptionParser

from norc.core import report
from norc.core.models import NorcDaemonStatus, TaskRunStatus
from norc.norc_utils import formatting, parsing

def report_daemon_statuses(status_filter=None, since_date=None):
    tabular = [["ID", "Type", "Region", "Host", "PID", "Running",
        "Success", "Error", "Status", "Started", "Ended"]]
    if status_filter:
        nds_set = report.ndss(since_date, status_filter.lower())
    else:
        nds_set = report.ndss(since_date)
    for nds in nds_set:
        one_row = [
            str(nds.id),
            nds.get_daemon_type(),
            nds.region.get_name(),
            nds.host,
            nds.pid,
            report.trss(nds, 'running', since_date).count(),
            report.trss(nds, 'success', since_date).count(),
            report.trss(nds, 'errored', since_date).count(),
            nds.get_status(),
            nds.date_started,
            nds.date_ended if nds.is_done() else '-']
        # if nds.is_done():
        #     one_row.append(nds.date_ended)
        # else:
        #     one_row.append("-")
        tabular.append(one_row)
    
    if since_date == None:
        print >>sys.stdout, "Status as of %s" % \
            time.strftime("%m/%d/%Y %H:%M:%S")
    else:
        print >>sys.stdout, "Status from %s to %s" % \
            (since_date.strftime("%m/%d/%Y %H:%M:%S"),
             time.strftime("%m/%d/%Y %H:%M:%S"))
    
    if len(tabular) == 1:
        print >>sys.stdout, "No %s Norc daemons." % (status_filter.upper())
    else:
        print >>sys.stdout, "%s %s Norc daemon(s):" % (len(tabular)-1,
            status_filter.upper())
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

def report_norcd_details(nds, status_filter, date_started=None):
    """report details for given norcd"""
    tabular = []
    tabular.append(["Job:Task", "Status", "Started", "Ended"])
    for trs in nds.get_task_statuses(status_filter, date_started):
        row = [
            trs.task.job.get_name() + ":" + trs.task.get_name(),
            trs.get_status(),
            trs.date_started,
            trs.date_ended if trs.date_ended else '-']
        tabular.append(row)
    if not date_started == None:
        print >>sys.stdout, "From %s - Now" % (date_started.strftime("%m/%d/%Y %H:%M:%S"))
    if len(tabular) == 1:
        print >>sys.stdout, "Norc Daemon %s (%s) hasn't run any tasks\n" % (nds.id, nds.get_status())
    else:
        print >>sys.stdout, "Norc Daemon %s (%s) manages %s task(s):\n" % (nds.id, nds.get_status(), len(tabular)-1)
        formatting.pprint_table(sys.stdout, tabular)
        print >>sys.stdout, ""

# def report_sqsd_details(status_filter, sqsd, date_started=None):
#     """report details for given sqsd"""
#     include_statuses = TASK_STATUS_FILTER_2_STATUS_LIST[status_filter.lower()]
#     tabular = []
#     tabular.append(["Task ID", "Status", "Started", "Ended"])
#     for run_status in sqsd.get_task_statuses(only_statuses=include_statuses \
#         , date_started=date_started):
#         one_row = []
#         one_row.append(str(run_status.get_task_id()))
#         one_row.append(run_status.get_status())
#         one_row.append(run_status.date_started)
#         if run_status.date_ended == None:
#             one_row.append("-")
#         else:
#             one_row.append(run_status.date_ended)
#         tabular.append(one_row)
#     
#     if not date_started == None:
#         print >>sys.stdout, "From %s - Now" % (date_started.strftime("%m/%d/%Y %H:%M:%S"))
#     if len(tabular) == 1:
#         print >>sys.stdout, "SQS Daemon %s:%s (%s) hasn't run any tasks\n" % (sqsd.region.get_name(), sqsd.get_id(), sqsd.get_status())
#     else:
#         print >>sys.stdout, "SQS Daemon %s:%s (%s) manages %s task(s):\n" % (sqsd.region.get_name(), sqsd.get_id(), sqsd.get_status(), len(tabular)-1)
#         formatting.pprint_table(sys.stdout, tabular)
#         print >>sys.stdout, ""


#
# Main
#



WAIT_POLL_SECONDS = 3



def main():
    global WAIT_POLL_SECONDS
    
    #def usage():
    #    return "%prog [--status [--filter <all|running|active|errored|interesting>] | --details <id>] \
    #[--started_since <m1d|m1h|m3min|...>] \
    #[--salvage <id> | --delete <id> | \
    #[--pause <id> | --stop <id> | --kill <id> [--wait_seconds <0>] [--force]]] [--debug]"
    usage = "%prog [-f all|running|active|errored|interesting] " + \
            "[--started_since <m1d|m1h|m3min|...>] [--details <id>]\n" + \
            "%prog --pause|stop|salvage|kill|delete <id> " + \
            "[-s] [--wait <seconds>] [--force] [--debug]"
    
    def bad_args(message):
        print message
        print usage
        sys.exit(2)
    
    def error(message):
        print message
        sys.exit(1)
    
    parser = OptionParser(usage=usage, description="")
    
    # Status report mode options.
    
    parser.add_option("-f", "--filter", action="store",
        default="interesting", help="if showing status, limit to this set. Defaults to 'interesting', which is active+errored.")
    parser.add_option("--started_since", action="store",
        help="limit statuses to those since relative start date. Format is '{num}{d|h|m}'.")
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
        help="Show a status report after performing an action.")
    parser.add_option("--wait", action="store", default=0, type="int",
        help="wait for N seconds for norcd to stop after kill or stop is issued. Default is 0")
    parser.add_option("--force", action="store_true",
        help="overrides some safety checks. Use carefully by trying not to use it first.")
    parser.add_option("--debug", action="store_true",
        help="Turns on debugging.")
    (options, args) = parser.parse_args()
    
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
        options.started_since = parsing.parse_date_relative(options.started_since)
    
    # Perform an action on a Norc daemon.
    flags = ['pause', 'stop', 'kill', 'salvage', 'delete']
    selected_flags = filter(lambda a: bool(getattr(options, a)), flags)
    if len(selected_flags) > 1:
        bad_args(
            "Conflicting flags; only one action may be performed at a time.")
    
    # TODO: Review all option logic from here on to match with above changes.
    if len(selected_flags) == 1:
        nds_id = getattr(options, selected_flags[0])
        nds = report.nds(nds_id)
        if not nds:
            bad_args("No Norc daemon with id %s found." % nds_id)
        
        if options.pause and nds.is_paused() or nds.is_pause_requested():
            error("norcd %s is already paused or requested to pause." % nds.id)
        if options.stop and nds.is_stop_requested():
            raise Exception("norcd %s is already scheduled to stop. You can \
                             also try --kill <id>." % (nds.id))
        elif options.kill and nds.is_kill_requested():
            raise Exception("norcd %s is already scheduled to be killed. The only thing more severe is $kill -9 %s." % (nds.id, nds.pid))
        elif options.salvage and (not nds.is_stop_requested() and not nds.is_kill_requested() and not nds.is_paused()):
            raise Exception("norcd %s cannot be salvaged.  Its status is not paused, stop- or kill- requested" % (nds.id))
        
        if options.delete:
            if not options.force and not nds.is_done_with_error():
                raise Exception("norcd %s cannot be deleted because it has status %s. Use --force to override." % (nds.id, nds.get_status()))
            print "Deleting norcd %s" % (nds)
            nds.set_status(NorcDaemonStatus.STATUS_DELETED)
        elif options.salvage:
            print "Salvaging norcd %s" % (nds)
            nds.set_status(NorcDaemonStatus.STATUS_RUNNING)
        elif options.pause or options.stop or options.kill:
            if nds.is_done():
                raise Exception("norcd %s is not running.  It cannot be shutdown or paused." % nds.id)
            if options.pause:
                print "Sending pause request to norcd %s" % nds
                nds.set_status(NorcDaemonStatus.STATUS_PAUSEREQUESTED)
            elif options.stop:
                print "Sending stop request to norcd %s" % nds
                nds.set_status(NorcDaemonStatus.STATUS_STOPREQUESTED)
            elif options.kill:
                print "Sending kill request to norcd %s" % nds
                nds.set_status(NorcDaemonStatus.STATUS_KILLREQUESTED)
            if options.wait:
                seconds_waited = 0
                timeout = False
                while True:
                    if seconds_waited >= options.wait:
                        timeout = True
                        break
                    nds = report.nds(nds_id)
                    if nds.is_shutting_down():
                        print "Waiting for shutdown of norcd %s.  It's been %s seconds." % (nds.id, seconds_waited)
                    elif nds.is_done():
                        print "norcd %s is done with status '%s'" % (nds.id, nds.get_status())
                        break
                    else:
                        raise Exception("norcd %s shutdown was requested but not honored or was overwritten in DB. This is bad, but try \"kill <pid>\" directly." % (tms.id))
                    time.sleep(WAIT_POLL_SECONDS)
                    seconds_waited += WAIT_POLL_SECONDS
                if timeout:
                    print "Timeout reached waiting for norcd %s to finish.  Check process id %s on host '%s'" % (nds.id, nds.pid, nds.host)
                    sys.exit(1)    
    
    #if options.status or len(selected_flags) == 0:
        
    #
    # report on status
    #
    since = parsing.parse_since(options.started_since)
    report_daemon_statuses(options.filter, since_date=since)
    if options.details:
        nds_id = options.details
        nds = report.nds(nds_id)
        #daemon_type = nds.get_daemon_type()
        #if daemon_type == NorcDaemonStatus.DAEMON_TYPE_NORC:
        report_norcd_details(nds, options.filter, since)
        #elif daemon_type == NorcDaemonStatus.DAEMON_TYPE_SQS:
        #    report_sqsd_details(options.filter, nds, options.started_since)
        #else:
        #    raise Exception("Unknown daemon_type '%s'" % (daemon_type))

if __name__ == '__main__':
    main()
#
