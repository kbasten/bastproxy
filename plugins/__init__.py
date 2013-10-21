"""
$Id$

#TODO: make initialized events use the same syntax as runtime added events
  make an addevent function to the plugin baseclass
  same with commands and all other items that can be added at runtime

make all functions that add things use kwargs instead of a table
"""

import glob
import os
import sys
import inspect

from libs.utils import find_files, verify, convert
from libs.persistentdict import PersistentDict
from libs.utils import DotDict
from libs.api import API


class PersistentDictEvent(PersistentDict):
  """
  a class to send events when a dictionary object is set
  """
  def __init__(self, plugin, filename, *args, **kwds):
    """
    init the class
    """
    self.plugin = plugin
    self.api = API()
    PersistentDict.__init__(self, filename, *args, **kwds)

  def __setitem__(self, key, val):
    """
    override setitem
    """
    key = convert(key)
    val = convert(val)
    dict.__setitem__(self, key, val)
    eventname = '%s_%s' % (self.plugin.sname, key)
    if not self.plugin.resetflag:
      self.api.get('events.eraise')(eventname, {'var':key,
                                        'newvalue':val})


def get_module_name(path, filename):
  """
  get a module name
  """
  filename = filename.replace(path, "")
  path, filename = os.path.split(filename)
  tpath = path.split(os.sep)
  path = '.'.join(tpath)
  return path, os.path.splitext(filename)[0]


def findplugin(name):
  """
  find a plugin file
  """
  basepath = ''
  index = __file__.rfind(os.sep)
  if index == -1:
    basepath = "." + os.sep
  else:
    basepath = __file__[:index]

  _module_list = find_files( basepath, name + ".py")

  if len(_module_list) == 1:
    return _module_list[0], basepath

  return False, ''


class BasePlugin(object):
  """
  a base class for plugins
  """
  def __init__(self, name, sname, fullname, basepath, fullimploc):
    """
    initialize the instance
    """
    self.author = ''
    self.purpose = ''
    self.version = 0
    self.name = name
    self.sname = sname
    self.dependencies = []
    self.canreload = True
    self.resetflag = False
    self.api = API()
    self.savedir = os.path.join(self.api.BASEPATH, 'data',
                                      'plugins', self.sname)
    try:
      os.makedirs(self.savedir)
    except OSError:
      pass
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                    'plugins', self.sname, 'variables.txt')
    self.fullname = fullname
    self.basepath = basepath
    self.fullimploc = fullimploc

    self.cmds = {}
    self.defaultcmd = ''
    self.variables = PersistentDictEvent(self, self.savefile,
                            'c', format='json')
    self.settings = {}
    self.api.overload('events', 'register', self.eventregister)
    self.api.overload('events', 'unregister', self.eventunregister)
    self.api.overload('output', 'msg', self.msg)
    self.timers = {}
    self.triggers = {}
    self.exported = {}
    self.cmdwatch = {}

    self.api.get('logger.adddtype')(self.sname)
    self.cmds['set'] = {'func':self.cmd_set, 'shelp':'Show/Set Variables'}
    self.cmds['reset'] = {'func':self.cmd_reset, 'shelp':'reset the plugin'}
    self.cmds['save'] = {'func':self.cmd_save, 'shelp':'save plugin state'}
    self.api.get('events.register')('firstactive', self.firstactive)

  def load(self):
    """
    load stuff
    """
    # load all commands
    proxy = self.api.get('managers.getm')('proxy')

    for i in self.cmds:
      cmd = self.cmds[i]
      if not 'lname' in cmd:
        cmd['lname'] = self.name
      self.api.get('commands.add')(self.sname, i, cmd)
      #self.addCmd(i, cmd['func'], cmd['shelp'])

    # if there is a default command, then set it
    if self.defaultcmd:
      self.api.get('commands.default')(self.sname, self.defaultcmd)

    self.variables.pload()

    # register all timers
    for i in self.timers:
      tim = self.timers[i]
      self.api.get('timer.add')(i, tim)

    for i in self.triggers:
      self.api.get('trigger.add')(i, self.triggers[i])

    for i in self.cmdwatch:
      self.api.get('cmdwatch.add')(i, self.watch[i])

    if len(self.exported) > 0:
      for i in self.exported:
        self.api.add(self.sname, i, self.exported[i]['func'])

    if proxy and proxy.connected:
      if self.api.get('aardu.firstactive')():
        self.api.get('events.unregister')('firstactive', self.firstactive)
        self.firstactive()

    self.api.get('events.eraise')('event_plugin_load', {'plugin':self.sname})

  def unload(self):
    """
    unload stuff
    """
    self.api.get('output.msg')('unloading %s' % self.name)

    #clear all commands for this plugin
    self.api.get('commands.reset')(self.sname)

    #remove all events
    self.api.get('events.removeplugin')(self.sname)

    # delete all timers
    for i in self.timers:
      self.api.get('timer.remove')(i)

    for i in self.triggers:
      self.api.get('trigger.remove')(i)

    for i in self.cmdwatch:
      self.api.get('cmdwatch.remove')(i, self.watch[i])

    #save the state
    self.savestate()

    self.api.remove(self.sname)

    self.api.get('events.eraise')('event_plugin_unload', {'plugin':self.sname})


  def msg(self, msg):
    """
    an internal function to send msgs
    """
    self.api.get('output.msg', True)(msg, self.sname)

  def savestate(self):
    """
    save the state
    """
    self.variables.sync()

  def cmd_set(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List or set vars
    @CUsage@w: var @Y<varname>@w @Y<varvalue>@w
      @Yvarname@w    = The variable to set
      @Yvarvalue@w   = The value to set it to
      if there are no arguments or 'list' is the first argument then
      it will list the variables for the plugin
    """
    if len(args) == 0 or args[0] == 'list':
      return True, self.listvars()
    elif len(args) == 2:
      var = args[0]
      val = args[1]
      if var in self.settings:
        if 'readonly' in self.settings[var] \
              and self.settings[var]['readonly']:
          return True, ['%s is a readonly setting' % var]
        else:
          if val == 'default':
            val = self.settings[var]['default']
          try:
            val = verify(val, self.settings[var]['stype'])
            self.variables[var] = val
            self.variables.sync()
            tvar = self.variables[var]
            if self.settings[var]['nocolor']:
              tvar = tvar.replace('@', '@@')
            elif self.settings[var]['stype'] == 'color':
              tvar = '%s%s@w' % (val, val.replace('@', '@@'))
            return True, ['set %s to %s' % (var, tvar)]
          except ValueError:
            msg = ['Cannot convert %s to %s' % \
                                    (val, self.settings[var]['stype'])]
            return True, msg
        return True, self.listvars()
    return False, {}

  def cmd_save(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    save plugin state
    @CUsage@w: save
    """
    self.savestate()
    return True, ['Plugin settings saved']

  def listvars(self):
    """
    return a list of strings that list all variables
    """
    tmsg = []
    if len(self.variables) == 0:
      tmsg.append('There are no variables defined')
    else:
      tform = '%-15s : %-15s - %s'
      for i in self.settings:
        val = self.variables[i]
        if 'nocolor' in self.settings[i] and self.settings[i]['nocolor']:
          val = val.replace('@', '@@')
        elif self.settings[i]['stype'] == 'color':
          val = '%s%s@w' % (val, val.replace('@', '@@'))
        tmsg.append(tform % (i, val, self.settings[i]['help']))
    return tmsg

  def addsetting(self, name, default, stype, shelp, **kwargs):
    """
    add a setting
    """
    if 'nocolor' in kwargs:
      nocolor = kwargs['nocolor']
    else:
      nocolor = False
    if 'readonly' in kwargs:
      readonly = kwargs['readonly']
    else:
      readonly = False
    if not (name in self.variables):
      self.variables[name] = default
    self.settings[name] = {'default':default, 'help':shelp,
                  'stype':stype, 'nocolor':nocolor, 'readonly':readonly}

  def cmd_reset(self, _=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      reset the plugin
      @CUsage@w: reset
    """
    self.reset()
    return True, ['Plugin reset']

  def reset(self):
    """
    internal function to reset data
    """
    self.resetflag = True
    self.variables.clear()
    for i in self.settings:
      self.variables[i] = self.settings[i]['default']
    self.variables.sync()
    self.resetflag = False

  def firstactive(self, _=None):
    """
    if we are connected do
    """
    self.api.get('events.unregister')('firstactive', self.firstactive)

  def eventregister(self, eventname, tfunc):
    """
    register an event
    """
    # we call the non overloaded version
    self.api.get('events.register', True)(eventname, tfunc, plugin=self.sname)

  def eventunregister(self, eventname, tfunc):
    """
    unregister an event
    """
    # we call the non overloaded versions
    self.api.get('events.unregister', True)(eventname, tfunc, plugin=self.sname)


class PluginMgr(object):
  """
  a class to manage plugins
  """
  def __init__(self):
    """
    initialize the instance
    """
    self.plugins = {}
    self.pluginl = {}
    self.pluginm = {}
    self.api = API()
    self.savefile = os.path.join(self.api.BASEPATH, 'data',
                                          'plugins', 'loadedplugins.txt')
    self.loadedplugins = PersistentDict(self.savefile, 'c', format='json')
    self.sname = 'plugins'
    self.lname = 'Plugins'
    self.api.get('logger.adddtype')(self.sname)
    self.api.get('logger.console')([self.sname])
    self.api.add(self.sname, 'isinstalled', self.isinstalled)

  def isinstalled(self, pluginname):
    """
    check if a plugin is installed
    """
    if pluginname in self.plugins or pluginname in self.pluginl:
      return True
    return False

  def loaddependencies(self, pluginname, dependencies):
    """
    load a list of modules
    """
    for i in dependencies:
      if i in self.plugins or i in self.pluginl:
        continue

      self.api.get('output.msg')('%s: loading dependency %s' % (pluginname, i), pluginname)

      name, path = findplugin(i)
      if name:
        self.load_module(name, path, force=True)

  def cmd_exported(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      see what functions are available to the exported module
      useful for finding out what can be gotten for scripting
      @CUsage@w: exported
    """
    tmsg = []
    if len(args) == 0:
      tmsg.append('Items available in exported')
      for i in dir(exported):
        if not (i in ['sys', 'traceback', '__builtins__', '__doc__',
                                '__file__', '__name__', '__package__',]):
          if inspect.isfunction(exported.__dict__[i]):
            tmsg.append('Function: %s' % i)
          elif isinstance(exported.__dict__[i], dict):
            for tfunc in exported.__dict__[i]:
              tmsg.append('Function: %s.%s' % (i, tfunc))
    else:
      i = args[0]
      if i in dir(exported):
        if inspect.isfunction(exported.__dict__[i]):
          tmsg = self.printexported(i, exported.__dict__[i])
        elif isinstance(exported.__dict__[i], dict):
          tmsg = []
          for tfunc in exported.__dict__[i]:
            tmsg = tmsg + self.printexported('%s.%s' % (i, tfunc),
                                          exported.__dict__[i][tfunc])
      else:
        tmsg.append('Could not find function')
    return True, tmsg

  def printexported(self, item, tfunction):
    """
    return a list of strings that describe a function
    """
    tmsg = []
    tmsg.append('Function: %s' % (item))
    if tfunction.__doc__:
      tlist = tfunction.__doc__.strip().split('\n')
      for i in tlist:
        tmsg.append('  %s' % i)
    return tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List plugins
      @CUsage@w: list
    """
    msg = []
    if len(args) > 0:
      #TODO: check for the name here
      pass
    else:
      tkeys = self.plugins.keys()
      tkeys.sort()
      msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                          ('Short Name', 'Name', 'Author', 'Vers', 'Purpose'))
      msg.append('-' * 75)
      for plugin in tkeys:
        tpl = self.plugins[plugin]
        msg.append("%-10s : %-25s %-10s %-5s %s@w" % \
                    (plugin, tpl.name, tpl.author, tpl.version, tpl.purpose))
    return True, msg

  def cmd_load(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Load a plugin
      @CUsage@w: load @Yplugin@w
        @Yplugin@w    = the name of the plugin to load
               use the name without the .py
    """
    tmsg = []
    if len(args) == 1:
      basepath = ''
      index = __file__.rfind(os.sep)
      if index == -1:
        basepath = "." + os.sep
      else:
        basepath = __file__[:index]

      fname = args[0].replace('.', os.sep)
      _module_list = find_files( basepath, fname + ".py")

      if len(_module_list) > 1:
        tmsg.append('There is more than one module that matches: %s' % \
                                                              args[0])
      elif len(_module_list) == 0:
        tmsg.append('There are no modules that match: %s' % args[0])
      else:
        sname, reason = self.load_module(_module_list[0], basepath, True)
        if sname:
          if reason == 'already':
            tmsg.append('Module %s is already loaded' % sname)
          else:
            tmsg.append('Load complete: %s - %s' % \
                                          (sname, self.plugins[sname].name))
        else:
          tmsg.append('Could not load: %s' % args[0])
      return True, tmsg
    else:
      return False, tmsg

  def cmd_unload(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      unload a plugin
      @CUsage@w: unload @Yplugin@w
        @Yplugin@w    = the shortname of the plugin to load
    """
    tmsg = []
    if len(args) == 1 and args[0] in self.plugins:
      if self.plugins[args[0]].canreload:
        if self.unload_module(self.plugins[args[0]].fullimploc):
          tmsg.append("Unloaded: %s" % args[0])
        else:
          tmsg.append("Could not unload:: %s" % args[0])
      else:
        tmsg.append("That plugin can not be unloaded")
      return True, tmsg

    return False

  def cmd_reload(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      reload a plugin
      @CUsage@w: reload @Yplugin@w
        @Yplugin@w    = the shortname of the plugin to reload
    """
    tmsg = []
    if len(args) == 0:
      return True, ['Please specify a plugin']

    if args[0] and args[0] in self.plugins:
      if self.plugins[args[0]].canreload:
        tret, _ = self.reload_module(args[0], True)
        if tret and tret != True:
          tmsg.append("Reload complete: %s" % self.plugins[tret].fullimploc)
          return True, tmsg
      else:
        tmsg.append("That plugin cannot be reloaded")
        return True, tmsg
    else:
      tmsg.append("That plugin does not exist")
      return True, tmsg

  def load_modules(self, tfilter):
    """
    load modules in all directories under plugins
    """
    index = __file__.rfind(os.sep)
    if index == -1:
      basepath = "." + os.sep
    else:
      basepath = __file__[:index]

    _module_list = find_files( basepath, tfilter)
    _module_list.sort()

    for fullname in _module_list:
      force = False
      if fullname in self.loadedplugins:
        force = True
      self.load_module(fullname, basepath, force)

  def load_module(self, fullname, basepath, force=False):
    """
    load a single module
    """
    imploc, modname = get_module_name(basepath, fullname)

    if modname.startswith("_"):
      return False, 'dev'

    try:
      if imploc == '.':
        fullimploc = "plugins" + imploc + modname
      else:
        fullimploc = "plugins" + imploc + '.' + modname
      if fullimploc in sys.modules:
        return sys.modules[fullimploc].SNAME, 'already'

      self.api.get('output.msg')('importing %s' % fullimploc, self.sname)
      _module = __import__(fullimploc)
      _module = sys.modules[fullimploc]
      load = True

      if 'AUTOLOAD' in _module.__dict__ and not force:
        if not _module.AUTOLOAD:
          load = False
      elif not ('AUTOLOAD' in _module.__dict__):
        load = False

      if load:
        if "Plugin" in _module.__dict__:
          self.add_plugin(_module, fullname, basepath, fullimploc)

        else:
          self.api.get('output.msg')('Module %s has no Plugin class' % \
                                              _module.NAME, self.sname)

        _module.__dict__["proxy_import"] = 1
        self.api.get('output.client')("load: loaded %s" % fullimploc)
        self.api.get('output.msg')('loaded %s' % fullimploc, self.sname)

        return _module.SNAME, 'Loaded'
      else:
        if fullimploc in sys.modules:
          del sys.modules[fullimploc]
        self.api.get('output.msg')('Not loading %s (%s) because autoload is False' % \
                                    (_module.NAME, fullimploc), self.sname)
      return True, 'not autoloaded'
    except:
      if fullimploc in sys.modules:
        del sys.modules[fullimploc]

      self.api.get('output.traceback')("Module '%s' refuses to load." % fullimploc)
      return False, 'error'

  def unload_module(self, fullimploc):
    """
    unload a module
    """
    if fullimploc in sys.modules:

      _module = sys.modules[fullimploc]
      _oldmodule = _module
      try:
        if "proxy_import" in _module.__dict__:

          if "unload" in _module.__dict__:
            try:
              _module.unload()
            except:
              self.api.get('output.traceback')(
                    "unload: module %s didn't unload properly." % fullimploc)

          if not self.remove_plugin(_module.SNAME):
            self.api.get('output.client')('could not remove plugin %s' % fullimploc)

        del sys.modules[fullimploc]
        self.api.get('output.client')("unload: unloaded %s." % fullimploc)

      except:
        self.api.get('output.traceback')(
                      "unload: had problems unloading %s." % fullimploc)
        return False
    else:
      _oldmodule = None

    return True

  def reload_module(self, modname, force=False):
    """
    reload a module
    """
    if modname in self.plugins:
      plugin = self.plugins[modname]
      fullimploc = plugin.fullimploc
      basepath = plugin.basepath
      fullname = plugin.fullname
      plugin = None
      if not self.unload_module(fullimploc):
        return False, ''

      if fullname and basepath:
        return self.load_module(fullname, basepath, force)

    else:
      return False, ''

  def add_plugin(self, module, fullname, basepath, fullimploc):
    """
    add a plugin to be managed
    """
    module.__dict__["lyntin_import"] = 1
    plugin = module.Plugin(module.NAME, module.SNAME,
                                    fullname, basepath, fullimploc)
    plugin.author = module.AUTHOR
    plugin.purpose = module.PURPOSE
    plugin.version = module.VERSION
    if plugin.name in self.pluginl:
      self.api.get('output.msg')('Plugin %s already exists' % plugin.name, self.sname)
      return False
    if plugin.sname in self.plugins:
      self.api.get('output.msg')('Plugin %s already exists' % plugin.sname, self.sname)
      return False

    #check dependencies here
    self.loaddependencies(plugin.sname, plugin.dependencies)

    plugin.load()
    self.pluginl[plugin.name] = plugin
    self.plugins[plugin.sname] = plugin
    self.pluginm[plugin.name] = module
    self.loadedplugins[fullname] = True
    self.loadedplugins.sync()
    return True

  def remove_plugin(self, pluginname):
    """
    remove a plugin
    """
    plugin = None
    if pluginname in self.plugins:
      plugin = self.plugins[pluginname]
      plugin.unload()
      del self.plugins[plugin.sname]
      del self.pluginl[plugin.name]
      del self.pluginm[plugin.name]
      del self.loadedplugins[plugin.fullname]
      self.loadedplugins.sync()
      plugin = None
      return True
    else:
      return False

  def savestate(self):
    """
    save all plugins
    """
    for i in self.plugins:
      self.plugins[i].savestate()

  def load(self):
    """
    load various things
    """
    self.api.get('managers.add')('plugin', self)
    self.load_modules("*.py")
    self.api.get('commands.add')(self.sname, 'list', {'lname':'Plugin Manager',
                          'func':self.cmd_list, 'shelp':'List plugins'})
    self.api.get('commands.add')(self.sname, 'load', {'lname':'Plugin Manager',
                          'func':self.cmd_load, 'shelp':'Load a plugin'})
    self.api.get('commands.add')(self.sname, 'unload', {'lname':'Plugin Manager',
                          'func':self.cmd_unload, 'shelp':'Unload a plugin'})
    self.api.get('commands.add')(self.sname, 'reload', {'lname':'Plugin Manager',
                          'func':self.cmd_reload, 'shelp':'Reload a plugin'})
    #self.api.get('commands.add')(self.sname, 'exported', {'lname':'Plugin Manager',
                          #'func':self.cmd_exported,
                          #'shelp':'Examine the exported module'})
    self.api.get('commands.default')(self.sname, 'list')
    self.api.get('events.register')('savestate', self.savestate, plugin=self.sname)

