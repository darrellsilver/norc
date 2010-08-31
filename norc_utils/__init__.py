
"""Some very generic utility functions."""

import time

def wait_until(cond, timeout=60, freq=0.5):
    """Tests the condition repeatedly until <timeout> seconds have passed."""
    seconds = 0
    while not cond():
        if seconds >= timeout:
            raise Exception('Timed out after %s seconds.' % seconds)
        time.sleep(freq)
        seconds += freq

def search(ls, cond):
    for e in ls:
        if cond(e):
            return e
    return None
