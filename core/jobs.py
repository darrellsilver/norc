#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification, 
# are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright notice, 
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice, 
#       this list of conditions and the following disclaimer in the documentation 
#       and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its 
#       contributors may be used to endorse or promote products derived from 
#       this software without specific prior written permission.
#     * 
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. 
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT 
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR 
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, 
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
#


import datetime

from django.db import models

class Job(models.Model):
    """A collection of Tasks across which dependencies can be defined."""
    
    class Meta:
        db_table = "norc_job"
    
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=512, blank=True, null=True)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    @staticmethod
    def get(name):
        return Job.objects.get(name=name)
    
    def get_tasks(self, include_expired=False):
        """Return all active Tasks in this Job"""
        # That this has to look at all implementations of the Task superclass
        tasks = []
        for tci in TaskClassImplementation.get_all():
            # Wont work if there's a collision across libraries, but that'll be errored by django on model creation
            # when it will demand a related_name for Job FK.  Solution isnt to create a related_name, but to rename lib entirely
            tci_name = "%s_set" % (tci.class_name.lower())
            matches = self.__getattribute__(tci_name)
            matches = matches.exclude(status=Task.STATUS_DELETED)
            if not include_expired:
                matches = matches.exclude(status=Task.STATUS_EXPIRED)
            tasks.extend(matches.all())
        return tasks
        
    def get_name(self):
        return self.name
    def has_description(self):
        return not self.get_description() == None
    def get_description(self):
        return self.description
    
    def __unicode__(self):
        return u"%s" % (self.get_name())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class Iteration(models.Model):
    """One iteration of a Job. A Job can have more than one Iteration simultaniously."""
    
    STATUS_RUNNING = 'RUNNING'       # Iteration is running: run Tasks when possible
    STATUS_PAUSED = 'PAUSED'         # Iteration is paused; don't start any Tasks
    STATUS_DONE = 'DONE'             # Iteration is done; no more Tasks will ever be run
    
    ALL_STATUSES = (STATUS_RUNNING, STATUS_PAUSED, STATUS_DONE)
    
    ITER_TYPE_PERSISTENT = 'PERSISTENT'  # Iteration stays 'RUNNING' until manually set to 'DONE'
    ITER_TYPE_EPHEMERAL = 'EPHEMERAL'    # Iteration automatically 'DONE' as soon as all Tasks in the Job have satisfactory completed
    
    ALL_ITER_TYPES = (ITER_TYPE_PERSISTENT, ITER_TYPE_EPHEMERAL)
    
    class Meta:
        db_table = 'norc_iteration'
    
    job = models.ForeignKey(Job)
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    iteration_type = models.CharField(choices=(zip(ALL_ITER_TYPES, ALL_ITER_TYPES)), max_length=16)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    
    @staticmethod
    def create(job, iteration_type):
        ji = Iteration(job=job, iteration_type=iteration_type, status=Iteration.STATUS_RUNNING)
        ji.save()
        return ji
    @staticmethod
    def get(iteration_id):
        return Iteration.objects.get(id=iteration_id)
    
    @staticmethod
    def get_running_iterations(job=None, iteration_type=None):
        matches = Iteration.objects.filter(status=Iteration.STATUS_RUNNING)
        if not job == None:
            matches = matches.filter(job=job)
        if not iteration_type == None:
            matches = matches.filter(iteration_type=iteration_type)
        return matches.all()
    
    def get_id(self):
        return self.id
    get_id.short_description = 'Iteration #'# for admin interface
    
    def get_job(self):
        return self.job
    def get_date_started(self):
        return self.date_started
    def get_date_ended(self):
        return self.date_ended
    
    def set_status(self, status):
        assert status in Iteration.ALL_STATUSES
        self.status = status
        if status == Iteration.STATUS_DONE:
            log.info("Ending Iteration %s" % (self.__str__()))
            self.date_ended = datetime.datetime.utcnow()
        self.save()
    def set_paused(self):
        self.set_status(Iteration.STATUS_PAUSE)
    def set_done(self):
        self.set_status(Iteration.STATUS_DONE)
    def set_running(self):
        self.set_status(Iteration.STATUS_RUNNING)
    def get_status(self):
        return self.status
    def is_running(self):
        return self.get_status() == Iteration.STATUS_RUNNING
    def is_paused(self):
        return self.get_status() == Iteration.STATUS_PAUSED
    def is_done(self):
        return self.get_status() == Iteration.STATUS_DONE
    
    def get_iteration_type(self):
        return self.iteration_type
    def is_ephemeral(self):
        return self.get_iteration_type() == Iteration.ITER_TYPE_EPHEMERAL
    def is_persistent(self):
        return self.get_iteration_type() == Iteration.ITER_TYPE_PERSISTENT
    
    def __unicode__(self):
        return u"%s_%s" % (self.get_job().get_name(), self.id)
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

