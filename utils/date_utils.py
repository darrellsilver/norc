
import re, datetime

def parse_date_relative(back, date=None):
    if date == None:
        date = datetime.datetime.utcnow()
    parser = re.compile("([mp])([0-9]*)(d|h|min)")
    parsed = parser.findall(back)
    if not len(parsed) == 1:
        raise TypeError("Could not parse '%s'" % (back))
    (sign, num, units) = parsed[0]
    if sign == 'm':
        sign = -1
    else:
        sign = 1
    num = int(num)
    if units == 'd':
        td = datetime.timedelta(days=sign*num)
    elif units == 'h':
        td = datetime.timedelta(hours=sign*num)
    elif units == 'min':
        td = datetime.timedelta(minutes=sign*num)
    
    return date + td