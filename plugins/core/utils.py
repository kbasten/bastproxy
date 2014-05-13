"""
This plugin handles utility functions
"""
import re
import datetime
import math
import time
import fnmatch
from plugins._baseplugin import BasePlugin

NAME = 'Utility functions'
SNAME = 'utils'
PURPOSE = 'Utility Functions'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 12

AUTOLOAD = True

TIMELENGTH_REGEXP = re.compile(r"^(?P<days>\d+d)?:?(?P<hours>\d+h)" \
                              "?:?(?P<minutes>\d+m)?:?(?P<seconds>\d+s?)?$")


class Plugin(BasePlugin):
  """
  a plugin to handle ansi colors
  """
  def __init__(self, *args, **kwargs):
    BasePlugin.__init__(self, *args, **kwargs)

    self.api.get('api.add')('timedeltatostring', self.api_timedeltatostring)
    self.api.get('api.add')('readablenumber', self.api_readablenumber)
    self.api.get('api.add')('secondstodhms', self.api_secondstodhms)
    self.api.get('api.add')('formattime', self.api_formattime)
    self.api.get('api.add')('center', self.api_center)
    self.api.get('api.add')('checklistformatch', self.api_checklistformatch)
    self.api.get('api.add')('timelengthtosecs', self.api_timelengthtosecs)
    self.api.get('api.add')('verify', self.api_verify)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

  def api_timedeltatostring(self, stime, etime, fmin=False, colorn='',
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

  def api_readablenumber(self, num, places=2):
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

  def api_secondstodhms(self, sseconds):
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
    nseconds = nseconds - (dtime['years'] * 3600 * 24 * 365)
    dtime['days'] = int(math.floor(nseconds/(3600 * 24)))
    nseconds = nseconds - (dtime['days'] * 3600 * 24)
    dtime['hours'] = int(math.floor(nseconds/3600))
    nseconds = nseconds - (dtime['hours'] * 3600)
    dtime['mins'] = int(math.floor(nseconds/60))
    nseconds = nseconds - (dtime['mins'] * 60)
    dtime['secs'] = int(nseconds % 60)
    return dtime

  def api_formattime(self, length, nosec=False):
    """
    format a length of time into a string
    """
    msg = []
    dtime = self.api.get('utils.secondstodhms')(length)
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

  def verify_bool(self, val):
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

  def verify_color(self, val):
    """
    verify an @ color
    """
    if self.api.get('colors.iscolor')(val):
      return val

    raise ValueError

  def verify_miltime(self, mtime):
    """
    verify a time like 0830 or 1850
    """
    try:
      time.strptime(mtime, '%H%M')
    except:
      raise ValueError

    return mtime

  def verify_timelength(self, usertime):
    """
    verify a user time length
    """
    ttime = None

    try:
      ttime = int(usertime)
    except ValueError:
      ttime = self.api.get('utils.timelengthtosecs')(usertime)

    if ttime != 0 and not ttime:
      raise ValueError

    return ttime

  def api_verify(self, val, vtype):
    """
    verify values
    """
    vtab = {}
    vtab[bool] = self.verify_bool
    vtab['color'] = self.verify_color
    vtab['miltime'] = self.verify_miltime
    vtab['timelength'] = self.verify_timelength

    if vtype in vtab:
      return vtab[vtype](val)
    else:
      return vtype(val)

  def api_center(self, tstr, fillerc, length):
    """
    center a string with color codes
    """
    convertcolors = self.api.get('colors.convertcolors')(tstr)
    nocolor = self.api.get('colors.stripansi')(convertcolors)

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

  def api_checklistformatch(self, arg, tlist):
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

  def api_timelengthtosecs(self, timel):
    """
    converts a time length to seconds

    Format is 1d:2h:30m:40s, any part can be missing
    """
    tmatch = TIMELENGTH_REGEXP.match(timel)

    if not tmatch:
      return None

    timem = tmatch.groupdict()

    if not timem["days"] and not timem["hours"] and not timem["minutes"] \
            and not timem["seconds"]:
      return None

    days = timem["days"]
    if not days:
      days = 0
    elif days.endswith("d"):
      days = int(days[:-1])

    hours = timem["hours"]
    if not hours:
      hours = 0
    elif hours.endswith("h"):
      hours = int(hours[:-1])

    minutes = timem["minutes"]
    if not minutes:
      minutes = 0
    elif minutes.endswith("m"):
      minutes = int(minutes[:-1])

    seconds = timem["seconds"]
    if not seconds:
      seconds = 0
    elif seconds.endswith("s"):
      seconds = int(seconds[:-1])

    return days * 24 * 60 * 60 + hours * 60 * 60 + minutes * 60 + seconds

