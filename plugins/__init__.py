"""
$Id$
"""

import glob, os, sys

from libs import exported
from libs.fileutils import find_files


def get_module_name(path, filename):
  filename = filename.replace(path, "")
  path, filename = os.path.split(filename)
  tpath = path.split(os.sep)
  path = '.'.join(tpath)
  return path, os.path.splitext(filename)[0]


class BasePlugin:
  def __init__(self, name, sname, filename, directory, importloc):
    self.author = ''
    self.purpose = ''
    self.version = 0
    self.name = name
    self.sname = sname
    self.filename = filename
    self.directory = directory
    self.importloc = importloc
    
  def load(self):
    pass
  
  def unload(self):
    pass

  def addCmd(self, cmd, tfunc, shelp=None):
    exported.cmdMgr.addCmd(self.sname, self.name, cmd, tfunc, shelp)
    
  def setDefaultCmd(self, name):
    exported.cmdMgr.setDefault(self.sname, name)
  

class PluginMgr:
  def __init__(self):
    self.plugins = {}
    self.pluginl = {}
    self.pluginm = {}
    self.load_modules()
    exported.cmdMgr.addCmd('plugins', 'Plugin Manager', 'list', self.cmd_list, 'List Plugins')

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
    pass

  def load_modules(self):
    index = __file__.rfind(os.sep)
    if index == -1:
      path = "." + os.sep
    else:
      path = __file__[:index]

    
    _module_list = find_files( path, "*.py")
    _module_list.sort()

    for mem in _module_list:
      # we skip over all files that start with a _
      # this allows hackers to be working on a module and not have
      # it die every time.
      impl, iname = get_module_name(path, mem)
      
      if iname.startswith("_"):
        continue

      try:
        if impl == '.':
          name = "plugins" + impl + iname          
        else:
          name = "plugins" + impl + '.' + iname
        print 'importing name', name
        _module = __import__(name)
        _module = sys.modules[name]
        load = True

        if _module.__dict__.has_key("autoload"):
          if not _module.autoload:          
            load = False
        
        if load:
          if _module.__dict__.has_key("Plugin"):
            self.add_plugin(_module, mem, path, name)

          else:
            print('Module %s has no Plugin class', _module.name)

          _module.__dict__["proxy_import"] = 1
        else:
          print('Not loading %s (%s) because autoload is False' % (_module.name, iname)) 
      except:
        exported.write_traceback("Module '%s' refuses to load." % name)

  def cmd_load(self, args):
    pass
  
  def cmd_reload(self, args):
    pass

  def reload_module(self, modname):
    mod = ''
    plugin = None
    
    if modname in self.sname:
      plugin = self.plugins[modname]  
      mod = plugin.importloc
      del self,plugins[plugin.sname]
      del self.pluginl[plugin.name]
      del self.pluginm[plugin.name]
    else:
      return False
    
    if sys.modules.has_key(mod):

      _module = sys.modules[mod]
      _oldmodule = _module
      try:
        if _module.__dict__.has_key("lyntin_import"):
          # if we're told not to reload it, we toss up a message and then
          # do nothing
          if not reload:
            exported.write_message("load: module %s has already been loaded." % mod)
            return

          # if we loaded it via a lyntin_import mechanism and it has an
          # unload method, then we try calling that
          if _module.__dict__.has_key("unload"):
            try:
              _module.unload()
            except:
              exported.write_traceback("load: module %s didn't unload properly." % mod)
        del sys.modules[mod]
        exported.write_message("load: reloading %s." % mod)

      except:
        exported.write_traceback("load: had problems unloading %s." % mod)
        return
    else:
      _oldmodule = None


    # here's where we import the module
    try:
      _module = __import__( mod )
      _module = sys.modules[mod]

      if (_oldmodule and _oldmodule.__dict__.has_key("reload")):
        try:
          _oldmodule.reload()
        except:
          exported.write_traceback("load: had problems calling reload on %s." % mod)
      
      if (_module.__dict__.has_key("load")):
        _module.load()

      _module.__dict__["lyntin_import"] = 1
      exported.write_message("load successful.")
      if mod not in config.lyntinmodules:
        config.lyntinmodules.append(mod)

    except:
      exported.write_traceback("load: had problems with %s." % mod)
  
  def add_plugin(self, module, mem, path, name):
    module.__dict__["lyntin_import"] = 1    
    plugin = module.Plugin(module.name, module.sname, mem, path, name)
    plugin.author = module.author
    plugin.purpose = module.purpose
    plugin.version = module.version    
    if plugin.name in self.pluginl:
      print('Plugin %s already exists' % plugin.name)
      return
    if plugin.sname in self.plugins:
      print('Plugin %s already exists' % plugin.sname)
      return
    
    plugin.load()
    self.pluginl[plugin.name] = plugin
    self.plugins[plugin.sname] = plugin
    self.pluginm[plugin.name] = module

  def remove_plugin(self, pluginname):
    plugin = None
    if pluginname in self.plugins:
      plugin = self.plugins[pluginname]

    if plugin:
      plugin.unload()
      del(self.plugins[pluginname])
      
      