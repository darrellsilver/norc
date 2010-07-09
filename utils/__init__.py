
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

"""Some very generic utility functions."""

import time

def wait_until(cond, timeout=60, freq=1, **kwargs):
    """Tests the condition repeatedly until <timeout> seconds have passed."""
    seconds = 0
    while not cond():
        if seconds >= timeout:
            raise Exception('Timed out after %s seconds.' % seconds)
        time.sleep(freq)
        seconds += freq

def search(ls, cond):
    while len(ls) > 0:
        e = ls.pop(0)
        if cond(e):
            return e
    return None

class SortedList(list):
    
    def __init__(self, ls, key=lambda x: x):
        list.__init__(self)
        self.extend(sorted(ls, key=key))
        self.key = key
        # for e in ls:
            # self.add(e)
    
    def add(self, e):
        kel = self.key(e)
        if len(self) == 0 or ke > self[len(self) - 1]:
            self.append(e)
        elif ke < self[0]:
            self.insert(0, e)
        else:
            self.insert(self.search(ke, 0, len(self)), elem)
        return self
    
    def search(self, ke, i, j):
        # print i, j
        if i == j:
            return i
        p = (i + j) / 2
        # print p
        if ke < self.key(self[p]):
            return self.search(ke, i, p)
        else:
            return self.search(ke, p + 1, j)

if __name__ == '__main__':
    s = SortedList([4,3,6,2])
    print s
    s.add(5)
    print s
    s.add(7)
    print s
    s.add(1)
    print s
