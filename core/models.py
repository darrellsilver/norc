
import sys
import os
import datetime
import random
import subprocess
import signal

from django.db import models, connection
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from django.conf import settings
from norc.norc_utils import django_extras, log
log = log.Log()

class Job(models.Model):
    """A collection of Tasks across which dependencies can be defined."""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_job'
    
    name = models.CharField(max_length=128, unique=True)
    description = models.CharField(max_length=512, blank=True, null=True)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
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
        db_table = settings.DB_TABLE_PREFIX + '_iteration'
    
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
            log.info("Ending Iteration %s" % self)
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
    

class Resource(models.Model):
    """A resource represents something of finite availability to Tasks.
    
    Naturally, a task will be run only if all resources necessary to
    run it are available in sufficient quantity.  Resources define total
    units of availability of the resource (units_in_existence) and a task
    demands a specific amount of these units to be available at runtime.
    
    Tasks are run within Regions, which are islands of resource availability.
    
    """
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_resource'
    
    name = models.CharField(max_length=128)
    # maximum units available for reservation regardless of region. If > -1, 
    # this takes precedence over all settings made at the regional level.
    # When = -1 (the default) regional availability is used.
    # There are checks and warnings in place when to help ensure that 
    # the data integrity is ensured.
    # TODO write check on saving RegionResourceRelationship & Resource
    # TODO issue warning when data integrity is broken.
    #global_units_available = models.IntegerField(default=-1)
    #seconds_between_runs = models.PositiveIntegerField()# TODO hmmmm.
    
    @staticmethod
    def get(name):
        try:
            return Resource.objects.get(name=name)
        except Resource.DoesNotExist, dne:
            return None
    @staticmethod
    def create(name):
        r = Resource(name=name)
        r.save()
        return r
    
    def get_name(self):
        return self.name
    
    def get_reservations(self, region):
        existing_rsvps = self.resourcereservation_set.filter(region=region)
        #existing_rsvps = ResourceReservation.objects.filter(region=region)
        #existing_rsvps = existing_rsvps.filter(resource=self)
        return existing_rsvps.all()
    def get_units_reserved(self, region):
        units_reserved = 0
        for rsvp in self.get_reservations(region):
            units_reserved += rsvp.get_units_reserved()
        return units_reserved
    def get_units_available(self, region):
        rrr = RegionResourceRelationship.get(region, self)
        if rrr == None:
            return 0
        return rrr.get_units_in_existence() - self.get_units_reserved(region)
    
    def __unicode__(self):
        return u"%s" % (self.get_name())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class ResourceRegion(models.Model):
    """A ResourceRegion defines an island of resource availability.
    
    Each task is run within a single Region, where resources are finite
    within that region.  A region might naturally be a single computer,
    where the shared resource is CPU usage.
    
    At this time, there is no way to define usage of a resource that spans
    multiple regions.
    
    """
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_resourceregion'
    
    name = models.CharField(max_length=128, unique=True)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def get_name(self):
        return self.name
    
    def __unicode__(self):
        return self.name
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class ResourceReservation(models.Model):
    """A reservation of a Resource in a given ResourceRegion."""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_resourcereservation'
        unique_together = (('region', 'task_resource_relationship'),)
    
    objects = django_extras.LockingManager()
    
    region = models.ForeignKey('ResourceRegion')
    resource = models.ForeignKey('Resource')
    units_reserved = models.PositiveIntegerField()
    # cleaner than referencing task, which must be done indirectly b/c Tasks are abstract
    task_resource_relationship = models.ForeignKey('TaskResourceRelationship')
    date_reserved = models.DateTimeField(default=datetime.datetime.utcnow)
    
    @staticmethod
    def reserve(region, trr):
        """
        Return True if this trr reservation had enough resources to make this rsvp in this region,
        and it was made, False otherwise
        """
        try:
            # for locking to work, all tables queried must be locked.
            # so, mine static data to allow query the ResourceReservation table in isolation
            # (replicates "if resource.get_units_available(region) < trr.get_units_demanded():")
            region_id = region.id
            resource_id = trr.resource.id
            rrr = RegionResourceRelationship.get(region, trr.resource)
            units_in_existence = 0
            if not rrr == None:
                units_in_existence = rrr.get_units_in_existence()
            units_demanded = trr.get_units_demanded()
            if units_in_existence < units_demanded:
                # There's no hope of reserving this.
                return False
            #
            ResourceReservation.objects.lock()
            cursor = connection.cursor()
            cursor.execute("""SELECT sum(`units_reserved`) as units_reserved
                                 FROM `%s` 
                                WHERE `region_id` = %s
                                  AND `resource_id` = %s
                            """ % (settings.DB_TABLE_PREFIX + '_resourcereservation', region_id, resource_id))
            row = cursor.fetchone()
            units_reserved = row[0]
            if units_reserved == None:# TODO How do you do this in the SQL?
                units_reserved = 0
            units_available = units_in_existence - units_reserved
            if units_available < units_demanded:
                # not enough of this resource currently available
                return False
            else:
                (rr, rsvp_made) = ResourceReservation.objects.get_or_create(region=region
                                            , resource=trr.resource
                                            , task_resource_relationship=trr
                                            , defaults={'units_reserved': trr.get_units_demanded()})
                if not rsvp_made:
                    # This Task must be running >1 at a time.
                    rr.units_reserved += trr.get_units_demanded()
                    rr.save()
                return True
        finally:
            ResourceReservation.objects.unlock()
    
    def release(self):
        if self.get_units_reserved() == self.task_resource_relationship.get_units_demanded():
            # Only one Task reserving it
            self.delete()
        else:
            # Multiple instances of this Task reserving it
            self.units_reserved -= self.task_resource_relationship.get_units_demanded()
            self.save()
        return True
    
    def get_units_reserved(self):
        return self.units_reserved
    
    def __unicode__(self):
        return "region:'%s': '%s' reserves %s" % (self.region, self.resource, self.get_units_reserved())
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class TaskResourceRelationship(models.Model):
    """Defines how much of a Resource a Task demands in order to run."""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_taskresourcerelationship'
        unique_together = (('_task_content_type', '_task_object_id', 'resource'),)
    
    _task_content_type = models.ForeignKey(ContentType)
    _task_object_id = models.PositiveIntegerField()
    task = generic.GenericForeignKey('_task_content_type', '_task_object_id')
    resource = models.ForeignKey('Resource')
    units_demanded = models.PositiveIntegerField()
    
    @staticmethod
    def adjust_or_create(resource, task, units_demanded):
        if task.get_id() == None:
            raise Exception("Task '%s' has not been save()d" % (task))
        existing = TaskResourceRelationship.objects.filter(resource=resource)
        task_content_type = ContentType.objects.get_for_model(task)
        existing = existing.filter(_task_content_type=task_content_type.id)
        existing = existing.filter(_task_object_id=task.id)
        if existing.count() == 0:
            trr = TaskResourceRelationship(resource=resource, task=task, units_demanded=units_demanded)
            trr.save()
        elif existing.count() == 1:
            trr = existing.all()[0]
            new_units_demanded = trr.get_units_demanded() + units_demanded
            if new_units_demanded <= 0:
                raise TypeError("Cannot demand (%s) 0 or fewer of a resource" 
                                % (units_demanded))
            else:
                trr.units_demanded = new_units_demanded
                trr.save()
        else:
            raise Exception("More than one (%s) TaskResourceRelationships exists for the same Task ('%s') & Resource ('%s'). Data error!"
                            % (existing.count(), task, resource))
        return trr
    
    def get_units_demanded(self):
        return self.units_demanded
    
    def can_reserve(self, region):
        """
        True if a reservation can CURRENTLY be made.  False otherwise.
        A fully thread safe check is done at reservation time, which not succeed.
        This is for convenience.
        """
        return self.get_units_demanded() <= self.resource.get_units_available(region)
    
    def reserve(self, region):
        """Return True if this resource has been reserved, False otherwise"""
        did_reserve = ResourceReservation.reserve(region, self)
        return did_reserve
    
    def release(self, region):
        rrs = self.resourcereservation_set.filter(region=region)
        if len(rrs) == 0:
            return False
        if len(rrs) == 1:
            return rrs[0].release()
        raise Exception("There are %s reservations for resource '%s' in region '%s'.  \
                        There should be exactly 0 or 1." 
                        % (len(rss), self.resource, region))
    
    def __unicode__(self):
        return u"Task@%s:%s demands %s '%s'" \
            % (self._task_content_type.model, self._task_object_id, self.units_demanded, self.resource)
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class RegionResourceRelationship(models.Model):
    """Defines the availability of resources in a given region"""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_regionresourcerelationship'
        unique_together = (('region','resource'),)
    
    region = models.ForeignKey('ResourceRegion')
    resource = models.ForeignKey('Resource')
    units_in_existence = models.PositiveIntegerField()
    
    @staticmethod
    def create(region, resource, units_in_existence):
        rrr = RegionResourceRelationship(region=region, resource=resource
            , units_in_existence=units_in_existence)
        rrr.save()
    
    @staticmethod
    def get(region, resource):
        try:
            rrr = RegionResourceRelationship.objects.get(region=region, resource=resource)
            return rrr
        except RegionResourceRelationship.DoesNotExist, dne:
            return None
    
    def get_units_in_existence(self):
        return self.units_in_existence
    
    def __unicode__(self):
        return u"%s provides %s %s" % (self.region, self.get_units_in_existence(), self.resource)
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class Task(models.Model):
    """Abstract class representing one task."""
    
    STATUS_ACTIVE = 'ACTIVE'
    # If a task is ephemeral then after it runs it 'expires',
    # which is effectively the same as deleting it.
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_DELETED = 'DELETED'
    
    ALL_STATUSES = (STATUS_ACTIVE, STATUS_EXPIRED, STATUS_DELETED)
    
    TASK_TYPE_PERSISTENT = 'PERSISTENT'  # Runs exactly once per Iteration.
    TASK_TYPE_EPHEMERAL = 'EPHEMERAL'    # Runs exactly once.
    # TASK_TYPE_SCHEDULED is ONLY valid for SchedulableTask subclasses.
    # However, django doesn't currently allow subclasses to override fields,
    # so instead of overriding 'task_type', the cleanest alternative is to
    # define it here, which is sloppy because now Task knows something about a
    # subclass. To limit irritation, there is an explicit check during
    # Task.save() that ensures TASK_TYPE_SCHEDULED Tasks are always
    # ScheduledTask subclasses. see bottom of
    # http://docs.djangoproject.com/en/dev/topics/db/models/
    # 
    #  Note that SchedulableTask's do not have to be of type SCHEDULED.
    # TASK_TYPE_EPHEMERAL for a ScheduledTask makes it equiv of an '@ job' in
    # unix. TASK_TYPE_PERSISTENT for a ScheduledTask makes it equiv of an '@
    # job' in unix, but for each Iteration. Just in case, this code explicitly
    # handles these three Task types, in case another one is created later which
    # is not compatible with SchedulableTask
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
    
    job = models.ForeignKey('Job')
    
    # To find this Task's parents, look where this Task is the child in the dependency table
    parent_dependencies = GenericRelation('TaskDependency',
        content_type_field='_child_task_content_type',
        object_id_field='_child_task_object_id')
        
    # To find this Task's children, look where this Task is the parent in the dependency table
    #child_dependencies = GenericRelation('TaskDependency'
    #                                        , content_type_field='_parent_task_content_type'
    #                                        , object_id_field='_parent_task_object_id')
    run_statuses = GenericRelation('TaskRunStatus',
        content_type_field='_task_content_type',
        object_id_field='_task_object_id')
    
    resource_relationships = GenericRelation('TaskResourceRelationship',
        content_type_field='_task_content_type',
        object_id_field='_task_object_id')
    #TODO could track when tasks when in and out of live/deleted status
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)),
        max_length=16, default=STATUS_ACTIVE)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def __init__(self, *args, **kwargs):
        models.Model.__init__(self, *args, **kwargs)
        self.current_run_status = None
        self._current_iteration = None
        self._current_nds = None
    
    def get_parent_dependencies(self):
        matches = self.parent_dependencies.filter(
            status=TaskDependency.STATUS_ACTIVE)
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
        assert status in TaskRunStatus.ALL_STATUSES, \
            "Unknown status '%s'" % status
        if self.current_run_status == None:
            self.current_run_status = TaskRunStatus(task=self, iteration=iteration, status=status)
        else:
            assert self.current_run_status.get_iteration() == iteration, \
                "Iteration %s doesn't match current_run_status iteration %s" \
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
            alert_msg = 'Norc Task %s:%s ended with %s!' % \
                (self.get_job().get_name(), self.get_name(), status)
            #if settings.NORC_EMAIL_ALERTS:
            #    send_mail(alert_msg, "d'oh!", settings.EMAIL_HOST_USER,
            #              settings.NORC_EMAIL_ALERT_TO, fail_silently=False)
            #else:
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
        if not self.current_run_status == None and \
            self.current_run_status.get_iteration() == iteration:
            return self.current_run_status
        self.current_run_status = TaskRunStatus.get_latest(self, iteration)
        return self.current_run_status
    
    def timeout_handler(self, signum, frame):
        self.set_ended_on_timeout(
            self.current_iteration, self.current_nds.region)
    
    def do_run(self, iteration, nds):
        """What's actually called by manager. Don't override!"""
        self.current_iteration = iteration
        self.current_nds = nds
        if not self.__try_reserve_resources(nds.region):
            raise InsufficientResourcesException()
        self.__set_run_status(iteration, TaskRunStatus.STATUS_RUNNING, nds=nds)
        if self.has_timeout():
            signal.signal(signal.SIGALRM, self.timeout_handler)
            signal.alarm(self.get_timeout())
        log.info("Running Task '%s'" % (self))
        try:
            success = self.run()
            if self.current_run_status.status == \
                TaskRunStatus.STATUS_TIMEDOUT:
                pass
            elif success:
                self.__set_run_status(iteration, TaskRunStatus.STATUS_SUCCESS)
                log.info("Task '%s' succeeded.\n\n" % (self.__unicode__()))
            else:
                raise Exception("Task returned failure status. See log for details.")
        except InsufficientResourcesException, ire:
            log.info("Task asked to run but did not run b/c of insufficient resources.")
        #except TaskAlreadyRunningException, tare:
        #    log.info("Task asked to while already running.")
        except SystemExit, se:
            # in python 2.4, SystemExit extends Exception, this is changed
            # in 2.5 to extend BaseException, specifically so this check 
            # isn't necessary. But we're using 2.4; upon upgrade, this check
            # will be unecessary but ignorable.
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
            if self.has_timeout():
                signal.alarm(0)
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
        For example, permalink.tms_impl.EnqueuedArchiveRequest
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
        db_table = settings.DB_TABLE_PREFIX + '_taskdependency'
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
        db_table = settings.DB_TABLE_PREFIX + '_taskrunstatus'
    
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
        return self.get_status() in (TaskRunStatus.STATUS_SKIPPED,
                                     TaskRunStatus.STATUS_CONTINUE,
                                     TaskRunStatus.STATUS_SUCCESS)
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
        db_table = settings.DB_TABLE_PREFIX + '_taskclassimplementation'
    
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
        db_table = settings.DB_TABLE_PREFIX + '_generic_runcommand'
    
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
        # cmd_n = cmd_n.replace("$AWS_ACCESS_KEY_ID", settings.AWS_ACCESS_KEY_ID)
        # cmd_n = cmd_n.replace("$AWS_SECRET_ACCESS_KEY", settings.AWS_SECRET_ACCESS_KEY)
        
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
        
        if self.__minute_r__ == [0,30] \
            and self.__hour_r__ == hour \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'every half hour'
            else:
                schedule_name = 'HALFHOURLY'
        elif self.__minute_r__ == [0] \
            and self.__hour_r__ == hour \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'every hour'
            else:
                schedule_name = 'HOURLY'
        elif self.__minute_r__ == [0] \
            and self.__hour_r__ == [0] \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and self.__day_of_week_r__ == day_of_week:
            if pretty_names:
                schedule_name = 'once a day'
            else:
                schedule_name = 'DAILY'
        elif self.__minute_r__ == [0] \
            and self.__hour_r__ == [0] \
            and self.__day_of_month_r__ == day_of_month \
            and self.__month_r__ == month \
            and len(self.__day_of_week_r__) == 1:
            if pretty_names:
                schedule_name = 'once a week'
            else:
                schedule_name = 'WEEKLY'
        elif self.__minute_r__ == [0] \
            and self.__hour_r__ == [0] \
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
        return u"minute:%s hour:%s day:%s day of month:%s day of week:%s" % (
            SchedulableTask.__prettify_rangestr__(self.__minute_r__),
            SchedulableTask.__prettify_rangestr__(self.__hour_r__),
            SchedulableTask.__prettify_rangestr__(self.__day_of_month_r__),
            SchedulableTask.__prettify_rangestr__(self.__month_r__),
            SchedulableTask.__prettify_rangestr__(self.__day_of_week_r__))
    def __unicode__(self):
        return self.get_pretty_schedule()
    

class StartIteration(SchedulableTask):
    """Schedule on which new Norc Iterations are started"""
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_startiteration'
    
    target_job = models.ForeignKey(Job, related_name="_ignore_target_job_set")
    target_iteration_type = models.CharField(
        choices=(zip(Iteration.ALL_ITER_TYPES, Iteration.ALL_ITER_TYPES)),
        max_length=16)
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
    

class NorcDaemonStatus(models.Model):
    """Track the statuses of Norc daemons."""
    
    # Daemon is starting.
    STATUS_STARTING = 'STARTING'
    # Daemon itself exited with bad error
    STATUS_ERROR = TaskRunStatus.STATUS_ERROR
    # Daemon is currently running
    STATUS_RUNNING = TaskRunStatus.STATUS_RUNNING
    # Pause has been requested
    STATUS_PAUSEREQUESTED = 'PAUSEREQUESTED'
    # Don't launch any more tasks, just wait.
    STATUS_PAUSED = 'PAUSED'
    # Stop launching tasks; exit gracefully when running tasks are complete.
    STATUS_STOPREQUESTED = 'STOPREQUESTED'
    # The daemon has received a stop request and will exit gracefully.
    STATUS_STOPINPROGRESS = 'BEING_STOPPED'
    # Stop launching tasks; kill already running tasks with error status.
    STATUS_KILLREQUESTED = 'KILLREQUESTED'
    # The daemon has received a kill request and is shutting down.
    STATUS_KILLINPROGRESS = 'BEING_KILLED'
    # Daemon was exited gracefully; no tasks were interrupted.
    STATUS_ENDEDGRACEFULLY = 'ENDED'
    # Daemon was killed; any running tasks were interrupted.
    STATUS_KILLED = 'KILLED'
    # Daemon status has been hidden for convenience.
    STATUS_DELETED = Task.STATUS_DELETED
    
    ALL_STATUSES = (STATUS_STARTING, STATUS_ERROR, STATUS_RUNNING,
        STATUS_PAUSEREQUESTED, STATUS_PAUSED, STATUS_STOPREQUESTED,
        STATUS_KILLREQUESTED, STATUS_KILLINPROGRESS, STATUS_STOPINPROGRESS,
        STATUS_ENDEDGRACEFULLY, STATUS_KILLED, STATUS_DELETED)
    
    class Meta:
        db_table = settings.DB_TABLE_PREFIX + '_daemonstatus'
    
    region = models.ForeignKey('ResourceRegion')
    host = models.CharField(max_length=124)
    pid = models.IntegerField()
    status = models.CharField(choices=(zip(ALL_STATUSES, ALL_STATUSES)), max_length=64)
    date_started = models.DateTimeField(default=datetime.datetime.utcnow)
    date_ended = models.DateTimeField(blank=True, null=True)
    
    def get_daemon_type(self):
        # TODO This is a temporary hack until we can backfill
        # a daemon_type database field.
        tms_c = self.taskrunstatus_set.count()
        if 'norc.sqs' in settings.INSTALLED_APPS:
            sqs_c = self.sqstaskrunstatus_set.count()
        else:
            sqs_c = 0
        if tms_c > 0 and sqs_c == 0:
            return 'NORC'
        elif tms_c == 0 and sqs_c > 0:
            return 'SQS'
        else:
            return 'NORC'
    daemon_type = property(get_daemon_type)
    
    @staticmethod
    def create(region, daemon_type, status=None, pid=None, host=None):
        if status == None:
            status = NorcDaemonStatus.STATUS_STARTING
        if pid == None:
            pid = os.getpid()
        if host == None:
            # or platform.unode(), platform.node(), socket.gethostname() -- which is best???
            host = os.uname()[1]
        
        status = NorcDaemonStatus(
            region=region, pid=pid, host=host, status=status)
        status.save()
        return status
    
    def get_id(self):
        return self.id
    
    def thwart_cache(self):
        """
        Django caches this object, so if someone changes 
        the database directly this object doesn't see that change.
        We must call this hack to return a new instance of this object, 
        reflecting the database's latest state.
        If the record no longer exists in the database, a DoesNotExist error is raised
        Perhaps there's something in this answer about db types and refreshes?
        Also, QuerySet._clone() will reproduce, but this is almost as good.
        http://groups.google.com/group/django-users/browse_thread/thread/e25cec400598c06d
        """
        # TODO how do you do this natively to Django???
        return NorcDaemonStatus.objects.get(id=self.id)
    
    def set_status(self, status):
        assert status in NorcDaemonStatus.ALL_STATUSES, \
            "Unknown status '%s'" % (status)
        self.status = status
        if not status == TaskRunStatus.STATUS_RUNNING:
            self.date_ended = datetime.datetime.utcnow()
        self.save()
    
    def get_status(self):
        return self.status
    
    def is_pause_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_PAUSEREQUESTED
    
    def is_stop_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STOPREQUESTED
    
    def is_kill_requested(self):
        return self.get_status() == NorcDaemonStatus.STATUS_KILLREQUESTED
    
    def is_paused(self):
        return self.get_status() == NorcDaemonStatus.STATUS_PAUSED
    
    def is_being_stopped(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STOPINPROGRESS
    
    def is_being_killed(self):
        return self.get_status() == NorcDaemonStatus.STATUS_KILLINPROGRESS
    
    def is_starting(self):
        return self.get_status() == NorcDaemonStatus.STATUS_STARTING
    
    def is_shutting_down(self):
        return self.is_stop_requested() or self.is_kill_requested()
    
    def is_running(self):
        return self.get_status() == NorcDaemonStatus.STATUS_RUNNING
    
    def is_done(self):
        return self.get_status() in (NorcDaemonStatus.STATUS_ENDEDGRACEFULLY
                                    , NorcDaemonStatus.STATUS_KILLED
                                    , NorcDaemonStatus.STATUS_ERROR
                                    , NorcDaemonStatus.STATUS_DELETED)
    
    def is_done_with_error(self):
        return self.get_status() == NorcDaemonStatus.STATUS_ERROR
    
    def is_deleted(self):
        return self.get_status() == NorcDaemonStatus.STATUS_DELETED
    
    def get_task_statuses(self, status_filter='all', since_date=None):
        """
        return the statuses (not the tasks) for all tasks run(ning) by this daemon
        date_started: limit to statuses with start date since given date, 
                    or all if date_started=None (the default)
        """
        task_statuses = self.taskrunstatus_set.all()
        status_filter = status_filter.lower()
        TRS_CATS = TaskRunStatus.STATUS_CATEGORIES
        #sqs_statuses = self.sqstaskrunstatus_set.filter(controlling_daemon=self)
        if not since_date == None:
            task_statuses = task_statuses.filter(date_started__gte=since_date)
            #sqs_statuses = sqs_statuses.filter(date_started__gte=since_date)
        if status_filter != 'all' and status_filter in TRS_CATS:
            only_statuses = TRS_CATS[status_filter.lower()]
            task_statuses = task_statuses.filter(status__in=only_statuses)
            #filtered.extend(sqs_statuses.filter(status__in=only_statuses))
        return task_statuses
    
    def __unicode__(self):
        base = u"id:%3s host:%s pid:%s" % (self.id, self.host, self.pid)
        if self.is_running():
            return u"running %s started %s" % (base, self.date_started)
        elif self.is_starting():
            return u"starting %s asof %s" % (base, self.date_started)
        elif self.is_shutting_down():
            return u"ending %s" % (base)
        else:
            return u"finished %s ran %s - %s" % (base, self.date_started, self.date_ended)
        
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class NorcInvalidStateException(Exception):
    pass
    

class InsufficientResourcesException(Exception):
    pass
    