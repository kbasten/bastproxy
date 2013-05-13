"""
$Id$
"""
import fnmatch
import os
import datetime
import math
import time
from libs.color import iscolor, strip_ansi, convertcolors
from libs.timing import timeit


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
  if os.sep in filematch:
    tstuff = filematch.split(os.sep)
    directory = os.path.join(directory, tstuff[0])
    filematch = tstuff[-1]
  for root, _, filenames in os.walk(directory):
    for filename in fnmatch.filter(filenames, filematch):
      matches.append(os.path.join(root, filename))

  return matches


def timedeltatostring(stime, etime, fmin=False, colorn='',
                       colors='', nosec=False):
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
  if not nosec:
    tmsg.append('%s%02d%ss' % (colorn, outar[3], colors))

  out   = ":".join(tmsg)
  return out


def readablenumber(num, places=2):
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


def secondstodhms(sseconds):
  """
  convert seconds to years, days, hours, mins, secs
  """
  nseconds = int(sseconds)
  dtime = {
      'years' : 0,
      'days' : 0,
      'hours' : 0,
      'mins': 0,
      'secs': 0
      }
  if nseconds == 0:
    return dtime

  dtime['years'] = int(math.floor(nseconds/(3600 * 24 * 365)))
  dtime['days'] = int(math.floor(nseconds/(3600 * 24)))
  dtime['hours'] = int(math.floor(nseconds/3600 - (dtime['days'] * 24)))
  dtime['mins'] = int(math.floor(nseconds/60 - (dtime['hours'] * 60) \
                                        - (dtime['days'] * 24 * 60)))
  dtime['secs'] = int(nseconds % 60)
  return dtime


def format_time(length, nosec=False):
  """
  format a length of time into a string
  """
  msg = []
  dtime = secondstodhms(length)
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
    msg.append('%02dd' % (dtime['days'] or 0))
  if dtime['hours']:
    if years or days:
      msg.append(':')
    hours = True
    msg.append('%02dh' % (dtime['hours'] or 0))
  if dtime['mins'] > 0:
    if years or days or hours:
      msg.append(':')
    mins = True
    msg.append('%02dm' % (dtime['mins'] or 0))
  if (dtime['secs'] > 0 or len(msg) == 0) and not nosec:
    if years or days or hours or mins:
      msg.append(':')
    msg.append('%02ds' % (dtime['secs'] or 0))

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


def verify_miltime(mtime):
  """
  verify a time like 0830 or 1850
  """
  try:
    time.strptime(mtime, '%H%M')
  except:
    raise ValueError

  return mtime


def verify(val, vtype):
  """
  verify values
  """
  vtab = {}
  vtab[bool] = verify_bool
  vtab['color'] = verify_color
  vtab['miltime'] = verify_miltime

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


def center(tstr, fillerc, length):
  """
  center a string with color codes
  """
  nocolor = strip_ansi(convertcolors(tstr))

  tlen = len(nocolor) + 4
  tdiff = length - tlen

  thalf = tdiff / 2
  tstr = "{filler}  {lstring}  {filler}".format(
        filler = fillerc * thalf,
        lstring = tstr)

  newl = (thalf * 2) + tlen

  if newl < length:
    tstr = tstr + '-' * (length - newl)

  return tstr

#TODO: This is slow, how can we speed it up?
def checklistformatch(arg, tlist):
  """
  check a list for a match of arg
  """
  sarg = str(arg)
  tdict = {}
  match = sarg + '*'
  tdict['part'] = []
  tdict['front'] = []

  if arg in tlist or sarg in tlist:
    return [arg]

  for i in tlist:
    if fnmatch.fnmatch(i, match):
      tdict['front'].append(i)
    elif isinstance(i, basestring) and sarg in i:
      tdict['part'].append(i)

  if tdict['front']:
    return tdict['front']
  else:
    return tdict['part']

  return tdict

