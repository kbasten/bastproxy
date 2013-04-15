"""
$Id$
"""
from libs import exported
from libs import utils
from plugins import BasePlugin
import time

#these 5 are required
NAME = 'Net Commands'
SNAME = 'net'
PURPOSE = 'get information about connections'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to show connection information
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.cmds['list'] = {'func':self.cmd_list, 
                            'shelp':'list clients that are connected'}

  def cmd_list(self, _):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List connections
      @CUsage@w: list
    """
    tmsg = ['']
    if exported.PROXY:
      for i in exported.PROXY.clients:
        ttime = utils.timedeltatostring(i.connectedtime, 
                                          time.mktime(time.localtime()))
        tmsg.append('%s : %s - %s - Connected for %s' % \
                                        (i.host, i.port, i.ttype, ttime))
      tmsg.append('')
      tmsg.append('The proxy has been connected to the mud for %s' %
                    utils.timedeltatostring(exported.PROXY.connectedtime, 
                                          time.mktime(time.localtime())))
      tmsg.append('')        
    else:
      tmsg.append('the proxy has not connected to the mud')
    
    return True, tmsg

