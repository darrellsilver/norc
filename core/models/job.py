
import os
import time

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
    
    # @property
    # def start_nodes(self):
    #     # return filter(lambda n: not queryset_exists(n.super_deps.all()),
    #     #     self.nodes.all()
    #     start_nodes = []
    #     for n in self.nodes.all():
    #         if not queryset_exists(n.super_deps.all()):
    #             start_nodes.append(n)
    #     return start_nodes
    
    def start(self, instance):
        """Modified to give run() the instance object."""
        return self.run(instance)
    
    def run(self, instance):
        """Enqueue instances for all nodes that don't have dependencies."""
        for node in self.nodes.all():
            node_instance = NodeInstance.objects.create(
                node=node,
                job_instance=instance)
            if node_instance.can_run():
                instance.schedule.queue.push(node_instance)
        while True:
            # print [(ni.status, ni.node) for ni in instance.nodis.all()]
            complete = True
            for ni in instance.nodis.all():
                if not Status.is_final(ni.status):
                    complete = False
                elif Status.is_failure(ni.status):
                    return False
            if complete and instance.nodis.count() == self.nodes.count():
                return True
            time.sleep(1)
    

class Node(Model):
    
    class Meta:
        app_label = 'core'
    
    task_type = ForeignKey(ContentType)
    task_id = PositiveIntegerField()
    task = GenericForeignKey('task_type', 'task_id')
    job = ForeignKey(Job, related_name='nodes')
    # optional = BooleanField(default=False)
    
    # def start(self, instance):
    #     instance.start()
    #     ji = instance.job_instance
    #     if not Status.is_failure(instance.status):
    #         for sub_node in self.sub_deps.all():
    #             for deps in sub_node.super_deps.all():
    #                 queryset_exists(NodeInstance.objects.get(node=n, job_instance=instance.job_instance))
    #             # check for all deps
    #             ni, created = NodeInstance.objects.get_or_create(
    #                 task=node,
    #                 job_instance=instance.job_instance,
    #             )
    #             if created:
    #                 instance.job_instance.schedule.queue.push(ni)
    
    def __unicode__(self):
        return u"Node #%s in %s for %s" % (self.id, self.job, self.task)
    
    __repr__ = __unicode__
    

class NodeInstance(BaseInstance):
    """An instance of a node executed within a job."""
    
    # The node that spawned this instance.
    node = ForeignKey('Node', related_name='nis') # nis -> NodeInstances
    
    # The JobInstance that this NodeInstance belongs to.
    job_instance = ForeignKey(Instance, related_name='nodis')
    
    def start(self):
        # print "starting %s" % self
        BaseInstance.start(self)
        ji = self.job_instance
        if not Status.is_failure(self.status):
            for sub_dep in self.node.sub_deps.all():
                sub_node = sub_dep.child
                ni = sub_node.nis.get(job_instance=ji)
                if ni.can_run():
                    # print "%s pushing %s" % (self, ni)
                    self.job_instance.schedule.queue.push(ni)
    
    def run(self):
        self.node.task.run()
    
    @property
    def timeout(self):
        return self.node.task.timeout
    
    @property
    def log_path(self):
        return os.path.join(self.job_instance.log_path + '-nodes',
            'node-%s' % self.id)
    
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
    
    parent = ForeignKey(Node, related_name='sub_deps')
    child = ForeignKey(Node, related_name='super_deps')
    
    def __init__(self, *args, **kwargs):
        Model.__init__(self, *args, **kwargs)
        assert self.parent.job == self.child.job
    
    def __unicode__(self):
        return u"Dependency: '%s ->- %s'" % (self.parent, self.child)
    
    __repr__ = __unicode__
    
