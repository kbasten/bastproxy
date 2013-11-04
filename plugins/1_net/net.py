"""
$Id$

This plugin will show information about connections to the proxy
"""
import time
from libs import utils
from plugins._baseplugin import BasePlugin

#these 5 are required
NAME = 'Net Commands'
SNAME = 'net'
PURPOSE = 'get information about connections'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 35

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

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('commands.add')('clients', self.cmd_clients,
                              shelp='list clients that are connected')
    self.api.get('commands.default')('clients')

  def cmd_clients(self, _):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    List connections
      @CUsage@w: list
    """
    proxy = self.api.get('managers.getm')('proxy')
    clientformat = '%-6s %-17s %-7s %-17s %-s'
    tmsg = ['']
    if proxy:
      if proxy.connectedtime:
        tmsg.append('PROXY: connected for %s' %
                      utils.timedeltatostring(proxy.connectedtime,
                                            time.mktime(time.localtime())))
      else:
        tmsg.append('PROXY: disconnected')

      tmsg.append('')
      tmsg.append(clientformat % ('Type', 'Host', 'Port',
                                            'Client', 'Connected'))
      tmsg.append('@B' + 60 * '-')
      for i in proxy.clients:
        ttime = utils.timedeltatostring(i.connectedtime,
                                          time.mktime(time.localtime()))

        tmsg.append(clientformat % ('Active', i.host[:17], i.port,
                                          i.ttype[:17], ttime))
      for i in proxy.vclients:
        ttime = utils.timedeltatostring(i.connectedtime,
                                          time.mktime(time.localtime()))
        tmsg.append(clientformat % ('View', i.host[:17], i.port,
                                          i.ttype[:17], ttime))

    return True, tmsg

