"""
$Id$

This module holds the class that manages Telnet Options as well as an
instance of the class
"""

import glob
import os
import sys

from libs.api import API

def get_module_name(filename):
  """
  get a module path given a filename
  """
  _, filename = os.path.split(filename)
  return os.path.splitext(filename)[0]

class TelnetOptionMgr(object):
  """
  a class to manage telnet options
  """
  def __init__(self):
    """
    initialize the instance
    """
    self.api = API()
    self.api.get('managers.add')('telopt', self)
    self.options = {}
    self.optionsmod = {}
    self.load_options()
    self.api.get('log.adddtype')('telopt')

  def load_options(self):
    """
    load all options
    """
    pluginmgr = self.api.get('managers.getm')('plugin')
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

        if "Plugin" in _module.__dict__:
          pluginmgr.add_plugin(_module, mem2, path, name)

        if "load" in _module.__dict__:
          _module.load()

        _module.__dict__["proxy_import"] = 1
        self.options[name] = True
        self.optionsmod[name] = _module

      except:
        self.api.get('output.traceback')("Option module '%s' refuses to load." % name)

  def reloadmod(self, mod):
    """
    reload a module
    """
    self.api.get('events.eraise')('OPTRELOAD', {'option':mod})

  def addtoclient(self, client):
    """
    add an option to a client
    """
    for i in self.options:
      try:
        self.optionsmod[i].CLIENT(client)
      except AttributeError:
        self.api.get('output.msg')('Did not add option to client: %s' % i, 'telopt')

  def addtoserver(self, server):
    """
    add an option to a server
    """
    for i in self.options:
      try:
        self.optionsmod[i].SERVER(server)
      except AttributeError:
        self.api.get('output.msg')('Did not add option to server: %s' % i, 'telopt')

  def resetoptions(self, server, onclose=False):
    """
    reset options
    """
    for i in server.option_handlers:
      if i in server.options:
        server.option_handlers[i].reset(onclose)


TELOPTMGR = TelnetOptionMgr()
