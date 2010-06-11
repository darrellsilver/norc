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


"""All data classes related to handling resources."""

import datetime

from django.db import models
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType

from norc.utils import django_extras


class Resource(models.Model):
    """A resource represents something of finite availability to Tasks.
    
    Naturally, a task will be run only if all resources necessary to
    run it are available in sufficient quantity.  Resources define total
    units of availability of the resource (units_in_existence) and a task
    demands a specific amount of these units to be available at runtime.
    
    Tasks are run within Regions, which are islands of resource availability.
    
    """
    
    class Meta:
        db_table = 'norc_resource'
    
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
        db_table = 'norc_resourceregion'
    
    name = models.CharField(max_length=128, unique=True)
    date_added = models.DateTimeField(default=datetime.datetime.utcnow)
    
    def get_name(self):
        return self.name
    
    def __unicode__(self):
        return self.get_name()
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class ResourceReservation(models.Model):
    """A reservation of a Resource in a given ResourceRegion."""
    
    class Meta:
        db_table = 'norc_resourcereservation'
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
            resource_id = trr.get_resource().id
            rrr = RegionResourceRelationship.get(region, trr.get_resource())
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
                            """ % ('norc_resourcereservation', region_id, resource_id))
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
                                            , resource=trr.get_resource()
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
    
    def get_region(self):
        return self.region
    def get_units_reserved(self):
        return self.units_reserved
    def get_resource(self):
        return self.resource
    def __unicode__(self):
        return "region:'%s': '%s' reserves %s" % (self.get_region(), self.get_resource(), self.get_units_reserved())
    def __str__(self):
        return str(self.__unicode__())
    __repr__ = __str__
    

class TaskResourceRelationship(models.Model):
    """Defines how much of a Resource a Task demands in order to run."""
    
    class Meta:
        db_table = 'norc_taskresourcerelationship'
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
    
    def get_resource(self):
        return self.resource
    
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
            % (self._task_content_type.model, self._task_object_id, self.units_demanded, self.get_resource())
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

class RegionResourceRelationship(models.Model):
    """Defines the availability of resources in a given region"""
    
    class Meta:
        db_table = 'norc_regionresourcerelationship'
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
    
    def get_region(self):
        return self.region
    
    def get_resource(self):
        return self.resource
    
    def get_units_in_existence(self):
        return self.units_in_existence
    
    def __unicode__(self):
        return u"%s provides %s %s" % (self.get_region(), self.get_units_in_existence(), self.get_resource())
    
    def __str__(self):
        return str(self.__unicode__())
    
    __repr__ = __str__
    

