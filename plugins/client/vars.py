"""
$Id$

This plugin is a variable plugin

"""
import os
import argparse
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
  a plugin to handle global variables, if something goes through
   send.execute (this includes from the client), a variable
   can be specified with $varname and will be substituted.
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

    self.variablefile = os.path.join(self.savedir, 'variables.txt')
    self._variables = PersistentDict(self.variablefile, 'c')
    self.api.get('api.add')('getv', self.api_getv)
    self.api.get('api.add')('setv', self.api_setv)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='add a variable')
    parser.add_argument('name', help='the name of the variable',
                        default='', nargs='?')
    parser.add_argument('value', help='the value of the variable',
                        default='', nargs='?')
    self.api.get('commands.add')('add', self.cmd_add,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='remove a variable')
    parser.add_argument('name', help='the variable to remove',
                        default='', nargs='?')
    self.api.get('commands.add')('remove', self.cmd_remove,
                                 parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='list variables')
    parser.add_argument('match',
              help='list only variables that have this argument in their name',
              default='', nargs='?')
    self.api.get('commands.add')('list', self.cmd_list,
                                 parser=parser)

    self.api.get('commands.default')('add')
    self.api.get('events.register')('from_client_event', self.checkvariable,
                                        prio=1)
    self.api.get('events.register')('from_client_event', self.checkvariable,
                                        prio=99)

  def api_getv(self, varname):
    """  get the variable with a specified name
    @Yvarname@w  = the variable to get

    this function returns the value of variable with the name of the argument
    """
    if varname in self._variables:
      return self._variables[varname]

    return None

  def api_setv(self, varname, value):
    """  set the variable with a specified name to the specified value
    @Yvarname@w  = the variable to get
    @Yvalue@w  = the value to set

    this function returns True if the value was set, False if an error was
    encountered
    """
    try:
      self._variables[varname] = value
      return True
    except:
      return False

  def checkvariable(self, args):
    """
    this function checks for variables in input
    """
    data = args['fromdata'].strip()

    templ = Template(data)
    datan = templ.safe_substitute(self._variables)
    if datan != data:
      self.api.get('send.msg')('replacing "%s" with "%s"' % (data.strip(),
                                                             datan.strip()))
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
    if args['name'] and args['value']:
      tmsg.append("@GAdding variable@w : '%s' will be replaced by '%s'" % \
                                              (args['name'], args['value']))
      self.addvariable(args['name'], args['value'])
      return True, tmsg
    else:
      tmsg.append("@RPlease include all arguments@w")
      return False, tmsg

  def cmd_remove(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Remove a variable
      @CUsage@w: rem @Y<originalstring>@w
        @Yoriginalstring@w    = The original string
    """
    tmsg = []
    if args['name']:
      tmsg.append("@GRemoving variable@w : '%s'" % (args['name']))
      self.removevariable(args['name'])
      return True, tmsg
    else:
      return False, ['@RPlease specifiy a variable to remove@w']

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List variables
      @CUsage@w: list
    """
    tmsg = self.listvariables(args['match'])
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

  def listvariables(self, match):
    """
    return a table of variables
    """
    tmsg = []
    for item in self._variables:
      if not match or match in item:
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
