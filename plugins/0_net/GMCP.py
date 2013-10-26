"""
$Id$

This plugin will show information about connections to the proxy
"""
from plugins import BasePlugin
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs.utils import DotDict

GMCP = chr(201)

NAME = 'GMCP'
SNAME = 'GMCP'
PURPOSE = 'GMCP'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True

# send a gmcp packet
def gmcpsendpacket(what):
  """
  send a gmcp packet
  only argument is what to send
  #IAC SB GMCP <gmcp message text> IAC SE
  """
  from libs.api import API
  api = API()
  api.get('events.eraise')('to_mud_event', {'data':'%s%s%s%s%s%s' % \
              (IAC, SB, GMCP, what.replace(IAC, IAC+IAC), IAC, SE),
              'raw':True, 'dtype':GMCP})

# Plugin
class Plugin(BasePlugin):
  """
  a plugin to handle external gmcp actions
  """
  def __init__(self, *args, **kwargs):
    """
    Iniitialize the class

    self.gmcpcache - the cache of values for different GMCP modules
    self.modstates - the current counter for what modules have been enabled
    self.gmcpqueue - the queue of gmcp commands that the client sent
              before connected to the server
    self.gmcpmodqueue - the queue of gmcp modules that were enabled by
              the client before connected to the server
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.api.get('api.add')('sendpacket', gmcpsendpacket)
    self.api.get('api.add')('sendmodule', self.sendmoduletoclients)
    self.api.get('api.add')('togglemodule', self.gmcptogglemodule)
    self.api.get('api.add')('getv', self.gmcpget)
    self.api.get('events.register')('GMCP_raw', self.gmcpfromserver)
    self.api.get('events.register')('GMCP_from_client', self.gmcpfromclient)
    self.api.get('events.register')('GMCP:server-enabled', self.gmcprequest)
    self.api.get('events.register')('muddisconnect', self.disconnect)
    self.canreload = False

    self.gmcpcache = {}
    self.modstates = {}
    self.gmcpqueue = []
    self.gmcpmodqueue = []

    self.reconnecting = False

  def disconnect(self, _=None):
    """
    disconnect
    """
    self.api.get('output.msg')('setting reconnect to true')
    self.reconnecting = True

  # toggle a gmcp module
  def gmcptogglemodule(self, modname, mstate):
    """
    toggle a gmcp module
    argument 1: module name
    argument 2: state (boolean)
    """
    if not (modname in self.modstates):
      self.modstates[modname] = 0

    if mstate:
      if self.modstates[modname] == 0:
        self.api.get('output.msg')('Enabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 1)
        gmcpsendpacket(cmd)
      self.modstates[modname] = self.modstates[modname] + 1

    else:
      self.modstates[modname] = self.modstates[modname] - 1
      if self.modstates[modname] == 0:
        self.api.get('output.msg')('Disabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 0)
        gmcpsendpacket(cmd)

  # get a gmcp value/module from the cache
  def gmcpget(self, module):
    """
    Get a gmcp module from the cache
    argument 1: module name (such as char.status)
    """
    mods = module.split('.')
    mods = [x.lower() for x in mods]
    tlen = len(mods)

    currenttable = self.gmcpcache
    #previoustable = DotDict()
    for i in range(0, tlen):
      if not (mods[i] in currenttable):
        return None

      #previoustable = currenttable
      currenttable = currenttable[mods[i]]

    return currenttable

  # send a gmcp module to all clients that support gmcp
  def sendmoduletoclients(self, modname):
    """
    send a gmcp module
    """
    data = self.gmcpget(modname)
    if data:
      import json
      tdata = json.dumps(data)
      tpack = '%s %s' % (modname, tdata)
      self.api.get('events.eraise')('to_client_event', {'todata':'%s%s%s%s%s%s' % \
              (IAC, SB, GMCP, tpack.replace(IAC, IAC+IAC), IAC, SE),
              'raw':True, 'dtype':GMCP})

  def gmcpfromserver(self, args):
    """
    handle gmcp data from the server
    """
    modname = args['module'].lower()
    mods = modname.split('.')
    mods = [x.lower() for x in mods]

    if modname != 'room.wrongdir':
      tlen = len(mods)

      currenttable = self.gmcpcache
      previoustable = DotDict()
      for i in range(0, tlen):
        if not (mods[i] in currenttable):
          currenttable[mods[i]] = DotDict()

        previoustable = currenttable
        currenttable = currenttable[mods[i]]

      previoustable[mods[tlen - 1]] = DotDict()
      datatable = previoustable[mods[tlen - 1]]

      for i in args['data']:
        try:
          datatable[i] = args['data'][i]
        except TypeError:
          msg = []
          msg.append("TypeError: string indices must be integers")
          msg.append('i: %s' % i)
          msg.append('datatable: %s' % datatable)
          msg.append('args: %s' % args)
          msg.append('args[data]: %s' % args['data'])
          self.api.get('output.traceback')('\n'.join(msg))

    self.api.get('output.msg')('%s : %s' % (args['module'], args['data']))
    self.api.get('events.eraise')('GMCP', args)
    self.api.get('events.eraise')('GMCP:%s' % modname, args)
    self.api.get('events.eraise')('GMCP:%s' % mods[0], args)

  def gmcprequest(self, _=None):
    """
    handle a gmcp request
    """
    if not self.reconnecting:
      for i in self.gmcpmodqueue:
        self.gmcptogglemodule(i['modname'], i['toggle'])
      self.gmcpmodqueue = []
    else:
      self.reconnecting = False
      for i in self.modstates:
        tnum = self.modstates[i]
        if tnum > 0:
          self.api.get('output.msg')('Re-Enabling GMCP module %s' % i)
          cmd = 'Core.Supports.Set [ "%s %s" ]' % (i, 1)
          gmcpsendpacket(cmd)

    for i in self.gmcpqueue:
      gmcpsendpacket(i)
    self.gmcpqueue = []

  def gmcpfromclient(self, args):
    """
    handle gmcp data from the client
    """
    #print 'gmcpfromclient', args
    proxy = self.api.get('managers.getm')('proxy')
    data = args['data']
    if 'core.supports.set' in data.lower():
      mods = data[data.find("[")+1:data.find("]")].split(',')
      for i in mods:
        tmod = i.strip()
        tmod = tmod[1:-1]
        modname, toggle = tmod.split()
        if int(toggle) == 1:
          toggle = True
        else:
          toggle = False

        if not proxy.connected:
          self.gmcpmodqueue.append({'modname':modname, 'toggle':toggle})
        else:
          self.gmcptogglemodule(modname, toggle)
    elif 'rawcolor' in data.lower() or 'group' in data.lower():
      #we only support rawcolor on right now, the json parser doesn't like
      #ascii codes, we also turn on group and leave it on
      return
    else:
      if not proxy.connected:
        if not (data in self.gmcpqueue):
          self.gmcpqueue.append(data)
      else:
        gmcpsendpacket(data)


