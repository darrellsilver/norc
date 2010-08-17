
import os
import sys
import signal
import time
from datetime import datetime, timedelta
from threading import Thread
from multiprocessing import Process, Event, TimeoutError

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

HANDLED_SIGNALS = [signal.SIGINT, signal.SIGTERM]

class Daemon(Model):
    """Daemons are responsible for the running of Tasks."""
    
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
    REQUESTS = {
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
        choices=[(s, Status.NAMES[s]) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(k, v) for k, v in REQUESTS.iteritems()])
    
    # The last heartbeat of the daemon.
    heartbeat = DateTimeField(default=datetime.utcnow)
    
    # When the daemon was started.
    started = DateTimeField(default=datetime.utcnow)
    
    # When the daemon was ended.
    ended = DateTimeField(null=True)
    
    # The queue this daemon draws task instances from.
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey('queue_type', 'queue_id')
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        self.flag = Event()
        self.processes = {}
    
    def update_request(self):
        """Updates the request field from the database.
        
        There doesn't appear to be an easy way to have Django refresh an
        object from the database, so this method just updates the status.
        
        """
        self.request = Daemon.objects.get(id=self.id).request
        return self.request
    
    def heart(self):
        while True:
            self.heartbeat = datetime.utcnow()
            self.save()
            time.sleep(5)
    
    def start(self):
        """Starts the daemon.  Mostly just a wrapper for run()."""
        if not hasattr(self, 'id'):
            self.save()
        if not hasattr(self, 'log'):
            self.log = make_log(self.log_path)
        self.log.debug("Starting %s..." % self)
        heart = Thread(target=self.heart)
        heart.daemon = True
        heart.start()
        try:
            self.run()
        except Exception:
            self.status = Status.ERROR
            self.log.error('Daemon suffered an internal error!', trace=True)
            self.save()
        self.log.info("%s has ended gracefully." % self)
    
    def run(self):
        """Core Daemon function.  Returns the exit status of the Daemon."""
        # Prechecks:
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        if self.status != Status.CREATED:
            self.log.error("Can't start a Daemon that's already been run.")
            return Status.ERROR
        for signum in HANDLED_SIGNALS:
            signal.signal(signum, self.signal_handler)
        self.status = Status.RUNNING
        self.save()
        self.log.info("%s is now running on host %s." % (self, self.host))
        # Main loop.
        self.update_request()
        last_request_update = datetime.utcnow()
        minimum_delay = timedelta(seconds=1)
        while not Status.is_final(self.status):
            if datetime.utcnow() - last_request_update > minimum_delay:
                self.update_request()
                last_request_update = datetime.utcnow()
            if self.request:
                self.handle_request()
            elif self.status == Status.RUNNING:
                if len(self.processes) < CONCURRENCY_LIMIT:
                    instance = self.queue.pop(timeout=5)
                    if instance:
                        self.start_instance(instance)
                else:
                    self.flag.clear()
                    self.flag.wait(5)
            elif self.status == Status.STOPPING and len(self.processes) == 0:
                self.set_status(Status.ENDED)
                self.save()
            # Cleanup before iterating.
            for pid, p in self.processes.iteritems():
                if not p.is_alive():
                    self.log.info("Instance '%s' ended with status %s." %
                        (p.instance, Status.decipher(p.instance.status)))
                    del self.processes[pid]
    
    def start_instance(self, instance):
        """Starts a given instance in a new process."""
        instance.daemon = self
        self.log.info("Starting instance '%s'..." % instance)
        p = Process(target=self.execute, args=[instance.run])
        p.start()
        p.instance = instance
        self.processes[p.pid] = p
    
    def execute(self, func):
        """Calls a function, then sets the flag after its execution."""
        try:
            func()
        finally:
            # del self.processes[os.getpid()]
            self.flag.set()
    
    def handle_request(self):
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
            for p in self.processes.values():
                p.terminate()
            self.set_status(Status.KILLED)
        
        self.request = None
        self.save()
    
    def signal_handler(self, signum, frame):
        sig_name = None
        # A reverse lookup to find the signal name.
        for attr in dir(signal):
            if attr.startswith('SIG') and getattr(signal, attr) == signum:
                sig_name = attr
                break
        self.log.info("Signal '%s' received!" % sig_name)
        if signum == signal.SIGINT:
            self.request = Daemon.REQUEST_STOP
        else:
            self.request = Daemon.REQUEST_KILL
        self.flag.set()
        self.save()
    
    def set_status(self, status):
        self.log.info("Changing state from %s to %s." %
            tuple(Status.decipher(self.status, status)))
        self.status = status
    
    def _get_log_path(self):
        return 'daemons/daemon-%s' % self.id
    log_path = property(_get_log_path)
    
    def __unicode__(self):
        return u"Daemon #%s" % self.id
    
    __repr__ = __unicode__
    
