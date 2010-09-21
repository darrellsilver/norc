
"""General logging utilities."""

import os
import sys
import datetime
import traceback

try:
    from boto.s3.connection import S3Connection
    from boto.s3.key import Key
except ImportError:
    pass

from norc.settings import (LOGGING_DEBUG, NORC_LOG_DIR, LOG_BACKUP_SYSTEM,
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME)

def timestamp():
    """Returns a string timestamp of the current time."""
    now = datetime.datetime.utcnow()
    return now.strftime('%Y/%m/%d %H:%M:%S') + '.%06d' % now.microsecond

class LogHook(object):
    """A pseudo file class meant to be set as stdout to intercept writes."""
    
    def __init__(self, log):
        self.log = log
    
    def write(self, string):    
        self.log.write(string, False)
    
    def writelines(seq):
        for s in seq:
            self.write(s)
    
    def flush(self):
        pass
    
    def fileno(self):
        return self.log.file.fileno()
    

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
    
    def __init__(self, log_file, debug=None, echo=False):
        """ Parameters:
        
        path    Path to the file that all output should go in.
        debug   Boolean; whether debug output should be logged.
        echo    Echoes all logging to stdout if True.
        
        """
        AbstractLog.__init__(self, debug)
        if not isinstance(log_file, file):
            if not os.path.isdir(os.path.dirname(log_file)):
                os.makedirs(os.path.dirname(log_file))
            log_file = open(log_file, 'a')
        self.file = log_file
        self.echo = echo
    
    def write(self, msg, format_prefix):
        if format_prefix:
            msg = Log.format(msg, format_prefix)
        self.file.write(msg)
        self.file.flush()
        if self.echo:
            print >>sys.__stdout__, msg,
    
    def info(self, msg, format=True):
        self.write(msg, Log.INFO if format else False)
    
    def error(self, msg, trace=False, format=True):
        self.write(msg, Log.ERROR if format else False)
        if trace:
            self.write(traceback.format_exc(), False)
    
    def debug(self, msg, format=True):
        if self.debug_on:
            self.write(msg, Log.DEBUG if format else False)
    
    def start_redirect(self):
        """Redirect all stdout and stderr to this log's files."""
        sys.stdout = sys.stderr = LogHook(self)
    
    def stop_redirect(self):
        """Restore stdout and stderr to their original values."""
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    def close(self):
        self.file.close()
    

class NorcLog(Log):
    
    def __init__(self, norc_path=None, *args, **kwargs):
        path = os.path.join(NORC_LOG_DIR, norc_path)
        Log.__init__(self, path, *args, **kwargs)
        self.path = path
        self.norc_path = norc_path
    

class S3Log(NorcLog):
    """Outputs logs to S3 in addition to a local file."""
    
    @staticmethod
    def make_s3_key(path):
        c = S3Connection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        b = c.get_bucket(AWS_BUCKET_NAME)
        if not b:
            b = c.create_bucket(AWS_BUCKET_NAME)
        k = Key(b)
        k.key = 'norc_logs/' + path
        return k
    
    def __init__(self, norc_path, *args, **kwargs):
        NorcLog.__init__(self, norc_path, *args, **kwargs)
        try:
            self.key = S3Log.make_s3_key(norc_path)
        except:
            self.error('Could not make S3 key:', trace=True)
    
    def close(self):
        self.file.flush()
        if hasattr(self, 'key'):
            try:
                self.key.set_contents_from_filename(self.path)
            except:
                self.error('Unable to push log file to S3:', trace=True)
        NorcLog.close(self)


BACKUP_LOGS = {
    'AmazonS3': S3Log,
}

def make_log(norc_path, *args, **kwargs):
    """Make a log object with a subpath of the norc log directory."""
    log_class = BACKUP_LOGS.get(LOG_BACKUP_SYSTEM, NorcLog)
    return log_class(norc_path, *args, **kwargs)
