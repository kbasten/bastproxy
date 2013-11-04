"""
$Id$

This plugin is a simple substition plugin
"""
import os
from libs import color
from plugins._baseplugin import BasePlugin
from libs.persistentdict import PersistentDict

#these 5 are required
NAME = 'Simple Substitute'
SNAME = 'ssub'
PURPOSE = 'simple substitution of strings'
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
    self.savesubfile = os.path.join(self.savedir, 'subs.txt')
    self._substitutes = PersistentDict(self.savesubfile, 'c', format='json')

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('commands.add')('add', self.cmd_add,
                                 shelp='Add a substitute')
    self.api.get('commands.add')('remove', self.cmd_remove,
                                 shelp='Remove a substitute')
    self.api.get('commands.add')('list', self.cmd_list,
                                 shelp='List substitutes')
    self.api.get('commands.add')('clear', self.cmd_clear,
                                 shelp='Clear all substitutes')
    self.api.get('commands.default')('list')
    self.api.get('events.register')('to_client_event', self.findsub)

  def findsub(self, args):
    """
    this function finds subs in mud data
    """
    data = args['todata']
    dtype = args['dtype']
    if dtype != 'fromproxy':
      for mem in self._substitutes.keys():
        if mem in data:
          data = data.replace(mem,
                    color.convertcolors(self._substitutes[mem]['sub']))
      args['todata'] = data
      return args

  def cmd_add(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Add a substitute
      @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
        @Yoriginalstring@w    = The original string to be replaced
        @Mreplacementstring@w = The new string
    """
    tmsg = []
    if len(args) == 2 and args[0] and args[1]:
      tmsg.append("@GAdding substitute@w : '%s' will be replaced by '%s'" % \
                                              (args[0], args[1]))
      self.addsub(args[0], args[1])
      return True, tmsg
    else:
      tmsg.append("@RWrong number of arguments")
      return False, tmsg

  def cmd_remove(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      Remove a substitute
      @CUsage@w: rem @Y<originalstring>@w
        @Yoriginalstring@w    = The original string
    """
    tmsg = []
    if len(args) > 0 and args[0]:
      tmsg.append("@GRemoving substitute@w : '%s'" % (args[0]))
      self.removesub(args[0])
      return True, tmsg
    else:
      return False, tmsg

  def cmd_list(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List substitutes
      @CUsage@w: list
    """
    if len(args) >= 1:
      return False, []
    else:
      tmsg = self.listsubs()
      return True, tmsg

  def cmd_clear(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      List substitutes
      @CUsage@w: list"""
    if len(args) > 0:
      #TODO check for subs that match args and remove them
      pass
    else:
      self.clearsubs()
    return True, ['Substitutes cleared']

  def addsub(self, item, sub):
    """
    internally add a substitute
    """
    self._substitutes[item] = {'sub':sub}
    self._substitutes.sync()

  def removesub(self, item):
    """
    internally remove a substitute
    """
    if item in self._substitutes:
      del self._substitutes[item]
      self._substitutes.sync()

  def listsubs(self):
    """
    return a table of strings that list subs
    """
    tmsg = []
    for item in self._substitutes:
      tmsg.append("%-35s : %s@w" % (item, self._substitutes[item]['sub']))
    if len(tmsg) == 0:
      tmsg = ['None']
    return tmsg

  def clearsubs(self):
    """
    clear all subs
    """
    self._substitutes.clear()
    self._substitutes.sync()

  def reset(self):
    """
    reset the plugin
    """
    BasePlugin.reset(self)
    self.clearsubs()

  def savestate(self):
    """
    save states
    """
    BasePlugin.savestate(self)
    self._substitutes.sync()

