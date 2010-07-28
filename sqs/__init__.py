
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

"""Contains some functions useful throughout the sqs module."""

import pickle
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message

from norc.norc_utils import parsing
from norc.web.data_defs import DataDefinition
from norc.settings import AWS_ACCESS_KEY_ID as AWS_ID, \
                          AWS_SECRET_ACCESS_KEY as AWS_KEY

# for st in SQSTASK_IMPLEMENTATIONS:
#     path = st.split('.')
#     name = path.pop()
#     path = '.'.join(path)
#     setattr(pickle, name, __import__(path, fromlist=name))

def push_task(task, queue):
    """Pushes a task into an SQS queue.
    
    task should be an SQSTask object.
    queue can be either a boto queue object or a string with the queue name.
    
    """
    if type(queue) == str:
        queue = SQSConnection(AWS_ID, AWS_KEY).lookup(queue)
    m = Message()
    # m.set_body(pickle.dumps(task))
    m.set_body(pickle.dumps(task.__dict__))
    queue.write(m)

def pop_task(queue):
    """Retrieves an SQSTask from the given SQS queue.
    
    queue can be either a boto queue object or a string with the queue name.
    Returns None if no message is found in the given queue.
    
    """
    # from norc.sqs.push_task import DemoSQSTask
    # globals()['DemoSQSTask'] = DemoSQSTask
    if type(queue) == str:
        queue = SQSConnection(AWS_ID, AWS_KEY).lookup(queue)
    m = queue.read()
    if not m:
        return None
    queue.delete_message(m)
    # return pickle.loads(m.get_body())
    dict_ = pickle.loads(m.get_body())
    path = dict_.pop('LIBRARY_PATH')
    class_ = parsing.parse_class(path)
    task = class_(**dict_)
    return task
