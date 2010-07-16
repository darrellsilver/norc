
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



#############################################
#
# Some utilities used in generating reports
#
#
#Darrell
#05/20/2009
#############################################

import datetime

from utils import log
log = log.Log()


def round_datetime(dt, round_to):
    if round_to == 'DAY':
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if round_to == 'HOUR':
        return dt.replace(minute=0, second=0, microsecond=0)
    if round_to == 'HALFHOUR':
        if dt.minute < 30:
            return dt.replace(minute=0, second=0, microsecond=0)
        else:
            return dt.replace(minute=30, second=0, microsecond=0)
    if round_to == '10MIN':
        return dt.replace(minute=int((dt.minute/10)*10), second=0, microsecond=0)
    raise Exception("Unknown round to unit '%s'" % (round_to))

def round_2_delta(round_to):
    if round_to == 'DAY':
        return datetime.timedelta(days=1)
    if round_to == 'HOUR':
        return datetime.timedelta(hours=1)
    if round_to == 'HALFHOUR':
        return datetime.timedelta(minutes=30)
    if round_to == '10MIN':
        return datetime.timedelta(minutes=10)
    raise Exception("Unknown round to unit '%s'" % (round_to))

def calc_avg(date_deltas):
    total = 0
    for d in date_deltas:
        total += d.seconds
    return float(total) / float(len(date_deltas))

def ensure_hash_depth(h, *keys):
    for key in keys:
        if not h.has_key(key):
            h[key] = {}
        h = h[key]

def ensure_list(h, key, to_append):
    if h.has_key(key):
        h[key].append(to_append)
    else:
        h[key] = [to_append]

def mod_timedelta(td, mod):
    s = td.seconds % mod.seconds
    return datetime.timedelta(seconds=s)

def save_csv(csv, fn):
    log.info("Savin' CSV to '%s'" % (fn))
    fh = open(fn, 'w')
    for line in csv:
        fh.write(','.join(map(str, line)))
        fh.write('\n')
    fh.close()

#
