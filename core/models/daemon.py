
class Daemon(Model):
    
    STATUSES = {
        1: 'RUNNING',
        2: 'PAUSED',
        
        5: 'ENDED',
        6: 'ERROR',
        7: 'KILLED',
        8: 'DELETED',
    }
    
    REQUESTS = {
        1: 'PAUSE',
        2: 'STOP',
        3: 'KILL',
    }
    
    class Meta:
        app_label = 'core'
    
    host = models.CharField(max_length=124)
    pid = models.IntegerField()
    status = models.CharField(
        choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=64)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(null=True)
    
    def __init__(self, host, **kws):
        defaults = dict(host=host, pid=os.getpid()) #
        Model.__init__(self, **defaults.update(kws))
    