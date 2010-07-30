
"""General logging utilities."""

import os
import sys
import datetime
import traceback

from norc.settings import NORC_LOG_DIR, LOGGING_DEBUG

def make_log(norc_path, debug=None):
    return FileLog(os.path.join(NORC_LOG_DIR, norc_path), debug=debug)

def timestamp():
    return datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S.%f')

class Log(object):
    """Abstract class for creating a text log."""
    
    INFO = 'INFO'
    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    
    @staticmethod
    def format(msg, prefix):
        return '[%s] %s: %s\n' % (timestamp(), prefix, msg)
    
    def __init__(self, debug=None):
        self.debug = debug if debug != None else LOGGING_DEBUG
    
    def info(self, msg):
        raise NotImplementedError
    
    def error(self, msg, trace):
        raise NotImplementedError
    
    def debug(self, msg):
        raise NotImplementedError
    

class FileLog(Log):
    """Implementation of Log that sends logs to a file."""
    
    def __init__(self, out=None, err=None, debug=None):
        Log.__init__(self, debug)
        self.out = open(out, 'a') if out else sys.stdout
        if not err and out:
            self.err = self.out
        else:
            self.err = open(err, 'a') if err else sys.stderr
        # Don't echo if already outputting to stdout.
        self.echo = self.debug and out
    
    def __del__(self):
        if self.out != sys.stdout:
            self.out.close()
        if self.err != sys.stderr:
            self.err.close()
    
    def write(self, stream, msg):
        stream.write(msg)
        stream.flush()
        if self.echo:
            print >>sys.__stdout__, msg
    
    def info(self, msg):
        self.write(self.out, Log.format(msg, Log.INFO))
    
    def error(self, msg, trace=False):
        self.write(self.err, Log.format(msg, Log.ERROR))
        if trace:
            self.write(self.err, traceback.format_exc())
    
    def debug(self, msg):
        if self.debug:
            self.write(self.out, Log.format(msg, Log.DEBUG))
    
    def start_redirect(self):
        sys.stdout = self.out
        sys.stderr = self.err
    
    def end_redirect(self):
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
