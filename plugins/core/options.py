"""
$Id$

This module holds the class that manages Telnet Options as well as an
instance of the class
"""

import glob
import os
import sys

from plugins._baseplugin import BasePlugin

NAME = 'Option Handler'
SNAME = 'options'
PURPOSE = 'Handle Telnet Options'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 7

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to manage telnet options
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.canreload = False

    self.options = {}
    self.optionsmod = {}

    self.api.get('managers.add')(self.sname, self)

  def load(self):
    """
    load the module
    """
    BasePlugin.load(self)
    self.api.get('events.register')('plugin_loaded', self.plugin_loaded)
    self.api.get('log.console')(self.sname)
    
  def plugin_loaded(self, args):
    """
    check to see if this plugin has SERVER and CLIENT
    """
    plugin = args['plugin']
    module = self.api.get('plugins.module')(plugin)

    try:
      module.SERVER
      self.options[plugin] = True
      self.optionsmod[plugin] = module
      self.api.get('output.msg')('adding %s as a telnet option' % plugin,
                                        secondary=plugin)
    except AttributeError:
      pass

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

