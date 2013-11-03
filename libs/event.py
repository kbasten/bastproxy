"""
$Id$

This plugin handles events.
  You can register/unregister with events, raise events
"""
import inspect
from libs.api import API
from libs import utils


class Event(object):
  """
  a basic event class
  """
  def __init__(self, name, plugin):
    """
    init the class
    """
    self.name = name
    self.plugin = plugin

  def execute(self):
    """
    execute the event
    """
    self.func()

  def __str__(self):
    """
    return a string representation of the timer
    """
    return 'Event %-10s : %-15s' % (self.name, self.plugin)


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
    self.pluginlookup = {}
    self.api = API()

    self.api.add(self.sname, 'register', self.api_register)
    self.api.add(self.sname, 'unregister', self.api_unregister)
    self.api.add(self.sname, 'eraise', self.api_eraise)
    self.api.add(self.sname, 'removeplugin', self.api_removeplugin)
    self.api.add(self.sname, 'gete', self.api_getevent)

    #print 'api', self.api.api
    #print 'overloadedapi', self.api.overloadedapi

  # return the event, will have registered functions
  def api_getevent(self, eventname):
    """  register a function with an event
    @Yeventname@w   = The event to register with

    this function returns a dictionary of format
      pluginslist = list of plugins that use this event
      funclist = a dictionary of funcnames, with their plugin, function name, and prio as values in a dictionary
    """
    pluginlist = []
    funcdict = {}
    if eventname in self.events:
      for prio in self.events[eventname]:
        for func in self.events[eventname][prio]:
          try:
            plugin = func.im_self.sname
          except AttributeError:
            plugin = 'Unknown'
          if not (plugin in pluginlist):
            pluginlist.append(plugin)
          funcdict[func] = {}
          funcdict[func]['name'] = func.__name__
          funcdict[func]['priority'] = prio
          funcdict[func]['plugin'] = plugin

      return {'pluginlist':pluginlist, 'funcdict':funcdict}

    else:
      return {}

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
                     primary=self.sname, secondary=plugin)
    if plugin:
      if not (plugin in self.pluginlookup):
        self.pluginlookup[plugin] = {}
        self.pluginlookup[plugin]['events'] = {}

      if not (func in self.pluginlookup[plugin]['events']):
        self.pluginlookup[plugin]['events'][func] = []
      self.pluginlookup[plugin]['events'][func].append(eventname)

  # unregister a function from an event
  def api_unregister(self, eventname, func, **kwargs):
    """  unregister a function with an event
    @Yeventname@w   = The event to unregister with
    @Yfunc@w        = The function to unregister
    keyword arguments:
      plugin        = the plugin this function is a part of

    this function returns no values"""
    try:
      plugin = func.im_self.sname
    except AttributeError:
      plugin = ''
    if not self.events[eventname]:
      return
    keys = self.events[eventname].keys()
    if keys:
      keys.sort()
      for i in keys:
        if self.events[eventname][i].count(func) == 1:
          self.api.get('output.msg')('removing function %s from event %s' % (
                func, eventname), primary=self.sname, secondary=plugin)
          self.events[eventname][i].remove(func)
          if len(self.events[eventname][i]) == 0:
            del(self.events[eventname][i])

      if plugin and plugin in self.pluginlookup:
        if func in self.pluginlookup[plugin]['events'] \
            and eventname in self.pluginlookup[plugin]['events'][func]:
          self.pluginlookup[plugin]['events'][func].remove(eventname)

  # remove all registered functions that are specific to a plugin
  def api_removeplugin(self, plugin):
    """  remove all registered functions that are specific to a plugin
    @Yplugin@w   = The plugin to remove events for
    this function returns no values"""
    self.api.get('output.msg')('removing plugin %s' % plugin, primary=self.sname,
                                 secondary=plugin)
    if plugin and plugin in self.pluginlookup:
      tkeys = self.pluginlookup[plugin]['events'].keys()
      for func in tkeys:
        events = list(self.pluginlookup[plugin]['events'][func])
        for event in events:
          self.api.get('events.unregister')(event, func)

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
              try:
                plugin = i.im_self.sname
              except AttributeError:
                plugin = ''
              tnargs = i(nargs)
              self.api.get('output.msg')('event %s : function %s, plugin %s called with args %s, returned %s' % \
                                         (eventname, i.__name__, plugin or 'Unknown', nargs, tnargs),
                                         primary=self.sname, secondary=plugin)
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
    self.api.get('events.eraise')('plugin_event_loaded', {})


