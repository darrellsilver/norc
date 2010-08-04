
class DaemonStatus(Model):
    
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
    
    host = CharField(default=lambda: os.uname()[1], max_length=124)
    pid = IntegerField(default=os.getpid)
    status = SmallPositiveIntegerField(
        choices=[(k, v) for k, v in DaemonStatus.STATUSES.iteritems()])
    date_started = DateTimeField(default=datetime.datetime.utcnow)
    date_ended = DateTimeField(null=True)
    