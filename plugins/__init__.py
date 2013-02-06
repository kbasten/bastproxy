"""
$Id$
"""

import glob, os, sys

from libs import exported

def get_module_name(filename):
  path, filename = os.path.split(filename)
  return os.path.splitext(filename)[0]


class BasePlugin:
  def __init__(self, name, sname, filename, directory, importloc):
    self.name = name
    self.sname = sname
    self.filename = filename
    self.directory = directory
    self.importloc = importloc
    
  def load(self):
    pass
  
  def unload(self):
    pass


class PluginMgr:
  def __init__(self):
    self.plugins = {}
    self.load_modules()

  def load_modules(self):
    index = __file__.rfind(os.sep)
    if index == -1:
      path = "." + os.sep
    else:
      path = __file__[:index]

    _module_list = glob.glob( os.path.join(path, "*.py"))
    _module_list.sort()

    for mem in _module_list:
      # we skip over all files that start with a _
      # this allows hackers to be working on a module and not have
      # it die every time.
      mem2 = get_module_name(mem)
      if mem2.startswith("_"):
        continue

      try:
        name = "plugins." + mem2
        _module = __import__(name)
        _module = sys.modules[name]
        load = True

        if _module.__dict__.has_key("autoload"):
          if not _module.autoload:          
            load = False
        
        if load:
          if _module.__dict__.has_key("Plugin"):
            self.add_plugin(_module.Plugin(_module.name, _module.sname, mem, path, name))
          else:
            print('Module %s has no Plugin class', _module.name)

          _module.__dict__["proxy_import"] = 1
        else:
          print('Not loading %s (%s) because autoload is False' % (_module.name, mem2)) 
      except:
        exported.write_traceback("Module '%s' refuses to load." % name)

  def reload_module(self, module):
    pass
  
  def add_plugin(self, plugin):
    if plugin.name in self.plugins:
      print('Plugin %s already exists' % plugin.name)
    if plugin.sname in self.plugins:
      print('Plugin %s already exists' % plugin.sname)
      
    plugin.load()
    self.plugins[plugin.name] = plugin
    self.plugins[plugin.sname] = plugin

  def remove_plugin(self, pluginname):
    plugin = None
    if pluginname in self.plugins:
      plugin = self.plugins[pluginname]

    if plugin:
      plugin.unload()
      del(self.plugins[pluginname])
      
      