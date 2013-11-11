"""
$Id$

This plugin is an variable plugin

TODO: add api for get, set, etc
"""
import os
import re
from string import Template
from plugins._baseplugin import BasePlugin
from libs.persistentdict import PersistentDict

#these 5 are required
NAME = 'Variables'
SNAME = 'vars'
PURPOSE = 'create variables'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 25

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to do simple substitution
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.variablefile = os.path.join(self.savedir, 'variables.txt')
    self._variables = PersistentDict(self.variablefile, 'c', format='json')

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('commands.add')('add', self.cmd_add,
                                 shelp='Add an variable')
    self.api.get('commands.add')('remove', self.cmd_remove,
                                 shelp='Remove an variable')
    self.api.get('commands.add')('list', self.cmd_list,
                                 shelp='List variables')
    self.api.get('commands.default')('add')
    self.api.get('events.register')('from_client_event', self.checkvariable, prio=99)

  def checkvariable(self, args):
    """
    this function finds subs in mud data
    """
    data = args['fromdata'].strip()

    templ = Template(data)
    datan = templ.safe_substitute(self._variables)
    if datan != data:
      self.api.get('output.msg')('replacing "%s" with "%s"' % (data.strip(), datan.strip()))
      args['fromdata'] = datan
    return args

  def cmd_add(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Add a variable
      @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
        @Yoriginalstring@w    = The original string to be replaced
        @Mreplacementstring@w = The new string
    """
    tmsg = []
    if len(args) == 2 and args[0] and args[1]:
      tmsg.append("@GAdding variable@w : '%s' will be replaced by '%s'" % \
                                              (args[0], args[1]))
      self.addvariable(args[0], args[1])
      return True, tmsg
    else:
      tmsg.append("@RWrong number of arguments")
      return False, tmsg

  def cmd_remove(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Remove a variable
      @CUsage@w: rem @Y<originalstring>@w
        @Yoriginalstring@w    = The original string
    """
    tmsg = []
    if len(args) > 0 and args[0]:
      tmsg.append("@GRemoving variable@w : '%s'" % (args[0]))
      self.removevariable(args[0])
      return True, tmsg
    else:
      return False, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List variables
      @CUsage@w: list
    """
    if len(args) >= 1:
      return False, []
    else:
      tmsg = self.listvariables()
      return True, tmsg

  def addvariable(self, item, value):
    """
    internally add a variable
    """
    self._variables[item] = value
    self._variables.sync()

  def removevariable(self, item):
    """
    internally remove a variable
    """
    if item in self._variables:
      del self._variables[item]
      self._variables.sync()

  def listvariables(self):
    """
    return a table of strings that list subs
    """
    tmsg = []
    for item in self._variables:
      tmsg.append("%-20s : %s@w" % (item, self._variables[item]))
    if len(tmsg) == 0:
      tmsg = ['None']
    return tmsg

  def clearvariables(self):
    """
    clear all subs
    """
    self._variables.clear()
    self._variables.sync()

  def reset(self):
    """
    reset the plugin
    """
    BasePlugin.reset(self)
    self.clearvariables()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self._variables.sync()
