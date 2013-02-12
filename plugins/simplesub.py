"""
$Id$
"""
from libs import exported
from libs import color
from plugins import BasePlugin

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
    self._substitutes = {}
    self.cmds['add'] = {'func':self.cmd_add, 'shelp':'Add a substitute'}
    self.cmds['remove'] = {'func':self.cmd_remove, 'shelp':'Remove a substitute'}
    self.cmds['list'] = {'func':self.cmd_list, 'shelp':'List substitutes'}
    self.defaultcmd = 'list'
    self.events.append({'event':'to_client_event', 'func':self.findsub})
        
        
  def findsub(self, args):
    data = args['todata']
    dtype = args['dtype']
    if dtype != 'fromproxy':
      for mem in self._substitutes.keys():
        data = data.replace(mem, color.convertcolors(self._substitutes[mem]['sub']))
      args['todata'] = data
      return args

  def cmd_add(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Add a substitute
  @CUsage@w: add @Y<originalstring>@w @M<replacementstring>@w
    @Yoriginalstring@w    = The original string to be replaced
    @Mreplacementstring@w = The new string
---------------------------------------------------------------"""  
    if len(args) == 2 and args[0] and args[1]:
      exported.sendtouser("@GAdding substitute@w : '%s' will be replaced by '%s'" % (args[0], args[1]))
      self.addsub(args[0], args[1])
      return True
    else:
      exported.sendtouser("@RWrong number of arguments")
      return False

  def cmd_remove(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  Remove a substitute
  @CUsage@w: rem @Y<originalstring>@w
    @Yoriginalstring@w    = The original string
---------------------------------------------------------------"""    
    if len(args) > 0 and args[0]:
      exported.sendtouser("@GRemoving substitute@w : '%s'" % (args[0]))
      self.removesub(args[0])
      return True
    else:
      return False

  def cmd_list(self, args):
    """---------------------------------------------------------------
@G%(name)s@w - @B%(cmdname)s@w
  List substitutes
  @CUsage@w: list
---------------------------------------------------------------"""
    print(args)
    if len(args) >= 1:
      return False
    else:
      self.listsubs()
      return True

  def addsub(self, item, sub):
    self._substitutes[item] = {'sub':sub}

  def removesub(self, item):
    if item in self._substitutes:
      del self._substitutes[item]

  def listsubs(self):    
    tstr = 'Substitutes:\n\r'
    tstr = tstr + '-' * 75 + '\n\r'
    for item in self._substitutes:
      tstr = tstr + "%-35s : %s@w\n\r" % (item, self._substitutes[item]['sub'])
    tstr = tstr + '-' * 75
    exported.sendtouser(tstr)  

