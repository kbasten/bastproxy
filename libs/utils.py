"""
$Id$
"""
import fnmatch
import os
import datetime
import math
from libs.color import iscolor


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

  
def timedeltatostring(stime, etime, fmin=False, colorn='', colors=''):
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
    tmsg.append('%s%02d%sd' % (colorn, outar[0], colors))
  if outar[1] != 0 or days:
    hours = True
    tmsg.append('%s%02d%sh' % (colorn, outar[1], colors))
  if outar[2] != 0 or days or hours or fmin:
    tmsg.append('%s%02d%sm' % (colorn, outar[2], colors))
  tmsg.append('%s%02d%ss' % (colorn, outar[3], colors))
    
  out   = ":".join(tmsg)
  return out


def ReadableNumber(num, places=2):
  """
  convert a number to a shorter readable number
  """
  ret = ''
  nform = "%%00.0%sf" % places
  if not num:
      return 0
  elif num >= 1000000000000:
      ret = nform % (num / 1000000000000.0) + " T" # trillion
  elif num >= 1000000000:
      ret = nform % (num / 1000000000.0) + " B" # billion
  elif num >= 1000000:
      ret = nform % (num / 1000000.0) + " M" # million
  elif num >= 1000:
      ret = nform % (num / 1000.0) + " K" # thousand
  else:
      ret = num # hundreds
  return ret


def SecondsToDHMS(sseconds):
  """
  convert seconds to years, days, hours, mins, secs
  """
  nseconds = int(sseconds)
  dtime = {
      'years' : 0,
      'days' : 0,
      'hours' : 0,
      'minutes': 0,
      'seconds': 0 
      }
  if nseconds == 0:
    return dtime
  
  dtime['years'] = math.floor(nseconds/(3600 * 24 * 365))
  dtime['days'] = math.floor(nseconds/(3600 * 24))
  dtime['hours'] = math.floor(nseconds/3600 - (dtime['days'] * 24))
  dtime['mins'] = math.floor(nseconds/60 - (dtime['hours'] * 60) \
                                        - (dtime['days'] * 24 * 60))
  dtime['secs'] = nseconds % 60
  return dtime
  
  
def format_time(length, nosec=False):
  """
  format a length of time into a string
  """
  msg = []
  dtime = SecondsToDHMS(length)
  years = False
  days = False
  hours = False
  mins = False
  if dtime['years'] > 0:
    years = True
    msg.append('%dy' % (dtime['years'] or 0))
  if dtime['days'] > 0:
    if years:
      msg.append(':')
    days = True
    msg.append('%dd' % (dtime['days'] or 0))
  if dtime['hours']:
    if years or days:
      msg.append(':')
    hours = True
    msg.append('%dh' % (dtime['hours'] or 0))
  if dtime['mins'] > 0:
    if years or days or hours:
      msg.append(':')
    mins = True
    msg.append('%dm' % (dtime['mins'] or 0))
  if (dtime['secs'] > 0 or len(msg) == 0) and not nosec:
    if years or days or hours or mins:
      msg.append(':')
    msg.append('%ds' % (dtime['secs'] or 0))
  
  return ''.join(msg)

  
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


def verify_color(val):
  """
  verify an @ color
  """
  if iscolor(val):
    return val
  
  raise ValueError

  
def verify(val, vtype):
  """
  verify values
  """
  vtab = {}
  vtab[bool] = verify_bool
  vtab['color'] = verify_color
  
  if vtype in vtab:
    return vtab[vtype](val)
  else:
    return vtype(val)
  
  
def convert(tinput):
  """
  converts input to ascii (utf-8)
  """  
  if isinstance(tinput, dict):
    return {convert(key): convert(value) for key, value in tinput.iteritems()}
  elif isinstance(tinput, list):
    return [convert(element) for element in tinput]
  elif isinstance(tinput, unicode):
    return tinput.encode('utf-8')
  else:
    return tinput
  
