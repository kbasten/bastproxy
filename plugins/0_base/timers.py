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
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

class TimerEvent(Event):
  """
  a class for a timer event
  """
  def __init__(self, name, func, seconds, plugin, **kwargs):
    """
    init the class

    time should be military time, "1430"

    """
    Event.__init__(self, name, plugin)
    self.func = func
    self.seconds = seconds

    self.onetime = False
    if 'onetime' in kwargs:
      self.onetime = kwargs['onetime']

    self.enabled = True
    if 'enabled' in kwargs:
      self.enabled = kwargs['enabled']

    self.time = None
    if 'time' in kwargs:
      self.time = kwargs['time']

    self.nextcall = self.getnext()

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

  def __str__(self):
    """
    return a string representation of the timer
    """
    return 'Timer - %-10s : %-15s : %05d : %-6s : %d' % (self.name, self.plugin,
                                  self.seconds, self.enabled, self.nextcall)

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

    self.api.get('api.add')('add', self.api_addtimer)
    self.api.get('api.add')('remove', self.api_remove)
    self.api.get('api.add')('toggle', self.api_toggle)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('events.register')('global_timer', self.checktimerevents, prio=1)
    self.api.get('output.msg')('lasttime:  %s' % self.lasttime)

  # add a timer
  def api_addtimer(self, name, func, seconds, **kwargs):
    """  add a timer
    @Yname@w   = The timer name
    @Yfunc@w  = the function to call when firing the timer
    @Yseconds@w   = the interval (in seconds) to fire the timer
    @Yargs@w arguments:
      @Ynodupe@w    = True if no duplicates of this timer are allowed, False otherwise
      @Yonetime@w   = True for a onetime timer, False otherwise
      @Yenabled@w   = True if enabled, False otherwise
      @Ytime@w      = The time to start this timer, e.g. 1300 for 1PM

    returns an Event instance"""
    try:
      plugin = func.im_self
    except AttributeError:
      plugin = ''

    if 'plugin' in kwargs:
      plugin = self.api.get('plugins.getp')(kwargs['plugin'])

    args = {}
    if seconds <= 0:
      self.api.get('output.msg')('timer %s has seconds <= 0, not adding' % name,
                                    secondary=plugin)
      return
    if not func:
      self.api.get('output.msg')('timer %s has no function, not adding' % name,
                                    secondary=plugin)
      return

    if 'nodupe' in kwargs and kwargs['nodupe']:
      if name in self.timerlookup:
        self.api.get('output.msg')('trying to add duplicate timer: %s' % name,
                                    secondary=plugin)
        return

    tevent = TimerEvent(name, func, seconds, plugin, **kwargs)
    self.api.get('output.msg')('adding %s from plugin %s' % (tevent, plugin), secondary=plugin.sname)
    self._addtimer(tevent)
    return tevent

  # remove all the timers associated with a plugin
  def api_removeplugin(self, name):
    """  remove a timer
    @Yname@w   = the name of the plugin

    this function returns no values"""
    plugin = self.api.get('plugins.getp')(name)
    timerstoremove = []
    self.api.get('output.msg')('removing timers for %s' % name, secondary=name)
    for i in self.timerlookup:
      if plugin == self.timerlookup[i].plugin:
        timerstoremove.append(i)

    for i in timerstoremove:
      self.api.get('timers.remove')(i)


  # remove a timer
  def api_remove(self, name):
    """  remove a timer
    @Yname@w   = the name of the timer to remove

    this function returns no values"""
    try:
      tevent = self.timerlookup[name]
      if tevent:
        self.api.get('output.msg')('removing %s' % tevent, secondary=tevent.plugin)
        ttime = tevent.nextcall
        if tevent in self.timerevents[ttime]:
          self.timerevents[ttime].remove(tevent)
        del self.timerlookup[name]
    except KeyError:
      self.api.get('output.msg')('timer %s does not exist' % name)


  # toggle a timer
  def api_toggle(self, name, flag):
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
              self.api.get('output.msg')('Timer fired: %s' % timer,
                                         secondary=timer.plugin.sname)
            except:
              self.api.get('output.traceback')('A timer had an error')
          self.timerevents[i].remove(timer)
          if not timer.onetime:
            timer.nextcall = timer.nextcall + timer.seconds
            self._addtimer(timer)
          else:
            self.api.get('timers.remove')(timer.name)
          if len(self.timerevents[i]) == 0:
            del self.timerevents[i]

    self.lasttime = ntime
