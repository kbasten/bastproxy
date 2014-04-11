"""
$Id$

This plugin holds information about timers
"""
import time
import datetime
import argparse
from plugins._baseplugin import BasePlugin
from libs.event import Event

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
    Event.__init__(self, name, plugin, func)
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

    self.nextcall = self.getnext() or -1

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
        tstuff = self.plugin.api.get('utils.secondstodhms')(self.seconds)
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
    return 'Timer - %-10s : %-15s : %05d : %-6s : %s' % (self.name,
                                  self.plugin,
                                  self.seconds, self.enabled,
                                  time.strftime('%a %b %d %Y %H:%M:%S',
                                  time.localtime(self.nextcall)))

class Plugin(BasePlugin):
  """
  a plugin to handle timers
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.timerevents = {}
    self.timerlookup = {}
    self.overallfire = 0
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

    self.api.get('events.register')('global_timer', self.checktimerevents,
                                        prio=1)
    self.api.get('send.msg')('lasttime:  %s' % self.lasttime)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list timers')
    parser.add_argument('match',
              help='list only events that have this argument in their name',
              default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get details for timers')
    parser.add_argument('timers', help='a list of timers to get details',
                        default=[], nargs='*')
    self.api.get('commands.add')('detail', self.cmd_detail,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='get overall timer stats')
    self.api.get('commands.add')('stats', self.cmd_stats,
                                 parser=parser)

  def cmd_stats(self, args=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      show timer stats
      @CUsage@w: detail
    """
    tmsg = []

    disabled = 0
    enabled = 0

    for i in self.timerlookup:
      if self.timerlookup[i].enabled:
        enabled = enabled + 1
      else:
        disabled = disabled + 1

    tmsg.append('%-20s : %s' % ('Total Timers', len(self.timerlookup)))
    tmsg.append('%-20s : %s' % ('Timers Fired', self.overallfire))
    tmsg.append('%-20s : %s' % ('Enabled', enabled))
    tmsg.append('%-20s : %s' % ('Disabled', disabled))

    return True, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list timers and the plugins they are defined in
      @CUsage@w: list
    """
    tmsg = []

    match = args['match']

    tmsg.append('Local time is: %s' % time.strftime('%a %b %d %Y %H:%M:%S',
                                             time.localtime()))

    tmsg.append('%-20s : %-13s %-9s %-8s %s' % ('Name', 'Defined in',
                                        'Enabled', 'Fired', 'Next Fire'))
    for i in self.timerlookup:
      if not match or match in i:
        timerc = self.timerlookup[i]
        tmsg.append('%-20s : %-13s %-9s %-8s %s' % (
                                timerc.name, timerc.plugin.sname,
                                timerc.enabled, timerc.timesfired,
                                time.strftime('%a %b %d %Y %H:%M:%S',
                                time.localtime(timerc.nextcall))))

    return True, tmsg

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list the details of a timer
      @CUsage@w: detail
    """
    tmsg = []
    if len(args['timers']) > 0:
      for timer in args['timers']:
        if timer in self.timerlookup:
          timerc = self.timerlookup[timer]
          tmsg.append('%-13s : %s' % ('Name', timer))
          tmsg.append('%-13s : %s' % ('Enabled', timerc.enabled))
          tmsg.append('%-13s : %s' % ('Plugin', timerc.plugin.sname))
          tmsg.append('%-13s : %s' % ('Onetime', timerc.onetime))
          tmsg.append('%-13s : %s' % ('Time', timerc.time))
          tmsg.append('%-13s : %s' % ('Seconds', timerc.seconds))
          tmsg.append('%-13s : %s' % ('Times Fired', timerc.timesfired))
          tmsg.append('%-13s : %s' % ('Next Fire',
                                        time.strftime('%a %b %d %Y %H:%M:%S',
                                        time.localtime(timerc.nextcall))))
          tmsg.append('')

    else:
      tmsg.append('Please specify a timer name')

    return True, tmsg

  # add a timer
  def api_addtimer(self, name, func, seconds, **kwargs):
    """  add a timer
    @Yname@w   = The timer name
    @Yfunc@w  = the function to call when firing the timer
    @Yseconds@w   = the interval (in seconds) to fire the timer
    @Yargs@w arguments:
      @Ynodupe@w    = True if no duplicates of this timer are allowed,
                                    False otherwise
      @Yonetime@w   = True for a onetime timer, False otherwise
      @Yenabled@w   = True if enabled, False otherwise
      @Ytime@w      = The time to start this timer, e.g. 1300 for 1PM

    returns an Event instance"""
    plugin = None
    try:
      plugin = func.im_self
    except AttributeError:
      plugin = ''

    if 'plugin' in kwargs:
      plugin = self.api.get('plugins.getp')(kwargs['plugin'])

    args = {}
    if not plugin:
      self.api.get('send.msg')('timer %s has no plugin, not adding' % name)
      return
    if seconds <= 0:
      self.api.get('send.msg')('timer %s has seconds <= 0, not adding' % name,
                                    secondary=plugin)
      return
    if not func:
      self.api.get('send.msg')('timer %s has no function, not adding' % name,
                                    secondary=plugin)
      return

    if 'nodupe' in kwargs and kwargs['nodupe']:
      if name in self.timerlookup:
        self.api.get('send.msg')('trying to add duplicate timer: %s' % name,
                                    secondary=plugin)
        return

    tevent = TimerEvent(name, func, seconds, plugin, **kwargs)
    self.api.get('send.msg')('adding %s from plugin %s' % (tevent, plugin),
                             secondary=plugin.sname)
    self._addtimer(tevent)
    return tevent

  # remove all the timers associated with a plugin
  def api_removeplugin(self, name):
    """  remove a timer
    @Yname@w   = the name of the plugin

    this function returns no values"""
    plugin = self.api.get('plugins.getp')(name)
    timerstoremove = []
    self.api.get('send.msg')('removing timers for %s' % name, secondary=name)
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
        self.api.get('send.msg')('removing %s' % tevent,
                                 secondary=tevent.plugin)
        ttime = tevent.nextcall
        if tevent in self.timerevents[ttime]:
          self.timerevents[ttime].remove(tevent)
        del self.timerlookup[name]
    except KeyError:
      self.api.get('send.msg')('timer %s does not exist' % name)


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
      self.api.get('send.msg')('timer had to check multiple seconds')
    for i in range(self.lasttime, ntime + 1):
      if i in self.timerevents and len(self.timerevents[i]) > 0:
        for timer in self.timerevents[i]:
          if timer.enabled:
            try:
              timer.execute()
              timer.timesfired = timer.timesfired + 1
              self.overallfire = self.overallfire + 1
              self.api.get('send.msg')('Timer fired: %s' % timer,
                                         secondary=timer.plugin.sname)
            except:
              self.api.get('send.traceback')('A timer had an error')
          self.timerevents[i].remove(timer)
          if not timer.onetime:
            timer.nextcall = timer.nextcall + timer.seconds
            self.api.get('send.msg')('Re adding timer %s for %s' % (timer.name,
                                    time.strftime('%a %b %d %Y %H:%M:%S',
                                             time.localtime(timer.nextcall))),
                                    secondary=timer.plugin.sname)
            self._addtimer(timer)
          else:
            self.api.get('timers.remove')(timer.name)
          if len(self.timerevents[i]) == 0:
            del self.timerevents[i]

    self.lasttime = ntime
