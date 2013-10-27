"""
$Id$

This plugin will show information about connections to the proxy
"""
import time
import datetime
from plugins._baseplugin import BasePlugin
from libs.timing import timeit
from libs.color import convertcolors
from libs.event import Event
from libs.utils import secondstodhms

#these 5 are required
NAME = 'timers'
SNAME = 'timers'
PURPOSE = 'handle timers'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class TimerEvent(Event):
  """
  a class for a timer event
  """
  def __init__(self, name, args):
    """
    init the class

    time should be military time, "1430"

    """
    Event.__init__(self, name)
    self.func = args['func']
    self.seconds = args['seconds']
    self.onetime = False

    if 'seconds' in args:
      self.seconds = int(args['seconds'])
    else:
      self.seconds = 60*60*24

    if 'time' in args:
      self.time = args['time']
    else:
      self.time = None

    self.nextcall = self.getnext()

    if 'onetime' in args:
      self.onetime = args['onetime']
    self.enabled = True
    if 'enabled' in args:
      self.enabled = args['enabled']

  def getnext(self):
    """
    get the next time to call this timer
    """
    if self.time:
      now = datetime.datetime(2012, 1, 1)
      now = now.now()
      ttime = time.strptime(self.time, '%H%M')
      tnext = now.replace(hour=ttime.tm_hour, minute=ttime.tm_min, second=0)
      diff = tnext - now
      while diff.days < 0:
        tstuff = secondstodhms(self.seconds)
        tnext = tnext + datetime.timedelta(days=tstuff['days'],
                                          hours=tstuff['hours'],
                                          minutes=tstuff['mins'],
                                          seconds=tstuff['secs'])
        diff = tnext - now

      nextt = time.mktime(tnext.timetuple())

    else:
      nextt = int(time.time()) + self.seconds

    return nextt


  def timerstring(self):
    """
    return a string representation of the timer
    """
    return '%s : %d : %s : %d' % (self.name, self.seconds,
                                  self.enabled, self.nextcall)

class Plugin(BasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.timerevents = {}
    self.timerlookup = {}
    self.lasttime = int(time.time())
    self.api.get('output.msg')('lasttime:  %s' % self.lasttime)

    self.api.get('api.add')('add', self.addtimer)
    self.api.get('api.add')('remove', self.removetimer)
    self.api.get('api.add')('toggle', self.toggletimer)

    self.api.get('events.register')('global_timer', self.checktimerevents, prio=1)

  # add a timer
  def addtimer(self, name, args):
    """  add a timer
    @Yname@w   = The timer name
    @Yargs@w arguments:
      @Yseconds@w   = the interval (in seconds) to fire the timer
      @Yfunction@w  = the function to call when firing the timer
      @Yonetime@w   = True for a onetime timer, False otherwise

    returns an Event instance"""
    if not ('seconds' in args):
      self.api.get('output.msg')('timer %s has no seconds, not adding' % name)
      return
    if not ('func' in args):
      self.api.get('output.msg')('timer %s has no function, not adding' % name)
      return

    if 'nodupe' in args and args['nodupe']:
      if name in self.timerlookup:
        self.api.get('output.msg')('trying to add duplicate timer: %s' % name)
        return

    tevent = TimerEvent(name, args)
    self.api.get('output.msg')('adding %s' % tevent)
    self._addtimer(tevent)
    return tevent

  # remove a timer
  def removetimer(self, name):
    """  remove a timer
    @Yname@w   = the name of the timer to remove

    this function returns no values"""
    try:
      tevent = self.timerlookup[name]
      if tevent:
        ttime = tevent.nextcall
        if tevent in self.timerevents[ttime]:
          self.timerevents[ttime].remove(tevent)
        del self.timerlookup[name]
    except KeyError:
      self.api.get('output.msg')('%s does not exist' % name)

  # toggle a timer
  def toggletimer(self, name, flag):
    """  toggle a timer to be enabled/disabled
    @Yname@w   = the name of the timer to toggle
    @Yflag@w   = True to enable, False to disable

    this function returns no values"""
    if name in self.timerlookup:
      self.timerlookup[name].enabled = flag

  def _addtimer(self, timer):
    """
    internally add a timer
    """
    nexttime = timer.nextcall
    if not (nexttime in self.timerevents):
      self.timerevents[nexttime] = []
    self.timerevents[nexttime].append(timer)
    self.timerlookup[timer.name] = timer

  def checktimerevents(self, args):
    """
    check all timers
    """
    ntime = int(time.time())
    if ntime - self.lasttime > 1:
      self.api.get('output.msg')('timer had to check multiple seconds')
    for i in range(self.lasttime + 1, ntime + 1):
      if i in self.timerevents and len(self.timerevents[i]) > 0:
        for timer in self.timerevents[i]:
          if timer.enabled:
            try:
              timer.execute()
            except:
              self.api.get('output.traceback')('A timer had an error')
          self.timerevents[i].remove(timer)
          if not timer.onetime:
            timer.nextcall = timer.nextcall + timer.seconds
            self._addtimer(timer)
          else:
            self.removetimer(timer.name)
          if len(self.timerevents[i]) == 0:
            #self.api.get('output.msg')('deleting', i)
            del self.timerevents[i]

    self.lasttime = ntime
