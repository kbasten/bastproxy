"""
$Id$
"""

from __future__ import print_function

import sys
import time
from libs import exported

class Event:
  def __init__(self):
    pass

  def execute(self):
    self.func()


class TimerEvent(Event):
  def __init__(self, name, func, seconds, onetime):
    self.name = name
    self.func = func
    self.seconds = seconds
    self.onetime = onetime
    self.nextcall = int(time.time()) + self.seconds
    self.enabled = True

  def execute(self):
   #exported.msg('timer %s fired' % self.name)
   Event.execute(self)


class EventMgr:
  def __init__(self):
    self.triggers = {}
    self.regexlookup = {}
    self.events = {}
    self.timerevents = {}
    self.timerlookup = {}
    self.lasttime = int(time.time())
    exported.msg('lasttime:  %s' % self.lasttime, 'timer')
    
  def addtrigger(self, triggername, regex):
    self.trigger[triggername] = regex
    self.regexlookup[regex] = triggername

  def registerevent(self, eventname, func, prio=50):
    if not (eventname in self.events):
      self.events[eventname] = {}
    if not (prio in self.events[eventname]):
      self.events[eventname][prio] = []
    if self.events[eventname][prio].count(func) == 0:
      self.events[eventname][prio].append(func)

  def unregisterevent(self, eventname, func):
    if not self.events[eventname]:
      return
    keys = self.events[eventname].keys()
    if keys:
      keys.sort()
      for i in keys:
        if self.events[eventname][i].count(func) == 1:
          self.events[eventname][i].remove(func)

  def raiseevent(self, eventname, args):
    #exported.msg('raiseevent', eventname, args)
    nargs = args.copy()
    nargs['eventname'] = eventname
    if eventname in self.events:
      keys = self.events[eventname].keys()
      if keys:
        keys.sort()
        for k in keys:
          for i in self.events[eventname][k]:
            try:
              tnargs = i(nargs)
              if tnargs:
                nargs = tnargs
            except:
              exported.write_traceback("error when calling function for event %s" % eventname)
    else:
      pass
      #exported.msg('nothing to process for %s' % eventname)
    #exported.msg('returning', nargs)
    return nargs

  def addtimer(self, name, func, seconds, onetime):
    tevent = TimerEvent(name, func, seconds, onetime)
    #exported.msg('adding', tevent)
    self._addtimer(tevent)
    return tevent

  def deletetimer(self, name):
    try:
      tevent = self.timerlookup[name]
      if tevent:
        ttime = tevent.nextcall
        if tevent in self.timerevents[ttime]:
          self.timerevents[ttime].remove(tevent)
        del self.timerlookup[name]
    except KeyError:
      exported.msg('%s does not exist' % name, 'timer')

  def _addtimer(self, timer):
    nexttime = timer.nextcall
    if not (nexttime in self.timerevents):
      self.timerevents[nexttime] = []
    self.timerevents[nexttime].append(timer)
    self.timerlookup[timer.name] = timer

  def checktimerevents(self):
    ntime = int(time.time())
    if ntime - self.lasttime > 1:
      exported.msg('timer had to check multiple seconds', 'timer')
    #exported.msg('checking timers', self.lasttime, ntime)
    for i in range(self.lasttime + 1, ntime + 1):
      if i in self.timerevents and len(self.timerevents[i]) > 0:
        for timer in self.timerevents[i]:
          if timer.enabled:
            try:
              timer.execute()
            except:
              exported.write_traceback('A timer had an error')
          self.timerevents[i].remove(timer)
          if not timer.onetime:
            timer.nextcall = timer.nextcall + timer.seconds
            self._addtimer(timer)
          else:
            self.deletetimer(timer.name)
          if len(self.timerevents[i]) == 0:
            #exported.msg('deleting', i)
            del self.timerevents[i]

    self.lasttime = ntime

  def enabletimer(self, name):
    if name in self.timerlookup:
      self.timerlookup[name].enabled = True

  def disabletimer(self, name):
    if name in self.timerlookup:
      self.timerlookup[name].enabled = False

  def load(self):
    exported.logger.adddtype('timer')
  