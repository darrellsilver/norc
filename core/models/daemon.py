
"""The Norc Daemon (norcd) is defined here."""

import os
import sys
import signal
import time
from datetime import datetime, timedelta
from threading import Thread, Event
# from multiprocessing import Process
from subprocess import Popen

from django.db.models import (Model, Manager,
    CharField,
    DateTimeField,
    IntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.models.queue import Queue
from norc.core.constants import Status, CONCURRENCY_LIMIT
from norc.norc_utils.log import make_log
from norc import settings

class Daemon(Model):
    """Daemons are responsible for the running of instances.
    
    Daemons have a single queue that they pull instances from.  There
    can (and in many cases should) be more than one Daemon running for
    a single queue.
    
    """
    
    VALID_STATUSES = [
        Status.CREATED,
        Status.RUNNING,
        Status.PAUSED,
        Status.STOPPING,
        Status.ENDED,
        Status.ERROR,
        Status.KILLED,
    ]
    
    REQUEST_PAUSE = 1
    REQUEST_UNPAUSE = 2
    REQUEST_STOP = 5
    REQUEST_KILL = 6
    REQUESTS = {        # Map the names.
        REQUEST_PAUSE: 'PAUSE',
        REQUEST_UNPAUSE: 'UNPAUSE',
        REQUEST_STOP: 'STOP',
        REQUEST_KILL: 'KILL',
    }
    
    class Meta:
        app_label = 'core'
    
    # The host this daemon ran on.
    host = CharField(default=lambda: os.uname()[1], max_length=128)
    
    # The process ID of the main daemon process.
    pid = IntegerField(default=os.getpid)
    
    # The status of this daemon.
    status = PositiveSmallIntegerField(default=Status.CREATED,
        choices=[(s, Status.NAME[s]) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(k, v) for k, v in REQUESTS.iteritems()])
    
    # The last heartbeat of the daemon.
    heartbeat = DateTimeField(default=datetime.utcnow)
    
    # When the daemon was started.
    started = DateTimeField(default=datetime.utcnow)
    
    # When the daemon was ended.
    ended = DateTimeField(null=True, blank=True)
    
    # The queue this daemon draws task instances from.
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    # The number of things that can be run concurrently.
    concurrent = IntegerField()
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        self.flag = Event()
        self.processes = {}
        self.heart = Thread(target=self.heart_run)
        self.heart.daemon = True
    
    def heart_run(self):
        """Method to be called by the heart thread."""
        while not Status.is_final(self.status):
            self.heartbeat = datetime.utcnow()
            self.save(safe=True)
            time.sleep(5)
    
    def start(self):
        """Starts the daemon.  Mostly just a wrapper for run()."""
        if not hasattr(self, 'id'):
            self.save()
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        self.log.debug("Starting %s..." % self)
        self.heart.start()
        try:
            self.run()
        except Exception:
            self.set_status(Status.ERROR)
            self.log.error('Daemon suffered an internal error!', trace=True)
        self.ended = datetime.utcnow()
        self.save()
        self.log.info("%s has ended gracefully." % self)
        self.log.close()
    
    def run(self):
        """Core Daemon function.  Returns the exit status of the Daemon."""
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        if self.status != Status.CREATED:
            self.log.error("Can't start a Daemon that's already been run.")
            return Status.ERROR
        if __name__ == '__main__':
            for signum in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(signum, self.signal_handler)
        self.status = Status.RUNNING
        self.save()
        self.log.info("%s is now running on host %s." % (self, self.host))
        # Main loop.
        self.update_request()
        period = timedelta(seconds=1)
        while not Status.is_final(self.status):
            if datetime.utcnow() > self.last_request_update + period:
                self.update_request()
            if self.request:
                self.handle_request()
            elif self.status == Status.RUNNING:
                if len(self.processes) < self.concurrent:
                    instance = self.queue.pop()
                    if instance:
                        self.start_instance(instance)
                    else:
                        self._wait()
                else:
                    self._wait()
            elif self.status == Status.STOPPING and len(self.processes) == 0:
                self.set_status(Status.ENDED)
                self.save(safe=True)
            # Cleanup before iterating.
            for pid, p in self.processes.items()[:]:
                p.poll()
                self.log.debug(
                    "Checking pid %s: return code %s." % (pid, p.returncode))
                if not p.returncode == None:
                    i = p.instance.__class__.objects.get(pk=p.instance.pk)
                    self.log.info("Instance '%s' ended with status %s." %
                        (i, Status.NAME[i.status]))
                    del self.processes[pid]
    
    def start_instance(self, instance):
        """Starts a given instance in a new process."""
        instance.daemon = self
        self.log.info("Starting instance '%s'..." % instance)
        # p = Process(target=self.execute, args=[instance.start])
        # p.start()
        ct = ContentType.objects.get_for_model(instance.__class__)
        p = Popen('norc_executor --ct_pk %s --target_pk %s' %
            (ct.pk, instance.pk), shell=True)
        p.instance = instance
        self.processes[p.pid] = p
    
    def _wait(self):
        """Waits on the flag.
        
        For whatever reason, when this is done signals are no longer
        handled properly, so we must catch the exceptions explicitly.
        
        """
        try:
            self.flag.clear()
            self.flag.wait(1)
        except KeyboardInterrupt:
            self.make_request(Daemon.REQUEST_STOP)
        except SystemExit:
            self.make_request(Daemon.REQUEST_KILL)
    
    # This should be used in 2.6, but with subprocess it's not possible.
    # def execute(self, func):
    #     """Calls a function, then sets the flag after its execution."""
    #     try:
    #         func()
    #     finally:
    #         self.flag.set()
    
    def handle_request(self):
        """Called when a request is found."""
        self.log.info("Request received: %s" % Daemon.REQUESTS[self.request])
        
        if self.request == Daemon.REQUEST_PAUSE:
            self.set_status(Status.PAUSED)
        
        elif self.request == Daemon.REQUEST_UNPAUSE:
            if self.status != Status.PAUSED:
                self.log.info("Must be paused to unpause; clearing request.")
            else:
                self.set_status(Status.RUNNING)
        
        elif self.request == Daemon.REQUEST_STOP:
            self.set_status(Status.STOPPING)
        
        elif self.request == Daemon.REQUEST_KILL:
            # for p in self.processes.values():
            #     p.terminate()
            for pid, p in self.processes.iteritems():
                self.log.info("Killing process for %s." % p.instance)
                os.kill(pid, signal.SIGTERM)
            self.set_status(Status.KILLED)
        
        self.request = None
        self.save()
    
    def signal_handler(self, signum, frame):
        """Handles signal interruption."""
        sig_name = None
        # A reverse lookup to find the signal name.
        for attr in dir(signal):
            if attr.startswith('SIG') and getattr(signal, attr) == signum:
                sig_name = attr
                break
        self.log.info("Signal '%s' received!" % sig_name)
        if signum == signal.SIGINT:
            self.make_request(Daemon.REQUEST_STOP)
        else:
            self.make_request(Daemon.REQUEST_KILL)
    
    def save(self, *args, **kwargs):
        """Overwrites Model.save().
        
        We have to be very careful to never overwrite a request, so
        often the request must be read from the database prior to saving.
        The safe parameter being set to True enables this behavior.
        
        """
        if kwargs.pop('safe', False):
            try:
                self.update_request()
            except Exception:
                pass
        Model.save(self, *args, **kwargs)
    
    def update_request(self):
        """Updates the request field from the database.
        
        There doesn't appear to be an easy way to have Django refresh an
        object from the database, so this method just updates the status.
        
        """
        if hasattr(self, 'id'):
            self.request = Daemon.objects.get(id=self.id).request
            self.last_request_update = datetime.utcnow()
            return self.request
    
    def make_request(self, req):
        """This method is how the request field should always be set."""
        assert req in Daemon.REQUESTS, "Invalid request!"
        self.request = req
        self.save()
        self.flag.set()
    
    def set_status(self, status):
        """Sets the status with a log message.  Does not save."""
        self.log.info("Changing state from %s to %s." %
            (Status.NAME[self.status], Status.NAME[status]))
        self.status = status
    
    @property
    def log_path(self):
        return 'daemons/daemon-%s' % self.id
    
    def __unicode__(self):
        return u"<Daemon #%s on %s>" % (self.id, self.host)
    
    __repr__ = __unicode__
    
