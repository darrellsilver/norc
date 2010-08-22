
"""Simple function for converting schedules.

The old Norc had SchedulableTask objects, which were tasks with a schedule.
This function takes that, a new-style task and a queue and creates a
CronSchedule out of them.

"""

import random
from norc.core.models import CronSchedule

def convert_schedule(st, task, queue):
    o = st.month if st.__month_r__ != CronSchedule.MONTHS else '*'
    d = st.day_of_month if st.__day_of_month_r__ != CronSchedule.DAYS else '*'
    w = st.day_of_week if st.__day_of_week_r__ != CronSchedule.DAYSOFWEEK else '*'
    h = st.hour if st.__hour_r__ != CronSchedule.HOURS else '*'
    m = st.minute if st.__minute_r__ != CronSchedule.MINUTES else '*'
    s = random.choice(CronSchedule.SECONDS)
    encoding = 'o%sd%sw%sh%sm%ss%s' % (o, d, w, h, m, s)
    return CronSchedule.create(task, queue, encoding)
