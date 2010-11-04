
import os
import time

from django.db.models import (Model, query,
    BooleanField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.models.task import Task, AbstractInstance, Instance
from norc.norc_utils.django_extras import queryset_exists, QuerySetManager

class Job(Task):
    """A Task composed of running several other Tasks."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_job'
    
    def start(self, instance):
        """Modified to give run() the instance object."""
        return self.run(instance)
    
    def run(self, instance):
        """Enqueue instances for all nodes that don't have dependencies."""
        for node in self.nodes.all():
            node_instance = JobNodeInstance.objects.create(
                node=node,
                job_instance=instance)
            if node_instance.can_run():
                instance.schedule.queue.push(node_instance)
        while True:
            complete = True
            for ni in instance.nodis.all():
                if not Status.is_final(ni.status):
                    complete = False
                elif Status.is_failure(ni.status):
                    return False
            if complete and instance.nodis.count() == self.nodes.count():
                return True
            time.sleep(1)
    

class JobNode(Model):
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_jobnode'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    job = ForeignKey(Job, related_name='nodes')
    
    def __unicode__(self):
        return u"JobNode #%s in %s for %s" % (self.id, self.job, self.task)
    
    __repr__ = __unicode__
    

class JobNodeInstance(AbstractInstance):
    """An instance of a node executed within a job."""
    
    class Meta:
        app_label = 'core'
        db_table = 'norc_jobnodeinstance'
    
    objects = QuerySetManager()
    
    QuerySet = Instance.QuerySet
    
    # The node that spawned this instance.
    node = ForeignKey(JobNode, related_name='nis') # nis -> NodeInstances
    
    # The JobInstance that this NodeInstance belongs to.
    job_instance = ForeignKey(Instance, related_name='nodis')
    
    def start(self):
        try:
            AbstractInstance.start(self)
        finally:
            ji = self.job_instance
            if not Status.is_failure(self.status):
                for sub_dep in self.node.sub_deps.all():
                    sub_node = sub_dep.child
                    ni = sub_node.nis.get(job_instance=ji)
                    if ni.can_run():
                        self.job_instance.schedule.queue.push(ni)
    
    def run(self):
        self.node.task.run()
    
    @property
    def timeout(self):
        return self.node.task.timeout
    
    @property
    def source(self):
        return self.node.job
    
    @property
    def log_path(self):
        return os.path.join(self.job_instance.log_path + '-nodes',
            'node-%s' % self.id)
    
    @property
    def task(self):
        return self.node.task
    
    def can_run(self):
        """Whether dependencies are met for this instance to run."""
        for dep in self.node.super_deps.all():
            ni = dep.parent.nis.get(job_instance=self.job_instance)
            if ni.status != Status.SUCCESS:
                return False
        return True
    
    def __unicode__(self):
        return 'NodeInstance for %s' % self.node.task

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    class Meta:
        app_label = 'core'
        db_table = 'norc_dependency'
    
    parent = ForeignKey(JobNode, related_name='sub_deps')
    child = ForeignKey(JobNode, related_name='super_deps')
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        assert self.parent.job == self.child.job
    
    def __unicode__(self):
        return u"Dependency: '%s ->- %s'" % (self.parent, self.child)
    
    __repr__ = __unicode__
    
