"""
$Id$
"""

import glob, os, sys

from libs import exported
from libs.fileutils import find_files
import inspect


def get_module_name(path, filename):
  filename = filename.replace(path, "")
  path, filename = os.path.split(filename)
  tpath = path.split(os.sep)
  path = '.'.join(tpath)
  return path, os.path.splitext(filename)[0]


class BasePlugin:
  def __init__(self, name, sname, fullname, basepath, fullimploc):
    self.author = ''
    self.purpose = ''
    self.version = 0
    self.name = name
    self.sname = sname
    self.canreload = True
    self.fullname = fullname
    self.basepath = basepath
    self.fullimploc = fullimploc
    
    self.cmds = {}
    self.defaultcmd = ''
    self.variables = {}
    self.events = []
    self.timers = {}
    
  def load(self):
    # load all commands
    for i in self.cmds:
      self.addCmd(i, self.cmds[i]['func'], self.cmds[i]['shelp'])
      
    # if there is a default command, then set it
    if self.defaultcmd:
      self.setDefaultCmd(self.defaultcmd)
      
    # register all events
    for i in self.events:
      exported.registerevent(i['event'], i['func'])
      
    # register all timers
    for i in self.timers:
      tim = self.timers[i]
      exported.addtimer(i, tim['func'], tim['seconds'], tim['onetime'])
  
  def unload(self):
    'clear all commands for this plugin from cmdMgr'
    exported.cmdMgr.resetPluginCmds(self.sname)

    # unregister all events
    for i in self.events:
      exported.unregisterevent(i['event'], i['func'])

    # delete all timers
    for i in self.timers:
      exported.deletetimer(i)


  def addCmd(self, cmd, tfunc, shelp=None):
    exported.cmdMgr.addCmd(self.sname, self.name, cmd, tfunc, shelp)
    
  def setDefaultCmd(self, name):
    exported.cmdMgr.setDefault(self.sname, name)
  

class PluginMgr:
  def __init__(self):
    self.plugins = {}
    self.pluginl = {}
    self.pluginm = {}
    self.load_modules("*.py")
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'list', self.cmd_list, 'List plugins')
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'load', self.cmd_load, 'Load a plugin')
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'unload', self.cmd_unload, 'Unload a plugin')
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'reload', self.cmd_reload, 'Reload a plugin')
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'exported', self.cmd_exported, 'Examine the exported module')
    exported.cmdMgr.setDefault('plugins', 'list')

  def cmd_exported(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  see what functions are available to the exported module
  useful for finding out what can be gotten for scripting
  @CUsage@w: exported
---------------------------------------------------------------"""
    if len(args) == 0:
      exported.sendtouser('Items available in exported')
      for i in dir(exported):
        if not (i in ['sys', 'traceback', '__builtins__', '__doc__', '__file__', '__name__', '__package__',]):
          if inspect.isfunction(exported.__dict__[i]):
            exported.sendtouser('Function: %s' % i)
          elif isinstance(exported.__dict__[i], dict):
            for t in exported.__dict__[i]:
              exported.sendtouser('Function: %s.%s' % (i,t))
    else:
      i = args[0]
      if i in dir(exported):
        if inspect.isfunction(exported.__dict__[i]):
          self.printexported(i, exported.__dict__[i])
        elif isinstance(exported.__dict__[i], dict):
          for t in exported.__dict__[i]:
            self.printexported('%s.%s' % (i,t), exported.__dict__[i][t])
    return True
    
  def printexported(self, item, tfunction):
    exported.sendtouser('Function: %s' % (item))
    if tfunction.__doc__:
      tlist = tfunction.__doc__.split('\n')
      for i in tlist:
        exported.sendtouser('  %s' % i)    
    
  def cmd_list(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  List plugins
  @CUsage@w: list
---------------------------------------------------------------"""
    tstr = 'Plugins:\n\r'
    tstr = tstr + "%-10s : %-20s %-10s %-5s %s@w\n\r" % ('Short Name', 'Name', 'Author', 'Vers', 'Purpose')    
    tstr = tstr + '-' * 75 + '\n\r'    
    for plugin in self.plugins:
      tpl = self.plugins[plugin]
      tstr = tstr + "%-10s : %-20s %-10s %-5s %s@w\n\r" % (plugin, tpl.name, tpl.author, tpl.version, tpl.purpose)
    tstr = tstr + '-' * 75
    exported.sendtouser(tstr)
    return True
    
  def cmd_load(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Load a plugin
  @CUsage@w: load @Yplugin@w
    @Yplugin@w    = the name of the plugin to load
               use the name without the .py    
---------------------------------------------------------------"""      
    if len(args) == 1:
      basepath = ''
      index = __file__.rfind(os.sep)
      if index == -1:
        basepath = "." + os.sep
      else:
        basepath = __file__[:index]      
        
      _module_list = find_files( basepath, args[0] + ".py")
      
      if len(_module_list) > 1:
        exported.sendtouser('There is more than one module that matches: %s' % args[0])
      elif len(_module_list) == 0:
        exported.sendtouser('There are no modules that match: %s' % args[0])        
      else:
        sname = self.load_module(_module_list[0], basepath, True)
        if sname:
          exported.sendtouser('Load complete: %s - %s' % (sname, self.plugins[sname].name))
        else:
          exported.sendtouser('Could not load: %s' % args[0])
      return True
    else:
      return False

  def cmd_unload(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  unload a plugin
  @CUsage@w: unload @Yplugin@w
    @Yplugin@w    = the shortname of the plugin to load
---------------------------------------------------------------"""    
    if len(args) == 1 and args[0] in self.plugins:
      if self.plugins[args[0]].canreload:
        if self.unload_module(self.plugins[args[0]].fullimploc):
          exported.sendtouser("Unloaded: %s" % args[0])
        else:
          exported.sendtouser("Could not unload:: %s" % args[0])
      else:
        exported.sendotouser("That plugin can not be unloaded")
      return True
      
    return False

  def cmd_reload(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  reload a plugin
  @CUsage@w: reload @Yplugin@w
    @Yplugin@w    = the shortname of the plugin to reload
---------------------------------------------------------------"""       
    if args[0] and args[0] in self.plugins:
      if self.plugins[args[0]].canreload:
        tret = self.reload_module(args[0])
        if tret and tret != True:
          exported.sendtouser("Reload complete: %s" % self.plugins[tret].fullimploc)
          return True
      else:
        exported.sendtouser("That plugin cannot be reloaded")
        return True
    else:
      exported.sendtouser("That plugin does not exist")
      return True

  def load_modules(self, filter):
    index = __file__.rfind(os.sep)
    if index == -1:
      basepath = "." + os.sep
    else:
      basepath = __file__[:index]
    
    _module_list = find_files( basepath, filter)
    _module_list.sort()

    for fullname in _module_list:
      # we skip over all files that start with a _
      # this allows hackers to be working on a module and not have
      # it die every time.
      self.load_module(fullname, basepath)

  def load_module(self, fullname, basepath, fromcmd=False):
    imploc, modname = get_module_name(basepath, fullname)
    
    if modname.startswith("_") and not fromcmd:
      return False

    try:
      if imploc == '.':
        fullimploc = "plugins" + imploc + modname          
      else:
        fullimploc = "plugins" + imploc + '.' + modname
      print 'loading', fullimploc
      _module = __import__(fullimploc)
      _module = sys.modules[fullimploc]
      load = True

      if _module.__dict__.has_key("autoload") and not fromcmd:
        if not _module.autoload:          
          load = False
      
      if load:
        if _module.__dict__.has_key("Plugin"):
          self.add_plugin(_module, fullname, basepath, fullimploc)

        else:
          print('Module %s has no Plugin class', _module.name)

        _module.__dict__["proxy_import"] = 1
        exported.write_message("load: loaded %s" % fullimploc)
        
        return _module.sname
      else:
        print('Not loading %s (%s) because autoload is False' % (_module.name, fullimploc)) 
      return True
    except:
      exported.write_traceback("Module '%s' refuses to load." % fullimploc)
      return False
     
  def unload_module(self, fullimploc):
    if sys.modules.has_key(fullimploc):
      
      _module = sys.modules[fullimploc]
      _oldmodule = _module
      try:
        if _module.__dict__.has_key("proxy_import"):
          
          if _module.__dict__.has_key("unload"):
            try:
              _module.unload()
            except:
              exported.write_traceback("unload: module %s didn't unload properly." % fullimploc)
          
          if not self.remove_plugin(_module.sname):
            exported.write_message('could not remove plugin %s' % fullimploc)
          
        del sys.modules[fullimploc]
        exported.write_message("unload: unloaded %s." % fullimploc)

      except:
        exported.write_traceback("unload: had problems unloading %s." % fullimploc)
        return False
    else:
      _oldmodule = None
      
    return True

  def reload_module(self, modname):
    if modname in self.plugins:
      plugin = self.plugins[modname]  
      fullimploc = plugin.fullimploc
      basepath = plugin.basepath
      fullname = plugin.fullname
      plugin = None
      if not self.unload_module(fullimploc):
        return False

      if fullname and basepath:
        return self.load_module(fullname, basepath)

    else:
      return False
  
  def add_plugin(self, module, fullname, basepath, fullimploc):
    module.__dict__["lyntin_import"] = 1    
    plugin = module.Plugin(module.name, module.sname, fullname, basepath, fullimploc)
    plugin.author = module.author
    plugin.purpose = module.purpose
    plugin.version = module.version    
    if plugin.name in self.pluginl:
      print('Plugin %s already exists' % plugin.name)
      return False
    if plugin.sname in self.plugins:
      print('Plugin %s already exists' % plugin.sname)
      return False
    
    plugin.load()
    self.pluginl[plugin.name] = plugin
    self.plugins[plugin.sname] = plugin
    self.pluginm[plugin.name] = module
    return True

  def remove_plugin(self, pluginname):
    plugin = None
    if pluginname in self.plugins:
      plugin = self.plugins[pluginname]
      plugin.unload()
      del self.plugins[plugin.sname]
      del self.pluginl[plugin.name]
      del self.pluginm[plugin.name]      
      plugin = None      
      return True
    else:
      return False

      