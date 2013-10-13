"""
$Id$

This plugin handles events.
  You can register/unregister with events, raise events
  Manipulate timers
  Manipulate triggers
  Watch for specific commands

"""
import time
import datetime
import re
from libs import exported
from libs.color import convertcolors
from libs.timing import timeit
from libs.utils import secondstodhms

class Event:
  """
  a basic event class
  """
  def __init__(self, name):
    """
    init the class
    """
    self.name = name

  def execute(self):
    """
    execute the event
    """
    self.func()

  def timerstring(self):
    """
    return a string representation of the timer
    """
    return self.name


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


class EventMgr:
  """
  a class to manage events, events include
    timers
    triggers
    events
  """
  def __init__(self):
    self.sname = 'events'
    self.triggers = {}
    self.regexlookup = {}
    self.events = {}
    self.timerevents = {}
    self.watchcmds = {}
    self.timerlookup = {}
    self.triggergroups = {}
    self.pluginlookup = {}
    self.lasttime = int(time.time())
    self.registerevent('from_mud_event', self.checktrigger, prio=1)
    self.registerevent('from_client_event', self.checkcmd)
    exported.msg('lasttime:  %s' % self.lasttime, 'events')

    exported.add(self.addtrigger, 'trigger', 'add')
    exported.add(self.removetrigger, 'trigger', 'remove')
    exported.add(self.toggletrigger, 'trigger', 'toggle')
    exported.add(self.toggletriggergroup, 'trigger', 'togglegroup')
    exported.add(self.toggletriggeromit, 'trigger', 'toggleomit')

    exported.add(self.registerevent, 'event', 'register')
    exported.add(self.unregisterevent, 'event', 'unregister')
    exported.add(self.raiseevent, 'event', 'eraise')
    exported.add(self.removeplugin, 'event', 'removeplugin')

    exported.add(self.addtimer, 'timer', 'add')
    exported.add(self.removetimer, 'timer', 'remove')
    exported.add(self.toggletimer, 'timer', 'toggle')

    exported.add(self.addwatch, 'watch', 'add')
    exported.add(self.removewatch, 'watch', 'remove')

  def addwatch(self, cmdname, args):
    """
    add a watch
    """
    if not ('regex' in args):
      exported.msg('cmdwatch %s has no regex, not adding' % cmdname, 'cmds')
      return
    if args['regex'] in self.regexlookup:
      exported.msg(
          'cmdwatch %s tried to add a regex that already existed for %s' % \
                      (cmdname, self.regexlookup[args['regex']]), 'cmds')
      return
    try:
      self.watchcmds[cmdname] = args
      self.watchcmds[cmdname]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = cmdname
    except:
      exported.write_traceback(
          'Could not compile regex for cmd watch: %s : %s' % \
                (cmdname, args['regex']))

  def removewatch(self, cmdname):
    """
    remove a watch
    """
    if cmdname in self.watchcmds:
      del self.regexlookup[self.watchcmds[cmdname]['regex']]
      del self.watchcmds[cmdname]
    else:
      exported.msg('removewatch: watch %s does not exist' % cmdname, 'cmds')

  def checkcmd(self, data):
    """
    check input from the client and see if we are watching for it
    """
    tdat = data['fromdata'].strip()
    for i in self.watchcmds:
      cmdre = self.watchcmds[i]['compiled']
      mat = cmdre.match(tdat)
      if mat:
        targs = mat.groupdict()
        targs['cmdname'] = 'cmd_' + i
        targs['data'] = tdat
        exported.msg('raising %s' % targs['cmdname'], 'cmds')
        tdata = exported.event.eraise('cmd_' + i, targs)
        if 'changed' in tdata:
          data['nfromdata'] = tdata['changed']

    if 'nfromdata' in data:
      data['fromdata'] = data['nfromdata']
    return data

  def addtrigger(self, triggername, args):
    """
    add a trigger
    the args table should include the following keys:
      regex: the regular expression
      enabled: (optional) whether the trigger is enabled, default is True
      group: (optional) the group the trigger is in, default is None
      omit: (optional) whether to omit the line, default is False
    """
    if not ('regex' in args):
      exported.msg('trigger %s has no regex, not adding' % triggername,
                            'events')
      return
    if args['regex'] in self.regexlookup:
      exported.msg(
            'trigger %s tried to add a regex that already existed for %s' % \
                    (triggername, self.regexlookup[args['regex']]), 'events')
      return
    if not ('enabled' in args):
      args['enabled'] = True
    if not ('group' in args):
      args['group'] = None
    if not ('omit' in args):
      args['omit'] = False
    if not ('argtypes' in args):
      args['argtypes'] = {}
    try:
      self.triggers[triggername] = args
      self.triggers[triggername]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = triggername
      if args['group']:
        if not (args['group'] in self.triggergroups):
          self.triggergroups[args['group']] = []
        self.triggergroups[args['group']].append(triggername)
    except:
      exported.write_traceback(
              'Could not compile regex for trigger: %s : %s' % \
                      (triggername, args['regex']))

  def removetrigger(self, triggername):
    """
    remove a trigger
    """
    if triggername in self.triggers:
      del self.regexlookup[self.triggers[triggername]['regex']]
      del self.triggers[triggername]
    else:
      exported.msg('deletetrigger: trigger %s does not exist' % \
                        triggername, 'events')

  def toggletrigger(self, triggername, flag):
    """
    toggle a trigger
    """
    if triggername in self.triggers:
      self.triggers[triggername]['enabled'] = flag
    else:
      exported.msg('toggletrigger: trigger %s does not exist' % \
                        triggername, 'events')

  def toggletriggeromit(self, triggername, flag):
    """
    toggle a trigger
    """
    if triggername in self.triggers:
      self.triggers[triggername]['omit'] = flag
    else:
      exported.msg('toggletriggeromit: trigger %s does not exist' % \
                        triggername, 'events')

  def toggletriggergroup(self, triggroup, flag):
    """
    toggle a trigger group
    """
    exported.msg('toggletriggergroup: %s to %s' % (triggroup, flag), 'events')
    if triggroup in self.triggergroups:
      for i in self.triggergroups[triggroup]:
        self.toggletrigger(i, flag)

  @timeit
  def checktrigger(self, args):
    """
    check a line of text from the mud
    the is called whenever the from_mud_event is raised
    """
    data = args['nocolordata']

    self.raisetrigger('beall', {'line':data, 'triggername':'all'}, args)

    if data == '':
      self.raisetrigger('emptyline',
                        {'line':'', 'triggername':'emptyline'}, args)
    else:
      for i in self.triggers:
        if self.triggers[i]['enabled']:
          trigre = self.triggers[i]['compiled']
          mat = trigre.match(data)
          if mat:
            targs = mat.groupdict()
            if 'argtypes' in self.triggers[i]:
              for arg in self.triggers[i]['argtypes']:
                if arg in targs:
                  targs[arg] = self.triggers[i]['argtypes'][arg](targs[arg])
            targs['line'] = data
            targs['triggername'] = i
            args = self.raisetrigger(i, targs, args)

    self.raisetrigger('all', {'line':data, 'triggername':'all'}, args)

    return args

  def raisetrigger(self, triggername, args, origargs):
    """
    raise a trigger event
    """
    tdat = self.raiseevent('trigger_' + triggername, args)
    exported.msg('trigger raiseevent returned: %s' % tdat, 'events')
    if tdat and 'newline' in tdat:
      exported.msg('changing line from trigger', 'events')
      origargs['fromdata'] = convertcolors(tdat['newline'])
    if triggername in self.triggers and self.triggers[triggername]['omit']:
      origargs['fromdata'] = ''
    return

  def registerevent(self, eventname, func,  **kwargs):
    """
    register a function with an event
    """
    if not ('prio' in kwargs):
      prio = 50
    else:
      prio = kwargs['prio']
    if not ('plugin' in kwargs):
      plugin = ''
    else:
      plugin = kwargs['plugin']
    if not (eventname in self.events):
      self.events[eventname] = {}
    if not (prio in self.events[eventname]):
      self.events[eventname][prio] = []
    if self.events[eventname][prio].count(func) == 0:
      self.events[eventname][prio].append(func)
      exported.msg('adding function %s to event %s' % (func, eventname),
                     'events')
    if plugin:
      if not (plugin in self.pluginlookup):
        self.pluginlookup[plugin] = {}
        self.pluginlookup[plugin]['events'] = {}

      self.pluginlookup[plugin]['events'][func] = \
                            {'eventname':eventname, 'prio':prio}

  def unregisterevent(self, eventname, func, **kwargs):
    """
    unregister a function with an event
    """
    if not ('plugin' in kwargs):
      plugin = ''
    else:
      plugin = kwargs['plugin']
    if not self.events[eventname]:
      return
    keys = self.events[eventname].keys()
    if keys:
      keys.sort()
      for i in keys:
        if self.events[eventname][i].count(func) == 1:
          exported.msg('removing function %s from event %s' % (
                func, eventname), 'events')
          self.events[eventname][i].remove(func)

      if plugin and plugin in self.pluginlookup:
        if func in self.pluginlookup[plugin]['events']:
          del(self.pluginlookup[plugin]['events'][func])

  def removeplugin(self, plugin):
    """
    remove all events related to a plugin
    """
    exported.msg('removing plugin %s' % plugin, 'events')
    if plugin and plugin in self.pluginlookup:
      tkeys = self.pluginlookup[plugin]['events'].keys()
      for i in tkeys:
        event = self.pluginlookup[plugin]['events'][i]
        self.unregisterevent(event['eventname'], i, plugin=plugin)

      self.pluginlookup[plugin]['events'] = {}

  def raiseevent(self, eventname, args):
    """
    raise an event with args
    """
    exported.msg('raiseevent %s' % eventname, 'events')
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
              #exported.msg('%s: returned %s' % (eventname, tnargs), 'events')
              if tnargs:
                nargs = tnargs
            except:
              exported.write_traceback(
                      "error when calling function for event %s" % eventname)
    else:
      pass
      #exported.msg('nothing to process for %s' % eventname)
    #exported.msg('returning', nargs)
    return nargs

  def addtimer(self, name, args):
    """
    add a timer
    the args table should include the following keys:
      seconds: the # of seconds this timer will fire
      function: the function to call when this timer fires
      onetime: (optional) whether this is a onetime timer, default is False
    """
    if not ('seconds' in args):
      exported.msg('timer %s has no seconds, not adding' % name, 'events')
      return
    if not ('func' in args):
      exported.msg('timer %s has no function, not adding' % name, 'events')
      return

    if 'nodupe' in args and args['nodupe']:
      if name in self.timerlookup:
        exported.msg('trying to add duplicate timer: %s' % name)
        return

    tevent = TimerEvent(name, args)
    exported.msg('adding', tevent)
    self._addtimer(tevent)
    return tevent

  def removetimer(self, name):
    """
    remove a timer
    """
    try:
      tevent = self.timerlookup[name]
      if tevent:
        ttime = tevent.nextcall
        if tevent in self.timerevents[ttime]:
          self.timerevents[ttime].remove(tevent)
        del self.timerlookup[name]
    except KeyError:
      exported.msg('%s does not exist' % name, 'events')

  def toggletimer(self, name, flag):
    """
    toggle a timer
    """
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

  def checktimerevents(self):
    """
    check all timers
    """
    ntime = int(time.time())
    if ntime - self.lasttime > 1:
      exported.msg('timer had to check multiple seconds', 'events')
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
            self.removetimer(timer.name)
          if len(self.timerevents[i]) == 0:
            #exported.msg('deleting', i)
            del self.timerevents[i]

    self.lasttime = ntime

  def load(self):
    """
    load the module
    """
    exported.LOGGER.adddtype(self.sname)
    exported.LOGGER.cmd_console(self.sname)

  def unload(self):
    """
    unload the module
    """
    exported.remove('event')
    exported.remove('trigger')
    exported.remove('timer')

