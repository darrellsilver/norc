
"""General logging utilities."""

import sys
import datetime
import traceback

from norc.settings import LOGGING_DEBUG

def timestamp():
    return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')

class Log(object):
    """Abstract class for creating a text log."""
    
    INFO = ' INFO'
    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    
    @staticmethod
    def format(msg, prefix):
        return '[%s] %s: %s\n' % (timestamp(), prefix, msg)
    
    def __init__(self, debug=None):
        self.debug = debug if debug != None else LOGGING_DEBUG
    
    def info(self, msg):
        raise NotImplementedError
    
    def error(self, msg, e):
        raise NotImplementedError
    
    def debug(self, msg):
        raise NotImplementedError
    

class FileLog(Log):
    """Implementation of Log that sends logs to a file."""
    
    def __init__(self, out=None, err=None, buffer=False, debug=None):
        Log.__init__(self, debug)
        self.out = open(out, 'a') if out else sys.stdout
        if not err and out:
            self.err = self.out
        else:
            self.err = open(err, 'a') if err else sys.stderr
        self.buffer = buffer
    
    def write(self, stream, msg):
        stream.write(msg)
        if not self.buffer:
            stream.flush()
    
    def info(self, msg):
        self.write(self.out, Log.format(msg, Log.INFO))
    
    def error(self, msg, e=None, st=False):
        self.write(self.err, Log.format(msg, Log.ERROR))
        if e and st:
            pass #print stacktrace somehow
    
    def debug(self, msg):
        if self.debug:
            self.write(self.out, Log.format(msg, Log.DEBUG))
    
