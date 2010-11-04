
import os
import sys
import signal
import time
from datetime import datetime, timedelta
from threading import Thread, Event

from django.db.models.query import QuerySet
from django.db.models import Model, CharField, DateTimeField, IntegerField

from norc import settings
from norc.core.constants import (Status, Request,
    HEARTBEAT_PERIOD, HEARTBEAT_FAILED)
from norc.norc_utils.log import make_log
from norc.norc_utils.backup import backup_log

class AbstractDaemon(Model):
    
    class Meta:
        app_label = "core"
        abstract = True
    
    class QuerySet(QuerySet):
        
        def alive(self):
            """Running executors with a recent heartbeat."""
            cutoff = datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
            return self.status_in("active").filter(
                heartbeat__isnull=False).filter(heartbeat__gt=cutoff)
        
        def since(self, since):
            """Date ended since a certain time, or not ended."""
            if type(since) == str:
                since = parse_since(since)
            return self.exclude(ended__lt=since) if since else self
        
        def status_in(self, statuses):
            """Filter by status group. Takes a string or iterable."""
            if isinstance(statuses, basestring):
                statuses = Status.GROUPS(statuses)
            return self.filter(status__in=statuses) if statuses else self
    
    # The host this daemon ran on.
    host = CharField(default=lambda: os.uname()[1], max_length=128)
    
    # The process ID of the main daemon process.
    pid = IntegerField(default=os.getpid)
    
    # The datetime of the daemon's last heartbeat.  Used in conjunction
    # with the active flag to determine whether a Scheduler is still alive.
    heartbeat = DateTimeField(null=True)
    
    # When this daemon started.
    started = DateTimeField(null=True)
    
    # When this daemon ended.
    ended = DateTimeField(null=True, blank=True)
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        self.flag = Event()
        self.heart = Thread(target=self.heart_run)
        self.heart.daemon = True
    
    def heart_run(self):
        """Method to be run by the heart thread."""
        while not Status.is_final(self.status):
            start = time.time()
            
            self.heartbeat = datetime.utcnow()
            self.save(safe=True)
            
            # In case the database is slow and saving takes longer
            # than HEARTBEAT_PERIOD to complete.
            wait = HEARTBEAT_PERIOD - (time.time() - start)
            if wait > 0:
                time.sleep(wait)
    
    def start(self):
        """Starts the daemon.  Does initialization then calls run()."""
        if self.status != Status.CREATED:
            print "Can't start a %s that's already been run." \
                % type(self).__name__
            return
        if not hasattr(self, 'id'):
            self.save()
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        try:
            for signum in (signal.SIGINT, signal.SIGTERM):
                signal.signal(signum, self.signal_handler)
        except ValueError:
            pass
        self.log.start_redirect()
        self.log.info("%s initialized; starting..." % self)
        self.status = Status.RUNNING
        self.heartbeat = self.started = datetime.utcnow()
        self.save()
        self.heart.start()
        try:
            self.run()
        except Exception:
            self.set_status(Status.ERROR)
            self.log.error("An internal error occured!", trace=True)
        else:
            if not Status.is_final(self.status):
                self.set_status(Status.ENDED)
        finally:    
            self.log.info("Shutting down...")
            try:
                self.clean_up()
            except:
                self.log.error("Clean up function failed.", trace=True)
            if not Status.is_final(self.status):
                self.set_status(Status.ERROR)
            self.heart.join()
            self.ended = datetime.utcnow()
            self.save()
            if settings.BACKUP_SYSTEM:
                self.log.info('Backing up log file...')
                if backup_log(self.log_path):
                    self.log.info('Completed log backup.')
                else:
                    self.log.info('Failed to backup log.')
            self.log.info('%s has been shut down successfully.' % self)
            self.log.stop_redirect()
            self.log.close()
            sys.exit(0)
    
    def run(self):
        raise NotImplementedError
    
    def clean_up(self):
        pass
    
    def signal_handler(self, signum, frame=None):
        """Handles signal interruption."""
        sig_name = None
        print signum
        # A reverse lookup to find the signal name.
        for attr in dir(signal):
            if attr.startswith('SIG') and getattr(signal, attr) == signum:
                sig_name = attr
                break
        self.log.info("Signal '%s' received!" % (sig_name or signum))
        if signum == signal.SIGINT:
            self.make_request(Request.STOP)
        elif signum == signal.SIGTERM:
            self.make_request(Request.KILL)
        
    
    def wait(self, t=1):
        """Waits on the flag.
        
        For whatever reason, when this is done signals are no longer
        handled properly, so we must catch the exceptions explicitly.
        
        """
        self.flag.clear()
        self.flag.wait(t)
    
    def is_alive(self):
        """Whether the Daemon is still alive.
        
        A Daemon is defined as alive if its status is not final and its
        last heartbeat was within the last HEARTBEAT_FAILED seconds.
        
        """
        return not Status.is_final(self.status) \
            and self.heartbeat and self.heartbeat > \
            datetime.utcnow() - timedelta(seconds=HEARTBEAT_FAILED)
    
    def set_status(self, status):
        """Sets the status with a log message.  Does not save."""
        self.log.info("Changing state from %s to %s." %
            (Status.name(self.status), Status.name(status)))
        self.status = status
    
    def make_request(self, request):
        """This method is how the request field should always be set."""
        assert request in self.VALID_REQUESTS, "Invalid request: " + \
            "\"%s\" (%s)" % (Request.name(request), request)
        if not Status.is_final(self.status):
            self.request = request
            self.save()
            self.flag.set()
            return True
        else:
            return False
    
    def save(self, *args, **kwargs):
        """Overwrites Model.save().
        
        We have to be very careful to never overwrite a request, so
        often the request must be read from the database prior to saving.
        The safe parameter being set to True enables this behavior.
        
        """
        if kwargs.pop('safe', False):
            try:
                self.request = self.objects.get(id=self.id).request
            except Exception:
                pass
        return Model.save(self, *args, **kwargs)
    
