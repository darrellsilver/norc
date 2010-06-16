#
# Copyright (c) 2009, Perpetually.com, LLC.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Perpetually.com, LLC. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#


"""All models related to tasks."""

import sys, os
import datetime
import random
import subprocess

from django.db import models
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)
from django.contrib.contenttypes.models import ContentType

from norc import settings
from jobs import *

class Task(models.Model):
    """Abstract class representing one task."""
    
    STATUS_ACTIVE = 'ACTIVE'
    # If a task is ephemeral after it runs it 'expires',
    # which is effectively the same as deleting it.
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_DELETED = 'DELETED'
    
    ALL_STATUSES = (STATUS_ACTIVE, STATUS_EXPIRED, STATUS_DELETED)
    
    TASK_TYPE_PERSISTENT = 'PERSISTENT'  # Runs exactly once per Iteration.
    TASK_TYPE_EPHEMERAL = 'EPHEMERAL'    # Runs exactly once.
    # TASK_TYPE_SCHEDULED is ONLY valid for SchedulableTask subclasses.
    # However, django doesn't currently allow subclasses to override fields, 
    # so instead of overriding 'task_type', the cleanest alternative is to define it here,
    # which is sloppy because now Task knows something about a subclass.
    # To limit irritation, there is an explicit check during Task.save() that ensures
    # TASK_TYPE_SCHEDULED Tasks are always ScheduledTask subclasses.
    # see bottom of http://docs.djangoproject.com/en/dev/topics/db/models/
    #
    # Note that SchedulableTask's do not have to be of type SCHEDULED.
    # TASK_TYPE_EPHEMERAL for a ScheduledTask makes it equiv of an '@ job' in unix.
    # TASK_TYPE_PERSISTENT for a ScheduledTask makes it equiv of an '@ job' in unix, but for each Iteration.
    # Just in case, this code explicitly handles these three Task types, in case another one is created 
    # later which is not compatible with SchedulableTask
    TASK_TYPE_SCHEDULED = 'SCHEDULED'    # run as often as the schedule dictates as long as the Iteration is running
    
    ALL_TASK_TYPES = (TASK_TYPE_PERSISTENT,
                      TASK_TYPE_EPHEMERAL,
                      TASK_TYPE_SCHEDULED)
    
    class Meta:
        abstract = True
    
    # Values for these are to be given upon instantiation
    # by the implementing classes.
    
    task_type = models.CharField(max_length=16, default=TASK_TYPE_PERSISTENT,
                                 choices=zip(ALL_TASK_TYPES, ALL_TASK_TYPES))
    
    # These are managed by the Task superclass (this class)
    
    # to efficiently change status w/o having to read from db
    current_run_status = None
    
    job = models.ForeignKey('Job')
    
    # To find this Task's parents, look where this Task is the child in the dependency table
    parent_dependencies = GenericRelation('TaskDependency',
        content_type_field='_child_task_content_type',
        object_id_field='_child_task_object_id')
        
    # To find this Task's children, look where this Task is the parent in the dependency table
    #child_dependencies = GenericRelation('TaskDependency'
    #                                        , content_type_field='_parent_task_content_type'
    #                                        , object_id_field='_parent_task_object_id')
    run_statuses = GenericRelation(
        'TaskRunStatus',
        content_type_field='_task_content_type',
        object_id_field='_task_object_id')
    
    resource_relationships = GenericRelation('TaskResourceRelationship'
                                                    , content_type_field='_task_content_type'
                                                    , object_id_field='_task_object_id')
    #TODO could track when tasks when in and out of live/deleted status
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16, default=STATUS_ACTIVE)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
    
    def get_parent_dependencies(self):
        matches = self.parent_dependencies.filter(status=TaskDependency.STATUS_ACTIVE)
        return matches.all()
    
    def parents_are_finished(self, iteration):
        for dep in self.get_parent_dependencies():
            if not dep.is_satisfied(iteration):
                # A parent of this Task hasn't successfully completed
                return False
            if not dep.get_parent().parents_are_finished(iteration):
                # An ancestor of this Task's parent hasn't successfully completed
                return False
        return True
    
    def depends_on(self, task, only_immediate=False):
        """
        True if this Task has given Task as parent or ancestor, otherwise False. 
        Limit to immediate parents if specified.
        """
        for dep in self.get_parent_dependencies():
            if dep.get_parent() == task:
                return True
            if not only_immediate and dep.get_parent().depends_on(task):
                return True
        return False
    
    def add_dependency(self, parent_task, dependency_type):
        TaskDependency.create(parent_task, self, dependency_type)
    
    def add_resource_demand(self, resource_name, units_demanded):
        """
        convenience method to add a resource necessary to run a task
        """
        r = Resource.get(resource_name)
        if r == None:
            raise TypeError("Unknown resource '%s'" % (resource_name))
        trr = TaskResourceRelationship.adjust_or_create(r, self, units_demanded)
        return True
    
    def __try_reserve_resources(self, region):
        """
        Reserve the resources necessary to run this task. 
        Return True if successful, False if not enough resources available.
        """
        reserved = []
        reserved_all = True
        for rr in self.resource_relationships.all():
            if rr.reserve(region):
                reserved.append(rr)
            else:
                # can't reserve one of the resources, rollback
                reserved_all = False
                break
        if not reserved_all:
            # one of the resources isn't available. rollback those already reserved
            for rr in reserved:
                rr.release(region)
        return reserved_all
    
    def __release_resources(self, region):
        for rr in self.resource_relationships.all():
            rr.release(region)
    
    def save(self, *args, **kwargs):
        """
        Add default resource usages that all tasks share.
        overrides default save().
        """
        if not SchedulableTask in self.__class__.__bases__ \
            and self.get_task_type() == SchedulableTask.TASK_TYPE_SCHEDULED:
            raise TypeError("TASK_TYPE_SCHEDULED is only available to ScheduledTask subclasses. See code comments.")
        # TODO is this the best way to check that the object is new?
        is_new = self.id == None
        # we must save this task so that the resources can be added
        result = models.Model.save(self, *args, **kwargs)
        
        if is_new:
            # only add the demand on first save of the task, not every time it's adjusted
            # all tasks take up 1 connection to the database
            self.add_resource_demand('DATABASE_CONNECTION', 1)
        return result
    
    def get_task_type(self):
        return self.task_type
    
    def is_ephemeral(self):
        return self.get_task_type() == Task.TASK_TYPE_EPHEMERAL
    
    def resources_available_to_run(self, region):
        for rr in self.resource_relationships.all():
            if not rr.can_reserve(region):
                return False
        return True
    
    def is_due_to_run(self, iteration, asof):
        """
        A Task can optionally choose to restrict when it is run by overriding this method.
        'asof' is in UTC time.
        By default it always returns True.
        """
        return True
    
    def is_allowed_to_run(self, iteration, asof=None):
        """
        Check that this Task's parents have run and that it's due_to_run()
        """
        if asof == None:
            asof = datetime.datetime.utcnow()
        
        status = self.get_current_run_status(iteration)
        if not status == None and not status.allows_run():
            # no status means no attempt has been made to run it yet
            return False
        return self.is_due_to_run(iteration, asof) and self.parents_are_finished(iteration)
    
    def __set_run_status(self, iteration, status, nds=None):
        assert status in TaskRunStatus.ALL_STATUSES, "Unknown status '%s'" % (status)
        if self.current_run_status == None:
            self.current_run_status = TaskRunStatus(task=self, iteration=iteration, status=status)
        else:
            assert self.current_run_status.get_iteration() == iteration \
                    , "Iteration %s does not match current_run_status iteration %s" \
                        % (iteration, self.current_run_status.get_iteration())
            self.current_run_status.status = status
        if not status == TaskRunStatus.STATUS_RUNNING:
            self.current_run_status.date_ended = datetime.datetime.utcnow()
        if not nds == None:
            self.current_run_status.controlling_daemon = nds
        self.current_run_status.save()
        if self.is_ephemeral():
            # TODO should it only be marked expired when it succeeds??
            self.status = Task.STATUS_EXPIRED
            self.save()
        if self.alert_on_failure() and status in (TaskRunStatus.STATUS_ERROR, TaskRunStatus.STATUS_TIMEDOUT):
            alert_msg = 'Norc Task %s:%s ended with %s!' % (self.get_job().get_name(), self.get_name(), status)
            if settings.NORC_EMAIL_ALERTS:
                send_mail(alert_msg, "d'oh!" \
                    , settings.EMAIL_HOST_USER, settings.NORC_EMAIL_ALERT_TO, fail_silently=False)
            else:
                log.info(alert_msg)
    
    def set_ended_on_error(self, iteration, region):
        self.__set_run_status(iteration, TaskRunStatus.STATUS_ERROR)
        self.__release_resources(region)
    
    def set_ended_on_timeout(self, iteration, region):
        self.__set_run_status(iteration, TaskRunStatus.STATUS_TIMEDOUT)
        self.__release_resources(region)
        
    def get_status(self):# This is the Task status, not the run status
        return self.status
    
    def is_active(self):
        return self.get_status() == Task.STATUS_ACTIVE
    
    def is_expired(self):
        return self.get_status() == Task.STATUS_EXPIRED
    
    def is_deleted(self):
        return self.get_status() == Task.STATUS_DELETED
    
    def set_status(self, status, save=True):
        assert status in Task.ALL_STATUSES, "Unknown status '%s'" % (status)
        self.status = status
        if save:
            self.save()
    
    def get_current_run_status(self, iteration):
        # TODO should this take asof param?? is_allowed_to_run() does
        if not self.current_run_status == None and self.current_run_status.get_iteration() == iteration:
            return self.current_run_status
        self.current_run_status = TaskRunStatus.get_latest(self, iteration)
        return self.current_run_status
    
    def do_run(self, iteration, nds):
        """What's actually called by manager. Don't override!"""
        try:
            try:
                if not self.__try_reserve_resources(nds.region):
                    raise InsufficientResourcesException()
                self.__set_run_status(iteration, TaskRunStatus.STATUS_RUNNING, nds=nds)
                log.info("Running Task '%s'" % (self))
                success = self.run()
                if success:
                    self.__set_run_status(iteration, TaskRunStatus.STATUS_SUCCESS)
                    log.info("Task '%s' succeeded.\n\n" % (self.__unicode__()))
                else:
                    raise Exception("Task returned failure status. See log for details.")
            except InsufficientResourcesException, ire:
                log.info("Task asked to run but did not run b/c of insufficient resources.")
            #except TaskAlreadyRunningException, tare:
            #    log.info("Task asked to while already running.")
            except SystemExit, se:
                # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
                # extend BaseException, specifically so this check isn't necessary. But
                # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
                raise se
            except Exception, e:
                log.error("Task failed!", e)
                log.error("\n\n", noalteration=True)
                self.__set_run_status(iteration, TaskRunStatus.STATUS_ERROR)
            except:
                # if the error thrown doesn't use Exception(...), ie just throws a string
                log.error("Task failed with poorly thrown exception!")
                traceback.print_exc()
                log.error("\n\n", noalteration=True)
                self.__set_run_status(iteration, TaskRunStatus.STATUS_ERROR)
        finally:
            try:
                self.__release_resources(nds.region)
            except:
                pass
    
    def alert_on_failure(self):
        """Whether alert(s) should be issued when this Task fails."""
        
        return True
    
    def get_library_name(self):
        """
        Return the python path for this Task implementation.
        For example, permalink.norc_impl.EnqueuedArchiveRequest
        """
        # TODO I HATE THIS! How can it be derived dynamically??
        raise NotImplementedError
    
    def has_timeout(self):
        raise NotImplementedError
    
    def get_timeout(self):
        """timeout Task after this many seconds"""
        raise NotImplementedError
    
    def run(self):
        """
        Run this task!
        Norc records success/failure, but any more detail than that is left to the internals of the run() implementation.
        """
        raise NotImplementedError
    
    def get_id(self):
        return self.id
    
    def get_job(self):
        return self.job
    
    def get_name(self):
        """A unique name for this Task in Norc; don't override!"""
        # TODO names should be allowed to be defined by the subclass for clarity
        # EnqueuedArchiveRequest.144
        return u"%s.%s" % (self.__class__.__name__, self.get_id())
    
    def get_log_file(self):
        # TODO BIG TODO!! There needs to be an iteration suffix, but can't do that from here! Arg!
        fp = os.path.join(settings.NORC_LOG_DIR, self.get_job().get_name(), self.get_name())
        return fp
    
    def __eq__(self, o):
        if not type(o) == Task:
            return False
        return self.get_id() == o.get_id()
    
    def __ne__(self, o):
        return not self.__eq__(o)
    
    def __unicode__(self):
        return self.get_name()
    
    def __str__(self):
        try:
            return str(self.__unicode__())
        except SystemExit, se:
            # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
            # extend BaseException, specifically so this check isn't necessary. But
            # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
            raise se
        except Exception, e:
            return repr(self.__unicode__())
    
    __repr__ = __str__
    

class TaskDependency(models.Model):
    """A dependency of one Task on another.
    
    For clarity and Freudian significance, dependencies are defined as
    the 'child' Task depends on the 'parent' Task, 
    meaning before the child can run, the parent must have run.
    
    """
    
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_DELETED = 'DELETED'
    
    ALL_STATUSES = (STATUS_ACTIVE, STATUS_DELETED)
    
    DEP_TYPE_STRICT = 'STRICT' # parent must have been successful or skipped before child can run
    DEP_TYPE_FLOW = 'FLOW'     # parent must have been run or skipped, but doesn't have to have been successful before child can run
    
    ALL_DEP_TYPES = (DEP_TYPE_STRICT, DEP_TYPE_FLOW)
    
    class Meta:
        db_table = 'norc_taskdependency'
        unique_together = (('_parent_task_content_type', '_parent_task_object_id'
                            , '_child_task_content_type', '_child_task_object_id'),)
    
    # I want to use a ManyToManyField for this in the Task superclass
    # but the relation is generic, so gotta use a seperate TaskDependency class.
    # @see http://www.djangoproject.com/documentation/models/generic_relations/ and
    # @see http://docs.djangoproject.com/en/dev/topics/db/models/#intermediary-manytomany
    _parent_task_content_type = models.ForeignKey(ContentType, related_name="_parent_task_content_type_set")
    _parent_task_object_id = models.PositiveIntegerField()
    parent_task = GenericForeignKey('_parent_task_content_type', '_parent_task_object_id')
    
    _child_task_content_type = models.ForeignKey(ContentType, related_name="_child_task_content_type_set")
    _child_task_object_id = models.PositiveIntegerField()
    child_task = GenericForeignKey('_child_task_content_type', '_child_task_object_id')
    
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    dependency_type = models.CharField(choices=(zip(ALL_DEP_TYPES, ALL_DEP_TYPES)), max_length=16)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    @staticmethod
    def create(parent_task, child_task, dependency_type):
        assert parent_task.get_job() == child_task.get_job(), "parent's Job (%s) doesn't match child's Job (%s)" \
                % (parent_task.get_job(), child_task.get_job())
        assert dependency_type in TaskDependency.ALL_DEP_TYPES, "unknown dependency_type '%s'" % (dependency_type)
        assert parent_task.is_active(), "parent Task must be active"
        assert child_task.is_active(), "child Task must be active"
        assert not child_task.depends_on(parent_task, only_immediate=True) \
                , "Dependency parent:'%s' -> child:'%s' already exists" % (parent_task, child_task)
        assert not parent_task.depends_on(child_task), "Attempting to creat circular dependency. \
                Given parent:'%s' already depends on child:'%s'" % (parent_task, child_task)
        
        td = TaskDependency(parent_task=parent_task, child_task=child_task
                            , status=TaskDependency.STATUS_ACTIVE
                            , dependency_type=dependency_type)
        td.save()
        return td
    
    def get_parent(self):
        return self.parent_task
    def get_child(self):
        return self.child_task
    def get_status(self):
        return self.status
    def is_active(self):
        return self.get_status() == TaskDependency.STATUS_ACTIVE
    def is_deleted(self):
        return self.get_status() == TaskDependency.STATUS_DELETED
    def get_dependency_type(self):
        return self.dependency_type
    
    def is_satisfied(self, iteration):
        """
        For the given iteration, has the parent Task 
        completed in a way that allows the child to run
        """
        if self.get_parent().is_expired():
            # Don't bother with expensive status lookup; it's expired!
            return True
        if self.get_parent().is_deleted():
            # This dependency links a task which cannot be satisfied b/c the parent is deleted
            raise NorcInvalidStateException("Parent %s of %s is deleted. Tree for Job '%s' is broken!" \
                % (self.get_child(), self.get_parent(), self.get_child().get_job()))
        # This check is valuable, but prevents us from checking if task is expired before 
        # performing EXPENSIVE task status lookup
        #if task_status == None and self.get_parent().is_expired():
        #    # Task isn't allowed to expire w/o running.
        #    raise NorcInvalidStateException("Parent '%s' of '%s' is expired w/ no status. Tree for Job '%s' broken!" \
        #        % (self.get_child().get_name(), self.get_parent().get_name(), self.get_child().get_job()))
        
        task_status = self.get_parent().get_current_run_status(iteration)
        if task_status == None:
            # Parent hasn't run yet
            return False
        if self.get_dependency_type() == TaskDependency.DEP_TYPE_STRICT \
            and task_status.get_status() in (TaskRunStatus.STATUS_SKIPPED
                                            , TaskRunStatus.STATUS_CONTINUE
                                            , TaskRunStatus.STATUS_SUCCESS):
            # Parent has succesfully completed
            return True
        if self.get_dependency_type() == TaskDependency.DEP_TYPE_FLOW \
            and task_status.get_status() in (TaskRunStatus.STATUS_SKIPPED
                                            , TaskRunStatus.STATUS_CONTINUE
                                            , TaskRunStatus.STATUS_SUCCESS
                                            , TaskRunStatus.STATUS_TIMEDOUT
                                            , TaskRunStatus.STATUS_ERROR):
            # Parent has finished, regardless of status
            return True
        return False
    
    def __unicode__(self):
        try:
            return u"'%s' -> '%s'" % (self.get_child(), self.get_parent())
        except SystemExit, se:
            # in python 2.4, SystemExit extends Exception, this is changed in 2.5 to 
            # extend BaseException, specifically so this check isn't necessary. But
            # we're using 2.4; upon upgrade, this check will be unecessary but ignorable.
            raise se
        except Exception, e:
            return u"%s.%s -> %s.%s" % (self._child_task_content_type.model, self._child_task_object_id
                , self._parent_task_content_type.model, self._parent_task_object_id)
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class TaskRunStatus(models.Model):
    """The status of a Task that has ran or is running"""
    
    STATUS_SKIPPED = 'SKIPPED'     # Task has been skipped; it ran and failed or did not run before being skipped
    STATUS_RUNNING = 'RUNNING'     # Task is running now.. OMG exciting!
    STATUS_ERROR = 'ERROR'         # Task ran but ended in error
    STATUS_TIMEDOUT = 'TIMEDOUT'   # Task timed out while running
    STATUS_CONTINUE = 'CONTINUE'   # Task ran, failed, but children are allowed to run as though it succeeded or children were flow dependencies
    STATUS_RETRY = 'RETRY'         # Task has been asked to be retried
    STATUS_SUCCESS = 'SUCCESS'     # Task ran successfully. Yay!
    
    ALL_STATUSES = (STATUS_SKIPPED, STATUS_RUNNING, STATUS_ERROR,
        STATUS_CONTINUE, STATUS_TIMEDOUT, STATUS_RETRY, STATUS_SUCCESS)
    
    STATUS_CATEGORIES = {}
    STATUS_CATEGORIES['running'] = [STATUS_RUNNING]
    STATUS_CATEGORIES['active'] = [STATUS_RUNNING]
    STATUS_CATEGORIES['errored'] = [STATUS_ERROR, STATUS_TIMEDOUT]
    STATUS_CATEGORIES['success'] = [STATUS_SUCCESS, STATUS_CONTINUE]
    STATUS_CATEGORIES['interesting'] = []
    STATUS_CATEGORIES['interesting'].extend(STATUS_CATEGORIES['active'])
    STATUS_CATEGORIES['interesting'].extend(STATUS_CATEGORIES['errored'])
    STATUS_CATEGORIES['all'] = ALL_STATUSES
    
    class Meta:
        db_table = 'norc_taskrunstatus'
    
    # @see http://docs.djangoproject.com/en/dev/ref/contrib/contenttypes/
    # or the lesser @see http://www.djangoproject.com/documentation/models/generic_relations/
    _task_content_type = models.ForeignKey(ContentType)
    _task_object_id = models.PositiveIntegerField()
    task = GenericForeignKey('_task_content_type', '_task_object_id')
    iteration = models.ForeignKey(Iteration)
    
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    # rename to nds
    controlling_daemon = models.ForeignKey('NorcDaemonStatus', blank=True, null=True)
    
    @staticmethod
    def get_all_statuses(task, iteration):
        """
        Return all run statuses as list for this Task/Iteration pair or None if it hasn't been run
        """
        try:
            # why can't django's GenericForeignKey handle this mapping for me??
            task_content_type = ContentType.objects.get_for_model(task)
            matches = TaskRunStatus.objects.filter(_task_content_type=task_content_type.id)
            matches = matches.filter(_task_object_id=task.id)
            matches = matches.filter(iteration=iteration)
            return matches.all()
        except TaskRunStatus.DoesNotExist, dne:
            return None
        
    @staticmethod
    def get_latest(task, iteration):
        """
        Return the latest (ie most recent by date_started) run status 
        for this Task/Iteration pair or None if it hasn't been run
        """
        try:
            trs = TaskRunStatus.get_all_statuses(task, iteration)
            if trs == None:
                return None
            latest = trs.latest('date_started')
            return latest
        except TaskRunStatus.DoesNotExist, dne:
            return None
    
    def save(self):
        """Save this TaskRunStatus. Ensure that only one of these is running at a time."""
        models.Model.save(self)
        
        # need to ensure that Tasks don't get run by multiple daemons at once
        # so this is a race condition check that's cheaper than locking the table but
        # will occasionally (and temporarily) result in the Task not getting run at all
        # when it should be run by 1.
        # TODO This can't be here and was removed 20090513.
        #      Daemon collisions need to be managed elsewhere, like in manage.py 
        #if self.get_status() == TaskRunStatus.STATUS_RUNNING:
        #    task_content_type = ContentType.objects.get_for_model(self.get_task())
        #    matches = TaskRunStatus.objects.filter(_task_content_type=task_content_type.id)
        #    matches = matches.filter(_task_object_id=self.get_task().get_id())
        #    matches = matches.filter(status=TaskRunStatus.STATUS_RUNNING)
        #    matches = matches.filter(iteration=self.get_iteration())
        #    if matches.count() > 1:
        #        self.delete()
        #        raise TaskAlreadyRunningException("Task already running. Stopped.")
    
    def get_id(self):
        return self.id
    def get_task(self):
        return self.task
    def get_iteration(self):
        return self.iteration
    def get_status(self):
        return self.status
    def get_controlling_daemon(self):
        return self.controlling_daemon
    def allows_run(self):
        return self.get_status() in (TaskRunStatus.STATUS_RETRY)
    def was_successful(self):
        return self.get_status() == TaskRunStatus.STATUS_SUCCESS
    def is_finished(self):
        return self.get_status() in (TaskRunStatus.STATUS_SKIPPED
            , TaskRunStatus.STATUS_CONTINUE
            , TaskRunStatus.STATUS_SUCCESS)
    def get_date_started(self):
        return self.date_started
    def get_date_ended(self):
        return self.date_ended
    
    def __unicode__(self):
        return u"%s: %s.%s %s-%s" % (self.status, self._task_content_type.model
            , self._task_object_id
            , self.date_started, self.date_ended)
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class TaskClassImplementation(models.Model):
    """List of classes that implement the Task interface and can be instantiated (not including abstract subclasses)"""
    
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    
    ALL_STATUSES = (STATUS_ACTIVE, STATUS_INACTIVE)
    
    class Meta:
        db_table = 'norc_taskclassimplementation'
    
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=16)
    library_name = models.CharField(max_length=1024)
    class_name = models.CharField(max_length=1024)
    
    @staticmethod
    def get_all():
        matches = TaskClassImplementation.objects.filter(status=TaskClassImplementation.STATUS_ACTIVE)
        return matches.all()
    
    def __unicode__(self):
        return "%s.%s (%s)" % (self.library_name, self.class_name, self.status)
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class RunCommand(Task):
    """Run an arbitrary command line as a Task."""
    
    class Meta:
        db_table = 'norc_generic_runcommand'
    
    cmd = models.CharField(max_length=1024)
    nice = models.IntegerField(default=0)
    timeout = models.PositiveIntegerField()
    
    def get_library_name(self):
        return 'norc.core.models.RunCommand'
    def has_timeout(self):
        return True
    def get_timeout(self):
        return self.timeout
    def get_command(self, interpret_vars=False):
        if interpret_vars:
            return self.interpret_vars(self.cmd)
        else:
            return self.cmd
    
    def interpret_vars(self, cmd):
        """replace specific var names in the given string with their values.
        Provides environment-like settings available only at run time to the a cmd line task."""
        
        cmd_n = cmd
        # Settings
        cmd_n = cmd_n.replace("$NORC_TMP_DIR", settings.NORC_TMP_DIR)
        cmd_n = cmd_n.replace("$DATABASE_NAME", settings.DATABASE_NAME)
        cmd_n = cmd_n.replace("$DATABASE_USER", settings.DATABASE_USER)
        cmd_n = cmd_n.replace("$DATABASE_PASSWORD", settings.DATABASE_PASSWORD)
        cmd_n = cmd_n.replace("$DATABASE_HOST", settings.DATABASE_HOST)
        cmd_n = cmd_n.replace("$DATABASE_PORT", settings.DATABASE_PORT)
        cmd_n = cmd_n.replace("$AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
        cmd_n = cmd_n.replace("$AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)
        
        # Local Dates
        now = datetime.datetime.now()
        cmd_n = cmd_n.replace("$LOCAL_YYYYMMDD.HHMMSS", "%s%02d%02d.%02d%02d%02d" \
            % (now.year, now.month, now.day, now.hour, now.minute, now.second))
        cmd_n = cmd_n.replace("$LOCAL_YYYYMMDD", "%s%02d%02d" % (now.year, now.month, now.day))
        cmd_n = cmd_n.replace("$LOCAL_MM/DD/YYYY", "%02d/%02d/%s" % (now.month, now.day, now.year))
        
        # UTC Dates
        utc = datetime.datetime.now()
        cmd_n = cmd_n.replace("$UTC_YYYYMMDD.HHMMSS", "%s%02d%02d.%02d%02d%02d" \
            % (utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second))
        cmd_n = cmd_n.replace("$UTC_YYYYMMDD", "%s%02d%02d" % (utc.year, utc.month, utc.day))
        cmd_n = cmd_n.replace("$UTC_MM/DD/YYYY", "%02d/%02d/%s" % (utc.month, utc.day, utc.year))
        
        return cmd_n
    
    def run(self):
        cmd = self.get_command(interpret_vars=True)
        if self.nice:
            cmd = "nice -n %s %s" % (self.nice, cmd)
        log.info("Running command '%s'" % (cmd))
        # make sure our output is in order up until this point for clarity
        sys.stdout.flush()
        if not sys.stdout == sys.stderr:
            sys.stderr.flush()
        exit_status = subprocess.call(cmd, shell=True, stdout=sys.stdout, stderr=sys.stderr)
        if exit_status == 0:
            return True
        else:
            return False
    
    def __unicode__(self):
        return u"%s" % self.get_name()
    

class SchedulableTask(Task):
    """Abstract class representing one task that can be scheduled in a crontab-like way"""
        
    SUPPORTED_SIMPLE_SCHEDULES = ['HALFHOURLY', 'HOURLY','DAILY','WEEKLY','MONTHLY']
    
    class Meta:
        abstract = True
    
    # represent the range of time as a string for efficiency in db; parse in and out on either end
    minute = models.CharField(max_length=1024)# 0-59
    hour = models.CharField(max_length=1024)# 0 <= hour < 24
    day_of_month = models.CharField(max_length=1024)# 1 <= day <= number of days in the given month and year
    month = models.CharField(max_length=1024)# 1 <= month <= 12
    day_of_week = models.CharField(max_length=1024)# 0-6 (Monday - Sunday)
    
    # stored actual ranges; parsed out from above char fields
    __minute_r__=None; __hour_r__=None; __day_of_month_r__=None; __month_r__=None; __day_of_week_r__=None
    
    def __init__(self, *args, **kwargs):
        Task.__init__(self, *args, **kwargs)
        self._parse_schedule()
    
    def _parse_schedule(self):
        self.__minute_r__ = SchedulableTask.__str2range__(self.minute, 0, 60)
        self.__hour_r__ = SchedulableTask.__str2range__(self.hour, 0, 24)
        self.__day_of_month_r__ = SchedulableTask.__str2range__(self.day_of_month, 1, 32)
        self.__month_r__ = SchedulableTask.__str2range__(self.month, 1, 13)
        self.__day_of_week_r__ = SchedulableTask.__str2range__(self.day_of_week, 0, 7)
    
    @staticmethod
    def __prettify_rangestr__(r):
        if len(r) <= 5:
            s = u",".join(map(str, r))
        else:
            s = u"%s-%s" % (min(r), max(r))
        return s
    
    @staticmethod
    def __range2str__(r, min_value, max_value):
        if type(r) == str and r == '*':
            r = range(min_value, max_value)
        elif type(r) == int:
            r = [r]
        elif not type(r) == list:
            raise TypeError, "range must be a list of ints"
        elif min(r) < min_value or max(r) >= max_value:
            raise TypeError, "range %s is not within limits %s-%s" % (r, min_value, max_value)
        return ",".join(map(str, r))
    
    @staticmethod
    def __str2range__(s, min_value, max_value):
        if s in (None, '', '*'):
            return range(min_value, max_value)
        return map(int, s.split(","))
    
    @staticmethod
    def parse_schedule_predefined(schedule_name):
        assert schedule_name in SchedulableTask.SUPPORTED_SIMPLE_SCHEDULES, "Unknown schedule name '%s'" % (schedule_name)
        minute = range(0, 60)
        hour = range(0, 24)
        day_of_month = range(1, 32)
        month = range(1, 13)
        day_of_week = range(0, 7)
        
        if schedule_name in ['HALFHOURLY']:
            minute = [0,30]
        elif schedule_name in ['HOURLY','DAILY','WEEKLY','MONTHLY']:
            minute = 0
        if schedule_name in ['DAILY','WEEKLY','MONTHLY']:
            hour = 0
        if schedule_name in ['WEEKLY']:
            day_of_week = random.randint(0,6)
        if schedule_name in ['MONTHLY']:
            # TODO this is a shortcut it should be 31 when that many days in the month
            day_of_month = random.randint(1, 30)
        
        return (minute, hour, day_of_month, month, day_of_week)
    
    def unparse_schedule_predefined(self, pretty_names=False):
        minute = range(0, 60)
        hour = range(0, 24)
        day_of_month = range(1, 32)
        month = range(1, 13)
        day_of_week = range(0, 7)
        
        schedule_name = None
        
        if len(self.__minute_r__) == 2 \
            and self.__hour_r__ == hour \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'every half hour'
            else:
                schedule_name = 'HALFHOURLY'
        elif len(self.__minute_r__) == 1 \
            and self.__hour_r__ == hour \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'every hour'
            else:
                schedule_name = 'HOURLY'
        elif len(self.__minute_r__) == 1 \
            and len(self.__hour_r__) == 1 \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'once a day'
            else:
                schedule_name = 'DAILY'
        elif len(self.__minute_r__) == 1 \
            and len(self.__hour_r__) == 1 \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and len(self.__day_of_week_r__) == 1:
            if pretty_names:
                schedule_name = 'once a week'
            else:
                schedule_name = 'WEEKLY'
        elif len(self.__minute_r__) == 1 \
            and len(self.__hour_r__) == 1 \
            and len(self.__day_of_month_r__) == 1 \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'once a month'
            else:
                schedule_name = 'MONTHLY'
        
        return schedule_name
    
    @staticmethod
    def prep_schedule_parts(minute, hour, day_of_month, month, day_of_week):
        """
        Take components as list and convert them into easily stored string lists
        and perform some sanity checks for valid times.
        EG minute=[1,2,3,4,5] => minute_r="1,2,3,4,5"
        hour='*' => hour_r="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23"
        """
        minute_r = SchedulableTask.__range2str__(minute, 0, 60)
        hour_r = SchedulableTask.__range2str__(hour, 0, 24)
        day_of_month_r = SchedulableTask.__range2str__(day_of_month, 1, 32)# not all months have 31 days, but doesn't matter
        month_r = SchedulableTask.__range2str__(month, 1, 13)
        day_of_week_r = SchedulableTask.__range2str__(day_of_week, 0, 7)
        
        return (minute_r, hour_r, day_of_month_r, month_r, day_of_week_r)
    
    def __closest_prev__(self, i, list, list_is_sorted=True):
        # TODO there's a binary search here that can be done more efficiently than this
        if not list_is_sorted:
            list = sorted(list)
        for element in reversed(list):
            if element <= i:
                return element
        return None
    
    def is_due_to_run_at(self, t):
        if not t.minute in self.__minute_r__:
            # 0 = 0
            return False
        if not t.hour in self.__hour_r__:
            # 0 = 0
            return False
        if not t.day in self.__day_of_month_r__:
            # 1st of Month = 1
            return False
        if not t.month in self.__month_r__:
            # January = 0
            return False
        if not t.weekday() in self.__day_of_week_r__:
            # Monday = 0
            return False
        return True
    def get_prev_due_to_run(self, until):
        """Return the last time this Task is due to run before 'until' datetime"""
        prev_time = until.replace(second=0, microsecond=0)
        minute = self.__closest_prev__(prev_time.minute, self.__minute_r__)
        if minute == None:
            # last run-minute has passed for this hour, roll to last in prev hour
            prev_time = prev_time.replace(minute=self.__minute_r__[-1])
            prev_time -= datetime.timedelta(hours=1)
        else:
            prev_time = prev_time.replace(minute=minute)
        hour = self.__closest_prev__(prev_time.hour, self.__hour_r__)
        if hour == None:
            # last run-hour has passed for this day, roll to last hour & minute on prev day
            prev_time = prev_time.replace(hour=self.__hour_r__[-1], minute=self.__minute_r__[-1])
            prev_time -= datetime.timedelta(days=1)
        else:
            prev_time = prev_time.replace(hour=hour)
        
        # We compromise on efficiency here.  Determining prev for day/month/day-of-week
        # is a lot of moving parts b/c they all have to align together. So
        # since we determine hour & minute intelligently, we brute force back day by day
        # until we find first one that fits.
        while not self.is_due_to_run_at(prev_time):
            prev_time -= datetime.timedelta(days=1)
        return prev_time
    
    def is_due_to_run(self, iteration, asof):
        """
        True if this Task hasn't run at all in this Iteration, or 
        if it's been due to run since it last ran.
        Note that a missed run time will not be 'caught up'.
        There's currently no logic that allows multiple missed runs to catch up.
        """
        # times are in UTC
        if not Task.is_due_to_run(self, iteration, asof):
            return False
        
        status = self.get_current_run_status(iteration)
        if status == None:
            # This Task has never ran; it's guaranteed to be due
            return True
        prev_run_time = self.get_prev_due_to_run(asof)
        # Tasks run once a minute max; must round to minute for comparison
        last_run_time = status.get_date_started().replace(second=0, microsecond=0)
        # has this Task become due between last run and asof?
        return last_run_time < prev_run_time
    
    def is_allowed_to_run(self, iteration, asof=None):
        """
        Overrides Task.is_allowed_to_run() to account for TASK_TYPE_SCHEDULED.
        """
        if asof == None:
            asof = datetime.datetime.utcnow()
        
        if self.get_task_type() == SchedulableTask.TASK_TYPE_SCHEDULED:
            if not self.is_due_to_run(iteration, asof):
                return False
            if not self.parents_are_finished(iteration):
                return False
            status = self.get_current_run_status(iteration)
            if not status == None:
                # SchedulableTasks have 1 minute granularity: Don't run if most recent is from same minute
                started = status.get_date_started().replace(second=0, microsecond=0)
                asof = asof.replace(second=0, microsecond=0)
                if started == asof:
                    # it's due to run, and can, but there already is/was one running in this minute.
                    return False
            return True
        elif self.get_task_type() in (Task.ITER_TYPE_PERSISTENT, Task.ITER_TYPE_EPHEMERAL):
            # delegate to superclass for other task types
            return Task.is_allowed_to_run(self, iteration, asof)
        else:
            raise NorcInvalidStateException("Task type '%s' for '%s' is unsupported for SchedulableTasks." \
                % (self.get_task_type(), self.get_name()))
    
    def get_pretty_schedule(self):
        return u"minute:%s hour:%s day:%s day of month:%s day of week:%s" % (SchedulableTask.__prettify_rangestr__(self.__minute_r__)
            , SchedulableTask.__prettify_rangestr__(self.__hour_r__)
            , SchedulableTask.__prettify_rangestr__(self.__day_of_month_r__)
            , SchedulableTask.__prettify_rangestr__(self.__month_r__)
            , SchedulableTask.__prettify_rangestr__(self.__day_of_week_r__))
    def __unicode__(self):
        return self.get_pretty_schedule()
    

class StartIteration(SchedulableTask):
    """Schedule on which new Norc Iterations are started"""
    
    class Meta:
        db_table = 'norc_startiteration'
    
    target_job = models.ForeignKey(Job, related_name="_ignore_target_job_set")
    target_iteration_type = models.CharField(choices=(zip(Iteration.ALL_ITER_TYPES, Iteration.ALL_ITER_TYPES)), max_length=16)
    allow_simultanious = models.BooleanField()
    
    def get_library_name(self):
        return 'norc.core.models.StartIteration'
    def has_timeout(self):
        return True
    def get_timeout(self):
        return 60
    def run(self):
        if not self.allow_simultanious:
            running = Iteration.get_running_iterations(job=self.target_job)
            if len(running) > 0:
                raise Exception("Cannot start iteration for job '%s' because %s already running!" % (self.target_job, running))
        new_iter = Iteration.create(job=self.target_job, iteration_type=self.target_iteration_type)
        new_iter.set_running()
        return True
    

class NorcInvalidStateException(Exception):
    pass
    

class InsufficientResourcesException(Exception):
    pass
    

