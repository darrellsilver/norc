
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
        #exec("from %s import %s" % (module, class_name))
        #return locals()[class_name]
        imported = __import__(module, globals(), locals(), [class_name])
        return getattr(imported, class_name)
    except ImportError:
        return None

# DEPR
# def _class_for_name(name, *args, **kw):
#     try:
#         ns = kw.get('namespace',globals())
#         return ns[name]
#     except KeyError, ke:
#         #raise Exception("Could not find class by name '%s'" % (name))
#         raise ImportError("Could not find class by name '%s'" % (name))
# 
# def _lib_by_name(library_name):
#     try:
#         lib_parts = library_name.split('.')
#         import_base = '.'.join(lib_parts[:-1])
#         to_import = lib_parts[-1]
#         import_str = "from %s import %s" % (import_base, to_import)
#         exec(import_str)
#         return locals()[to_import]
#     except ImportError:
#         return None
# 
# def _get_task_class(path):
#     # get the class for this library
#     task_lib_parts = task_library.split('.')
#     if len(task_lib_parts) < 2:
#         raise Exception("--task_library must be of the form path.to.lib.ClassName")
#     try:
#         task_class_baselib = '.'.join(task_lib_parts[:-1])
#         task_class_name = task_lib_parts[-1]
#         library = _lib_by_name(task_class_baselib)
#         task_class = _class_for_name(task_class_name, namespace=library.__dict__)
#         return task_class
#     except ImportError, ie:
#         raise Exception("Could not find class '%s'" % (task_library))
