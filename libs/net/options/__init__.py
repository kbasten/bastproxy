"""
$Id$

This will manage Telnet Options
"""

import glob, os, sys

from libs import exported

def get_module_name(filename):
  path, filename = os.path.split(filename)
  return os.path.splitext(filename)[0]

class TelnetOptionMgr:
  def __init__(self):
    self.options = {}
    self.optionsmod = {}
    self.load_options()

  def load_options(self):
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
        name = "libs.net.options." + mem2
        _module = __import__(name)
        _module = sys.modules[name]
          
        if _module.__dict__.has_key("Plugin"):
           exported.pluginMgr.add_plugin(_module.Plugin(_module.name, _module.sname,  mem, path, name))            

        if _module.__dict__.has_key("load"):
          _module.load()
          
        _module.__dict__["proxy_import"] = 1
        self.options[name] = True
        self.optionsmod[name] = _module
        
      except:
        exported.write_traceback("Option module '%s' refuses to load." % name)
        
  def reloadmod(self, mod):
    exported.processevent('OPTRELOAD', {'option':mod})
  
  def addtoclient(self, client):
    for i in self.options:
      try:
        self.optionsmod[i].CLIENT(client)
      except AttributeError:
        print('Did not add option:', i)
        
  def addtoserver(self, server):
    for i in self.options:
      try:
        self.optionsmod[i].SERVER(server)
      except AttributeError:
        print('Did not add option:', i)
  
  def resetoptions(self, server, onclose=False):
    print('resetoptions')
    for i in server.option_handlers:
      if i in server.options:
        print('resetting option', i)
        server.option_handlers[i].reset(onclose)          
      
        
toptionMgr = TelnetOptionMgr()
