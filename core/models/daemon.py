
import os
from datetime import datetime
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



class Daemon(Model):
    """Daemons are responsible for the running of Tasks."""
    
    VALID_STATUSES = [
        Status.RUNNING,
        Status.PAUSED,
        Status.ENDED,
        Status.ERROR,
        Status.KILLED,
        Status.DELETED,
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
    status = PositiveSmallIntegerField(default=Status.RUNNING,
        choices=[(s, Status.NAMES[s]) for s in VALID_STATUSES])
    
    # A state-change request.
    request = PositiveSmallIntegerField(null=True,
        choices=[(k, v) for k, v in REQUESTS.iteritems()])
    
    # The date and time that the daemon was started.
    started = DateTimeField(default=datetime.utcnow)
    
    # The date and time that the daemon was started.
    ended = DateTimeField(null=True)
    
    # The queue this daemon draws task iterations from.
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey(queue_type, queue_id)
    
    def __init__(self, queue, **kwargs):
        if type(queue) == str:
            queue = Queue.get(queue)
        Model.__init__(self, queue=queue, **kwargs)
        self.save()
        self.log = make_log('daemons/daemon-%s' % self.id)
        self.flag = Event()
        self.processes = set()
        self.accepting = True
    
    def update_request(self):
        """Updates the request field from the database.
        
        There doesn't appear to be an easy way to have Django refresh an
        object from the database, so this method just updates the status.
        
        """
        self.request = Daemon.objects.get(id=self.id).request
    
    def start(self):
        """Starts the daemon.  Mostly just a wrapper for run()."""
        try:
            self.status = self.run()
        except Exception:
            self.status = Status.ERROR
            self.log.error('Daemon suffered an internal error!', trace=True)
        self.save()
    
    def run(self):
        """Core Daemon function.  Returns the exit status of the Daemon."""
        # Preconditions:
        if not hasattr(self, 'id'):
            print "You must save the Daemon before starting it."
            return Status.ERROR
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        if self.status != Status.CREATED:
            self.log.error("Can't start a Daemon that's already been run.")
            return Status.ERROR
        # Main loop.
        self.run = True
        while self.run:
            self.update_request()
            if self.request:
                self.handle_request()
            elif self.accepting and len(self.processes) < CONCURRENCY_LIMIT:
                runnable = self.queue.pop(timeout=5)
                if runnable:
                    self.log.debug("Running: %s" % runnable)
                    p = Process(target=runnable.run)
                    p.start()
                    self.processes.add(p)
            else:
                self.flag.clear()
                self.flag.wait(5)
            # Cleanup before iterating.
            for p in self.processes:
                if not p.is_alive():
                    self.processes.remove(p)
    
    def handle_request(self):
        self.log.info("Request received: %s" %
                      Daemon.REQUESTS[self.request])
        if self.request == Daemon.REQUEST_PAUSE:
            self.status = Status.PAUSED
            self.request = None
            self.accepting = False
        elif self.request == Daemon.REQUEST_UNPAUSE:
            if self.status != Status.PAUSED:
                self.log.info(
                    "Must be paused to unpause; clearing request.")
                self.request = None
            else:
                self.status = Status.RUNNING
                self.request = None
                self.accepting = True
        elif self.request == Daemon.REQUEST_STOP:
            self.accepting = False
            if len(self.processes) == 0:
                self.status = Status.ENDED
                self.request = None
                self.run = False
        elif self.request == Daemon.REQUEST_KILL:
            self.accept = False
            for p in self.processes:
                p.terminate()
            self.status = Status.KILLED
            self.run = False
        self.save()
