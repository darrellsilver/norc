
import re, datetime

def parse_since(since_str):
    """A utility function to help parse a since string."""
    if since_str == 'all':
        since_date = None
    else:
        try:
            since_date = parse_date_relative(since_str)
        except TypeError:
            since_date = None
    return since_date

def parse_date_relative(back, date=None):
    if date == None:
        date = datetime.datetime.utcnow()
    parser = re.compile("([0-9]*)(d|h|m)")
    parsed = parser.findall(back)
    if not len(parsed) == 1:
        raise TypeError("Could not parse '%s'" % (back))
    num, units = parsed[0]
    num = -1 * int(num)
    if units == 'd':
        td = datetime.timedelta(days=num)
    elif units == 'h':
        td = datetime.timedelta(hours=num)
    elif units == 'm':
        td = datetime.timedelta(minutes=num)
    
    return date + td
    

def parse_class(class_path):
    """Attempts to import a class at the given path and return it."""
    parts = class_path.split('.')
    module = '.'.join(parts[:-1])
    class_name = parts[-1]
    if len(parts) < 2:
        raise Exception(
            'Invalid path "%s".  Must be of the form "x.Y".' % class_path)
    try:
        imported = __import__(module, globals(), locals(), [class_name])
        return getattr(imported, class_name)
    except ImportError:
        return None
