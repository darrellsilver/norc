
"""General logging utilities."""

import os
import sys
import datetime
import traceback

from norc.settings import LOGGING_DEBUG, NORC_LOG_DIR

def make_log(norc_path, **kwargs):
    """Make a log object with a subpath of the norc log directory."""
    path = os.path.join(NORC_LOG_DIR, norc_path)
    try:
        os.makedirs(os.path.dirname(path))
    except (IOError, OSError):
        pass
    return Log(path, **kwargs)

def timestamp():
    """Returns a string timestamp of the current time."""
    now = datetime.datetime.utcnow()
    return now.strftime('%Y/%m/%d %H:%M:%S') + '.%06d' % now.microsecond

class AbstractLog(object):
    """Abstract class for creating a text log."""
    
    INFO = 'INFO'
    ERROR = 'ERROR'
    DEBUG = 'DEBUG'
    
    @staticmethod
    def format(msg, prefix):
        """The format of all log messages."""
        return '[%s] %s: %s\n' % (timestamp(), prefix, msg)
    
    def __init__(self, debug):
        """Initialize a Log object.
        
        If debug is not given, it defaults to the
        LOGGING_DEBUG setting of Norc.
        
        """
        self.debug_on = debug if debug != None else LOGGING_DEBUG
    
    def info(self, msg):
        """Log some informational message."""
        raise NotImplementedError
    
    def error(self, msg, trace):
        """Log about an error that occurred, with optional stack trace."""
        raise NotImplementedError
    
    def debug(self, msg):
        """Message for debugging purposes; only log if debug is true."""
        raise NotImplementedError
    

class Log(AbstractLog):
    """Implementation of Log that sends logs to a file."""
    
    def __init__(self, out=None, err=None, debug=None, echo=False):
        """ Parameters:
        
        out     Path to the file that output should go in.  Defaults
                to sys.stdout if no string is given.
        err     Path to the file that error output should go in.  Defaults
                to out if out is given and sys.stderr if it isn't.
        debug   Boolean; whether debug output should be logged.
        echo    Echoes all logging to stdout if True.
        
        """
        AbstractLog.__init__(self, debug)
        self.out = open(out, 'a') if out else sys.stdout
        if not err and out:
            self.err = self.out
        else:
            self.err = open(err, 'a') if err else sys.stderr
        # Don't echo if already outputting to stdout.
        self.echo = echo and out
    
    def _write(self, stream, msg, format_prefix):
        if format_prefix:
            msg = Log.format(msg, format_prefix)
        stream.write(msg)
        stream.flush()
        if self.echo:
            print >>sys.__stdout__, msg,
    
    def info(self, msg, format=True):
        self._write(self.out, msg, Log.INFO if format else False)
    
    def error(self, msg, trace=False, format=True):
        self._write(self.err, msg, Log.ERROR if format else False)
        if trace:
            self._write(self.err, traceback.format_exc(), False)
    
    def debug(self, msg, format=True):
        if self.debug_on:
            self._write(self.out, msg, Log.DEBUG if format else False)
    
    def start_redirect(self):
        """Redirect all stdout and stderr to this log's files."""
        sys.stdout = self.out
        sys.stderr = self.err
    
    def stop_redirect(self):
        """Restore stdout and stderr to their original values."""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    def close(self):
        if self.out.name != '<stdout>':
            self.out.close()
        if self.err.name != '<stderr>' and self.err.name != '<stdout>':
            self.err.close()

class S3Log(Log):
    """Outputs logs to S3 in addition to a local file."""
    
    # def __init__(self, *args, **kwargs):
        # FileLog.__init__(self, *args, **kwargs)
        
    def close(self):
        if not self.closed:
            FileLog.close(self)
            pass
            self.closed = True
        