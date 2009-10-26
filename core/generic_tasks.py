
############################################
#
# Generic Task types
#
#
#
#Darrell
#06/10/2009
############################################

import subprocess

from norc.core import models as core

from utils import log
log = log.Log()

#
#
#

"""
class RunCommand(core.Task):
    " " "Set a specific archiving schedule for a given record" " "
    
    class Meta:
        db_table = 'tms_generic_runcommand'
    
    cmd = models.CharField(max_length=1024)
    timeout = models.PositiveIntegerField()
        
    def get_library_name(self):
        return 'norc.core.generic_tasks.RunCommand'
    def has_timeout(self):
        return True
    def get_timeout(self):
        return self.timeout
    def get_command(self):
        return self.cmd
    
    def run(self):
        log.info("Running '%s'" % (self.get_command()))
        exit_status = subprocess.call(self.get_command(), shell=True)
        if exit_status == 0:
            return True:
        else:
            return False
    
    def __unicode__(self):
        return u"%s" % (self.get_command())

"""
#
