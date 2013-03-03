"""
$Id$
"""
import fnmatch
import os
import datetime


class DotDict(dict):
  """
  a class to create dictionaries that can be accessed like dict.key
  """
  def __getattr__(self, attr):
    """
    override __getattr__ to use get
    """
    return self.get(attr, DotDict())
  __setattr__ = dict.__setitem__
  __delattr__ = dict.__delitem__
    

def find_files(directory, filematch):
  """
  find files in a directory that match a filter
  """
  matches = []
  for root, _, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, filematch):
      matches.append(os.path.join(root, filename))
        
  return matches

  
def timedeltatostring(stime, etime):
  """
  take two times and return a string of the difference
  in the form ##d:##h:##m:##s
  """
  delay = datetime.timedelta(seconds=abs(etime - stime))
  if (delay.days > 0):
    tstr = str(delay)
    tstr = tstr.replace(" day, ", ":")
    out  = tstr.replace(" days, ", ":")
  else:
    out = "0:" + str(delay)
  outar = out.split(':')
  outar = [(int(float(x))) for x in outar]
  tmsg = []
  days, hours = False, False
  if outar[0] != 0:
    days = True
    tmsg.append('%02dd' % outar[0])
  if outar[1] != 0 or days:
    hours = True
    tmsg.append('%02dh' % outar[1])
  if outar[2] != 0 or days or hours:
    tmsg.append('%02dm' % outar[2])
  tmsg.append('%02ds' % outar[3])
    
  out   = ":".join(tmsg)
  return out

  
def verify_bool(val):
  """
  convert a value to a bool, also converts some string and numbers
  """
  if val == 0 or val == '0':
    return False
  elif val == 1 or val == '1':
    return True
  elif isinstance(val, basestring):
    val = val.lower()
    if val  == 'false' or val == 'no':
      return False
    elif val == 'true' or val == 'yes':
      return True
  
  return bool(val)

  
def verify(val, vtype):
  """
  verify values
  """
  vtab = {}
  vtab[bool] = verify_bool
  
  if vtype in vtab:
    return vtab[vtype](val)
  else:
    return vtype(val)
  
def convert(tinput):
  """
  converts input to ascii
  """  
  if isinstance(tinput, dict):
    return {convert(key): convert(value) for key, value in tinput.iteritems()}
  elif isinstance(tinput, list):
    return [convert(element) for element in tinput]
  elif isinstance(tinput, unicode):
    return tinput.encode('utf-8')
  else:
    return tinput
  
  