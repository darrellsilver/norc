
from django.db.models import (Model,
    BooleanField,
    PositiveIntegerField,
    ForeignKey)
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import (GenericRelation,
                                                 GenericForeignKey)

from norc.core.constants import Status
from norc.core.models.task import Task, BaseInstance, Instance
from norc.norc_utils.django_extras import queryset_exists

class Job(Task):
    """A Task composed of running several other Tasks."""
    
    def _get_start_nodes(self):
        start_nodes = []
        for n in self.nodes:
            if queryset_exists(Dependency.objects.filter(child=n)):
                start_nodes.append(n)
        return start_nodes
    start_nodes = property(_get_start_nodes)
    
    def run(self, instance):
        """Enqueue instances for all nodes that don't have dependencies."""
        for n in self.start_nodes:
            node_iter = SubInstance.objects.create(
                source=n,
                job_iter=instance,
                daemon=instance.daemon,
                schedule=instance.schedule)
            instance.schedule.queue.push(node_iter)
        # wait for all nodes to complete
    

class JobInstance(Instance):
    
    class Meta(Instance.Meta):
        proxy = True
    
    def completion_check(self):
        if self.source.nodes.count() == self.node_iters.filter(
                                            status=Status.SUCCESS).count():
            self.complete()
    
    def complete(self):
        """Called when all of this Job's TaskNodes have run."""
        # Set status to completed/success.
        pass
    

class Node(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    job = ForeignKey(Job, related_name='nodes')
    optional = BooleanField(default=False)
    
    def start(self, instance):
        self.task.start(instance)
        if self.optional or not Status.is_failure(instance.status):
            for node in self.sub_deps:
                # check for all deps
                ni, created = NodeInstance.objects.get_or_create(
                    source=node,
                    job_iter=instance.job_iter,
                )
                if created:
                    instance.job_iter.schedule.queue.push(ni)
        instance.job_iter.completion_check()
    
    def __unicode__(self):
        return u"Node in Job %s for Task %s" % (self.job, self.task)
    
    __repr__ = __unicode__
    

class SubInstance(BaseInstance):
    """An instance of something executed within a job.
    
    Called SubInstance instead of NodeInstance to allow for the possibility
    that the it was dynamically made and therefore not attached to a Node.
    
    """
    # The node that spawned this instance, or null if it was dynamically made.
    node = ForeignKey('Node', null=True)
    
    # The JobInstance that this SubInstance belongs to.
    job_instance = ForeignKey(JobInstance, related_name='subinstances')
    
    def run(self):
        if self.node:
            self.node.start()
    

class Dependency(Model):
    """One task Node's dependency on another.
    
    Represents an edge in the job's dependency digraph.
    
    """
    class Meta:
        app_label = 'core'
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
    def __unicode__(self):
        return u"Dependency of %s on %s" % (self.child, self.parent)
    
    __repr__ = __unicode__
    
