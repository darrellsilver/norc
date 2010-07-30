#!/usr/bin/python

import sys
import random, string
import datetime
from norc.sqs.models import *
from norc.core.models import ResourceRegion

def random_string(a, b=None):
    CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890_'
    length = random.randint(a, b) if b else a
    return "".join([random.choice(CHARS) for _ in range(length)])
    
HOSTS = ['.'.join([random_string(3) for _ in range(3)]) for _ in range(20)]

def choice_from_queryset(q):
    return q[random.randint(0, len(q) - 1)]

def print_period():
    sys.stdout.write('.')
    sys.stdout.flush()

def add_sqs_daemon():
    region = choice_from_queryset(ResourceRegion.objects.all())
    global HOSTS
    host = random.choice(HOSTS)
    pid = random.randint(15000, 25000)
    r = random.random()
    if r < 0.9:
        status = NorcDaemonStatus.STATUS_ENDEDGRACEFULLY
    elif r < 0.92:
        status = NorcDaemonStatus.STATUS_ERROR
    elif r < 0.94:
        status = NorcDaemonStatus.STATUS_RUNNING
    else:
        status = random.choice(NorcDaemonStatus.ALL_STATUSES)
    started = datetime.datetime.now() - datetime.timedelta(
        seconds=random.randrange(1209600))
    if status in [NorcDaemonStatus.STATUS_ERROR,
                  NorcDaemonStatus.STATUS_PAUSED,
                  NorcDaemonStatus.STATUS_ENDEDGRACEFULLY,
                  NorcDaemonStatus.STATUS_KILLED,
                  NorcDaemonStatus.STATUS_DELETED]:
        ended = started + datetime.timedelta(
            seconds=random.uniform(120, 60*60*24))
    else:
        ended = None
    daemon = NorcDaemonStatus(region=region, host=host, pid=pid,
        status=status, date_started=started, date_ended=ended)
    daemon.save()
    for _ in range(random.randint(100, 10000)):
        add_sqs_trs(daemon)
    

def add_sqs_trs(daemon):
    task_id = random.randint(1000000, 1000000000)
    r = random.random()
    if r < 0.9:
        status = SQSTaskRunStatus.STATUS_SUCCESS
    elif r < 0.95:
        status = SQSTaskRunStatus.STATUS_ERROR
    else:
        status = random.choice(SQSTaskRunStatus.ALL_STATUSES)
    started = daemon.date_started + datetime.timedelta(
        seconds=random.uniform(1, 60*60*24))
    enqueued = started - datetime.timedelta(
        seconds=random.uniform(30, 60*60*24))
    if status != SQSTaskRunStatus.STATUS_RUNNING:
        ended = started + datetime.timedelta(seconds=random.uniform(0.1, 60))
    else:
        ended = None
    trs = SQSTaskRunStatus(queue_name=daemon.region, task_id=task_id,
        status=status, date_enqueued=enqueued, date_started=started,
        date_ended=ended, controlling_daemon=daemon)
    trs.save()

def populate():
    for _ in range(10):
        add_sqs_daemon()
        print_period()
    print ''

if __name__ == '__main__':
    populate()
