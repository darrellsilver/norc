
from multiprocessing import Process, Pool, TimeoutError

from norc.core.constants import Status
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
    REQUEST_STOP = 2
    REQUEST_KILL = 3
    REQUESTS = {
        Daemon.REQUEST_PAUSE: 'PAUSE',
        Daemon.REQUEST_STOP: 'STOP',
        Daemon.REQUEST_KILL: 'KILL',
    }
    
    class Meta:
        app_label = 'core'
    
    # The host this daemon ran on.
    host = CharField(default=lambda: os.uname()[1], max_length=128)
    # The process ID of the main daemon process.
    pid = IntegerField(default=os.getpid)
    # The status of this daemon.
    status = SmallPositiveIntegerField(default=Status.RUNNING,
        choices=[(s, Status.NAMES[s]) for s in
            Daemon.VALID_STATUSES.iteritems()])
    # A state-change request.
    request = SmallPositiveIntegerField(null=True,
        choices=[(k, v) for k, v in DaemonStatus.STATUSES.iteritems()])
    # The date and time that the daemon was started.
    started = DateTimeField(default=datetime.datetime.utcnow)
    # The date and time that the daemon was started.
    ended = DateTimeField(null=True)
    # The queue this daemon draws task iterations from.
    queue_type = ForeignKey(ContentType)
    queue_id = PositiveIntegerField()
    queue = GenericForeignKey(queue_type, queue_id)
    
    def __init__(self, queue, **kwargs):
        Model.__init__(self, queue=queue, **kwargs)
        self.save()
        self.log = make_log('daemons/daemon-%s' % self.id)
    
    def update_request(self):
        """Updates the request field from the database.
        
        There doesn't appear to be an easy way to have Django refresh an
        object from the database, so this method just updates the status.
        
        """
        self.request = Daemon.objects.get(id=self.id).request
    
    def start(self):
        """Starts the daemon."""
        try:
            self.status = self.run()
        except Exception:
            self.status = Status.ERROR
            self.log.error('Daemon suffered an internal error!', trace=True)
    
    def run(self):
        """Core Daemon function.  Returns the exit status of the Daemon."""
        if not hasattr(self, 'log'):
            self.log.error('You must save the Daemon before starting it.')
            return Status.ERROR
        if settings.DEBUG:
            self.log.info("WARNING, DEBUG is True, which means Django " +
                "will gobble memory as it stores all database queries.")
        # Check status not final here.
        run = True
        while run:
            # Check requests here.
            runnable = queue.pop()
            self.log.debug("")
            Process(target=runnable.start).start()
    
