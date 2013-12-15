"""
$Id$

This plugin handles events.
  You can register/unregister with events, raise events
"""
import inspect
import argparse
from libs.api import API
from libs import utils
from plugins._baseplugin import BasePlugin

NAME = 'Event Handler'
SNAME = 'events'
PURPOSE = 'Handle events'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 3

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a class to manage events, events include
    events
  """
  def __init__(self, *args, **kwargs):

    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.events = {}
    self.pluginlookup = {}

    self.api.get('api.add')('register', self.api_register)
    self.api.get('api.add')('unregister', self.api_unregister)
    self.api.get('api.add')('eraise', self.api_eraise)
    self.api.get('api.add')('removeplugin', self.api_removeplugin)
    self.api.get('api.add')('gete', self.api_getevent)
    self.api.get('api.add')('detail', self.api_detail)

  # return the event, will have registered functions
  def api_getevent(self, eventname):
    """  register a function with an event
    @Yeventname@w   = The event to register with

    this function returns a dictionary of format
      pluginslist = list of plugins that use this event
      funclist = a dictionary of funcnames, with their plugin,
              function name, and prio as values in a dictionary
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
      self.api.get('output.msg')(
                  'adding function %s (plugin: %s) to event %s' \
                          % (func, plugin, eventname), secondary=plugin)
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
                func, eventname), secondary=plugin)
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
    self.api.get('output.msg')('removing plugin %s' % plugin,
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
    self.api.get('output.msg')('raiseevent %s' % eventname)
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
              if eventname != 'global_timer':
                self.api.get('output.msg')('event %s : function %s, plugin %s called with args %s, returned %s' % \
                                         (eventname, i.__name__, plugin or 'Unknown', nargs, tnargs),
                                         secondary=plugin)
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

  # get the details of an event
  def api_detail(self, eventname):
    """  get the details of an event
    @Yeventname@w = The event name

    this function returns a list of strings for the info"""
    tmsg = []
    eventstuff = self.api.get('events.gete')(eventname)
    plugins = []
    tmsg.append('%-13s : %s' % ('Event', eventname))
    tmsg.append('@B' + utils.center('Registrations', '-', 60))
    tmsg.append('%-4s : %-15s - %-s' % ('prio',
                                        'plugin',
                                        'function name'))
    tmsg.append('@B' + '-' * 60)
    if not eventstuff:
      tmsg.append('None')
    else:
      for func in eventstuff['funcdict']:
        eventfunc = eventstuff['funcdict'][func]
        tmsg.append('%-4s : %-15s - %-s' % (eventfunc['priority'],
                                            eventfunc['plugin'],
                                            eventfunc['name']))
    tmsg.append('')
    return tmsg

  def cmd_detail(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list events and the plugins registered with them
      @CUsage@w: detail show @Y<eventname>@w
        @Yeventname@w  = the eventname to get info for
    """
    tmsg = []
    if len(args.event) > 0:
      for eventname in args.event:
        tmsg.extend(self.api.get('events.detail')(eventname))
        tmsg.append('')
    else:
      tmsg.append('Please provide an event name')

    return True, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      list events and the plugins registered with them
      @CUsage@w: list
    """
    tmsg = []
    match = args.match
    for name in self.events:
      if not match or match in name:
        if len(self.events[name]) > 0:
          tmsg.append(name)

    return True, tmsg

  def logloaded(self, args):
    """
    initialize the event log types
    """
    self.api.get('log.adddtype')(self.sname)
    #self.api.get('log.console')(self.sname)

  def load(self):
    """
    load the module
    """
    BasePlugin.load(self)
    self.api.get('managers.add')(self.sname, self)
    self.api.get('events.register')('log_plugin_loaded', self.logloaded)
    self.api.get('events.eraise')('event_plugin_loaded', {})

    parser = argparse.ArgumentParser(add_help=False,
                 description='get details of an event')
    parser.add_argument('event', help='list only events that have this argument in their name', default=[], nargs='*')
    self.api.get('commands.add')('detail', self.cmd_detail,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list events and the plugins registered with them')
    parser.add_argument('match', help='list only events that have this argument in their name', default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)
