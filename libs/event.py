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
   exported.debug('timer %s fired' % self.name)
   Event.execute(self)


class EventMgr:
  def __init__(self):
    self.triggers = {}
    self.regexlookup = {}
    self.events = {}
    self.timerevents = {}
    self.timerlookup = {}
    self.lasttime = int(time.time())
    exported.debug('lasttime', self.lasttime)
    self.registerevent('to_client_event', self.touser)
    self.registerevent('from_client_event', self.fromuser)
    self.registerevent('to_server_event', self.toserver)
    self.registerevent('from_server_event', self.fromserver)
    
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

  def processevent(self, eventname, args):
    #exported.debug('processevent', eventname, args)
    nargs = args.copy()
    nargs['eventname'] = eventname
    if eventname in self.events:
      keys = self.events[eventname].keys()
      if keys:
        keys.sort()
        for k in keys:
          for i in self.events[eventname][k]:
            tnargs = i(nargs)
            if tnargs:
              nargs = tnargs
    else:
      pass
      #exported.debug('nothing to process for %s' % eventname)
    #exported.debug('returning', nargs)
    return nargs

  def touser(self, args):
    #exported.debug('touser got', args['todata'].strip())
    pass

  def fromuser(self, args):
    #exported.debug('fromuser got', args['fromdata'].strip())
    pass

  def toserver(self, args):
    #exported.debug('touser got', args['todata'].strip())
    pass

  def fromserver(self, args):
    #exported.debug('fromuser got', args['fromdata'].strip())
    pass

  def addtimer(self, name, func, seconds, onetime):
    tevent = TimerEvent(name, func, seconds, onetime)
    #exported.debug('adding', tevent)
    self._addtimer(tevent)
    return tevent

  def deletetimer(self, name):
    tevent = self.timerlookup[name]
    if tevent:
      ttime = tevent.nextcall
      if tevent in self.timerevents[ttime]:
        self.timerevents[ttime].remove(tevent)
      del self.timerlookup[name]

  def _addtimer(self, timer):
    nexttime = timer.nextcall
    if not (nexttime in self.timerevents):
      self.timerevents[nexttime] = []
    self.timerevents[nexttime].append(timer)
    self.timerlookup[timer.name] = timer

  def checktimerevents(self):
    ntime = int(time.time())
    if ntime - self.lasttime > 1:
      exported.debug('timer had to check multiple seconds')
    #exported.debug('checking timers', self.lasttime, ntime)
    for i in range(self.lasttime + 1, ntime + 1):
      if i in self.timerevents and len(self.timerevents[i]) > 0:
        for timer in self.timerevents[i]:
          if timer.enabled:
            timer.execute()
          self.timerevents[i].remove(timer)
          if not timer.onetime:
            timer.nextcall = timer.nextcall + timer.seconds
            self._addtimer(timer)
          else:
            self.deletetimer(timer.name)
          if len(self.timerevents[i]) == 0:
            exported.debug('deleting', i)
            del self.timerevents[i]

    self.lasttime = ntime

  def enabletimer(self, name):
    if name in self.timerlookup:
      self.timerlookup[name].enabled = True

  def disabletimer(self, name):
    if name in self.timerlookup:
      self.timerlookup[name].enabled = False

