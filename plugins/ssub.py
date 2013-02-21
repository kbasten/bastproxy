"""
$Id$
"""
import os
from libs import exported
from libs import color
from plugins import BasePlugin
from libs.persistentdict import PersistentDict

#these 5 are required
name = 'Simple Substitute'
sname = 'ssub'
purpose = 'simple substitution of strings'
author = 'Bast'
version = 1

# This keeps the plugin from being autoloaded if set to False
autoload = True


class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.savesubfile = os.path.join(exported.basepath, 'data', 'plugins', self.sname + '-subs.txt')
    self._substitutes = PersistentDict(self.savesubfile, 'c', format='json')
    self.cmds['add'] = {'func':self.cmd_add, 'shelp':'Add a substitute'}
    self.cmds['remove'] = {'func':self.cmd_remove, 'shelp':'Remove a substitute'}
    self.cmds['list'] = {'func':self.cmd_list, 'shelp':'List substitutes'}
    self.cmds['clear'] = {'func':self.cmd_clear, 'shelp':'Clear all substitutes'}
    self.defaultcmd = 'list'
    self.events['to_client_event'] = {'func':self.findsub}
    self.addsetting('test', True, bool, 'A test boolean variable')

  def findsub(self, args):
    data = args['todata']
    dtype = args['dtype']
    if dtype != 'fromproxy':
      for mem in self._substitutes.keys():
        if mem in data:
          data = data.replace(mem, color.convertcolors(self._substitutes[mem]['sub']))
      args['todata'] = data
      return args

  def cmd_add(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  Add a substitute
  @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
    @Yoriginalstring@w    = The original string to be replaced
    @Mreplacementstring@w = The new string"""  
    tmsg = []
    if len(args) == 2 and args[0] and args[1]:
      tmsg.append("@GAdding substitute@w : '%s' will be replaced by '%s'" % (args[0], args[1]))
      self.addsub(args[0], args[1])
      return True, tmsg
    else:
      tmsg.append("@RWrong number of arguments")
      return False, tmsg

  def cmd_remove(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  Remove a substitute
  @CUsage@w: rem @Y<originalstring>@w
    @Yoriginalstring@w    = The original string"""    
    tmsg = []
    if len(args) > 0 and args[0]:
      tmsg.append("@GRemoving substitute@w : '%s'" % (args[0]))
      self.removesub(args[0])
      return True, tmsg
    else:
      return False, tmsg

  def cmd_list(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  List substitutes
  @CUsage@w: list"""
    if len(args) >= 1:
      return False, []
    else:
      tmsg = self.listsubs()
      return True, tmsg

  def cmd_clear(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  List substitutes
  @CUsage@w: list"""
    self.clearsubs()
    return True, ['Substitutes cleared']
    
  def addsub(self, item, sub):
    self._substitutes[item] = {'sub':sub}
    self._substitutes.sync()

  def removesub(self, item):
    if item in self._substitutes:
      del self._substitutes[item]
      self._substitutes.sync()      

  def listsubs(self):
    tmsg = []    
    for item in self._substitutes:
      tmsg.append("%-35s : %s@w" % (item, self._substitutes[item]['sub']))
    if len(tmsg) == 0:
      tmsg = ['None']
    return tmsg  

  def clearsubs(self):
    self._substitutes.clear()
    self._substitutes.sync()
    
  def reset(self):
    BasePlugin.reset(self)
    self.clearsubs()
    
  def savestate(self):
    BasePlugin.savestate(self)
    self._substitutes.sync()
    
    