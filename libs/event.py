"""
$Id$

This plugin handles events.
  You can register/unregister with events, raise events
  Manipulate timers
  Manipulate triggers
  Watch for specific commands

"""
import datetime
import re
from libs.color import convertcolors
from libs.timing import timeit
from libs.utils import secondstodhms
from libs.api import API

class Event(object):
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


class EventMgr(object):
  """
  a class to manage events, events include
    timers
    triggers
    events
  """
  def __init__(self):
    self.sname = 'events'
    self.events = {}
    self.watchcmds = {}
    self.pluginlookup = {}
    self.regexlookup = {}
    self.api = API()

    self.api.add(self.sname, 'register', self.api_register)
    self.api.add(self.sname, 'unregister', self.api_unregister)
    self.api.add(self.sname, 'eraise', self.api_eraise)
    self.api.add(self.sname, 'removeplugin', self.api_removeplugin)

    self.api.add('watch', 'add', self.addwatch)
    self.api.add('watch', 'remove', self.removewatch)

    #print 'api', self.api.api
    #print 'overloadedapi', self.api.overloadedapi

  # add a cmd to watch for
  def addwatch(self, cmdname, args):
    """
    add a watch
    """
    if not ('regex' in args):
      self.api.get('output.msg')('cmdwatch %s has no regex, not adding' % cmdname, 'cmds')
      return
    if args['regex'] in self.regexlookup:
      self.api.get('output.msg')(
          'cmdwatch %s tried to add a regex that already existed for %s' % \
                      (cmdname, self.regexlookup[args['regex']]), 'cmds')
      return
    try:
      self.watchcmds[cmdname] = args
      self.watchcmds[cmdname]['compiled'] = re.compile(args['regex'])
      self.regexlookup[args['regex']] = cmdname
    except:
      self.api.get('output.traceback')(
          'Could not compile regex for cmd watch: %s : %s' % \
                (cmdname, args['regex']))

  # remove a command to watch for
  def removewatch(self, cmdname):
    """
    remove a watch
    """
    if cmdname in self.watchcmds:
      del self.regexlookup[self.watchcmds[cmdname]['regex']]
      del self.watchcmds[cmdname]
    else:
      self.api.get('output.msg')('removewatch: watch %s does not exist' % cmdname, 'cmds')

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
        self.api.get('output.msg')('raising %s' % targs['cmdname'], 'cmds')
        tdata = self.api.get('events.eraise')('cmd_' + i, targs)
        if 'changed' in tdata:
          data['nfromdata'] = tdata['changed']

    if 'nfromdata' in data:
      data['fromdata'] = data['nfromdata']
    return data


  # register a function with an event
  def api_register(self, eventname, func,  **kwargs):
    """  register a function with an event
    @Yeventname@w   = The event to register with
    @Yfunc@w        = The function to register
    keyword arguments:
      prio          = the priority of the function (default: 50)

    this function returns no values"""
    if not ('prio' in kwargs):
      prio = 50
    else:
      prio = kwargs['prio']
    try:
      plugin = func.im_self.sname
    except AttributeError:
      plugin = ''
    if not (eventname in self.events):
      self.events[eventname] = {}
    if not (prio in self.events[eventname]):
      self.events[eventname][prio] = []
    if self.events[eventname][prio].count(func) == 0:
      self.events[eventname][prio].append(func)
      self.api.get('output.msg')('adding function %s (plugin: %s) to event %s' % (func, plugin, eventname),
                     self.sname)
    if plugin:
      if not (plugin in self.pluginlookup):
        self.pluginlookup[plugin] = {}
        self.pluginlookup[plugin]['events'] = {}

      self.pluginlookup[plugin]['events'][func] = \
                            {'eventname':eventname, 'prio':prio}

  # unregister a function from an event
  def api_unregister(self, eventname, func, **kwargs):
    """  unregister a function with an event
    @Yeventname@w   = The event to unregister with
    @Yfunc@w        = The function to unregister
    keyword arguments:
      plugin        = the plugin this function is a part of

    this function returns no values"""
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
          self.api.get('output.msg')('removing function %s from event %s' % (
                func, eventname), self.sname)
          self.events[eventname][i].remove(func)

      if plugin and plugin in self.pluginlookup:
        if func in self.pluginlookup[plugin]['events']:
          del(self.pluginlookup[plugin]['events'][func])

  # remove all registered functions that are specific to a plugin
  def api_removeplugin(self, plugin):
    """  remove all registered functions that are specific to a plugin
    @Yplugin@w   = The plugin to remove events for
    this function returns no values"""
    self.api.get('output.msg')('removing plugin %s' % plugin, self.sname)
    if plugin and plugin in self.pluginlookup:
      tkeys = self.pluginlookup[plugin]['events'].keys()
      for i in tkeys:
        event = self.pluginlookup[plugin]['events'][i]
        self.api.get('events.unregister')(event['eventname'], i)

      self.pluginlookup[plugin]['events'] = {}

  # raise an event, args vary
  def api_eraise(self, eventname, args):
    """  raise an event with args
    @Yeventname@w   = The event to raise
    @Yargs@w        = A table of arguments

    this function returns no values"""
    self.api.get('output.msg')('raiseevent %s' % eventname, self.sname)
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
              #self.api.get('output.msg')('%s: returned %s' % (eventname, tnargs), self.sname)
              if tnargs:
                nargs = tnargs
            except:
              self.api.get('output.traceback')(
                      "error when calling function for event %s" % eventname)
    else:
      pass
      #self.api.get('output.msg')('nothing to process for %s' % eventname)
    #self.api.get('output.msg')('returning', nargs)
    return nargs

  def loggerloaded(self, args):
    """
    initialize the event logger types
    """
    self.api.get('logger.adddtype')(self.sname)
    #self.api.get('logger.console')(self.sname)


  def load(self):
    """
    load the module
    """
    self.api.get('managers.add')(self.sname, self)
    self.api.get('events.register')('plugin_logger_loaded', self.loggerloaded)
    self.api.get('events.register')('from_client_event', self.checkcmd)
    self.api.get('events.eraise')('plugin_event_loaded', {})


