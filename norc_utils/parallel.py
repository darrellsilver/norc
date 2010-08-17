
from __future__ import division

import time
from datetime import datetime, timedelta
from threading import Thread, Event, RLock
from heapq import heappop, heappush

class MultiTimer(Thread):
    """A timer implementation that can handle multiple tasks at once."""
    
    def __init__(self):
        Thread.__init__(self)
        self.tasks = [] # SortedList(reverse=True)
        self.cancelled = False
        self.interrupt = Event()
        self.start()
    
    def run(self):
        while not self.cancelled:
            if len(self.tasks) == 0:
                self.interrupt.wait()
                self.interrupt.clear()
            else:
                self.interrupt.wait(self.tasks[0][0] - time.time())
                if not self.interrupt.is_set():
                    func, args, kwargs = heappop(self.tasks)[1:]
                    # self.tasks.pop()
                    # assert item == self.tasks.pop()
                    func(*args, **kwargs)
                else:
                    self.interrupt.clear()
    
    def cancel(self):
        self.cancelled = True
        self.interrupt.set()
    
    def addTask(self, delay, func, args=[], kwargs={}):
        if type(delay) == datetime:
            now = datetime.now()
            delay = delay - now if now < delay else 0
        if type(delay) == timedelta:
            delay = total_secs(delay)
        delay += time.time()
        item = (delay, func, args, kwargs)
        heappush(self.tasks, item)
        # self.tasks.add(item)
        if item == self.tasks[0]: # .peek():
            self.interrupt.set()
    
