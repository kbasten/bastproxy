"""
$Id$

This plugin will show information about connections to the proxy
"""
from plugins._baseplugin import BasePlugin
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

    self.canreload = False

    self.gmcpcache = {}
    self.modstates = {}
    self.gmcpqueue = []
    self.gmcpmodqueue = []

    self.reconnecting = False

    self.api.get('api.add')('sendpacket', self.api_sendpacket)
    self.api.get('api.add')('sendmodule', self.api_sendmodule)
    self.api.get('api.add')('togglemodule', self.api_togglemodule)
    self.api.get('api.add')('getv', self.api_getv)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('events.register')('GMCP_raw', self.gmcpfromserver)
    self.api.get('events.register')('GMCP_from_client', self.gmcpfromclient)
    self.api.get('events.register')('GMCP:server-enabled', self.gmcprequest)
    self.api.get('events.register')('muddisconnect', self.disconnect)

  # send a GMCP packet
  def api_sendpacket(self, message):
    """  send a GMCP packet
    @Ymessage@w  = the message to send

    this function returns no values

    Format: IAC SB GMCP <gmcp message text> IAC SE"""
    from libs.api import API
    api = API()
    api.get('events.eraise')('to_mud_event', {'data':'%s%s%s%s%s%s' % \
                (IAC, SB, GMCP, message.replace(IAC, IAC+IAC), IAC, SE),
                'raw':True, 'dtype':GMCP})

  def disconnect(self, _=None):
    """
    disconnect
    """
    self.api.get('output.msg')('setting reconnect to true')
    self.reconnecting = True

  # toggle a GMCP module
  def api_togglemodule(self, modname, mstate):
    """  toggle a GMCP module
    @Ymodname@w  = the GMCP module to toggle
    @Ymstate@w  = the state, either True or False

    this function returns no values"""
    if not (modname in self.modstates):
      self.modstates[modname] = 0

    if mstate:
      if self.modstates[modname] == 0:
        self.api.get('output.msg')('Enabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 1)
        self.api.get('GMCP.sendpacket')(cmd)
      self.modstates[modname] = self.modstates[modname] + 1

    else:
      self.modstates[modname] = self.modstates[modname] - 1
      if self.modstates[modname] == 0:
        self.api.get('output.msg')('Disabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 0)
        self.api.get('GMCP.sendpacket')(cmd)

  # get a GMCP value/module from the cache
  def api_getv(self, module):
    """  get a GMCP value/module from the cache
    @Ymodule@w  = the module to get

    this function returns a table or value depending on what is requested"""
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

  # send a GMCP module to all clients that support GMCP
  def api_sendmodule(self, modname):
    """  send a GMCP module to clients that support GMCP
    @Ymodname@w  = the module to send to clients

    this function returns no values"""
    data = self.api.get('GMCP.getv')(modname)
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
        self.api.get('GMCP.togglemodule')(i['modname'], i['toggle'])
      self.gmcpmodqueue = []
    else:
      self.reconnecting = False
      for i in self.modstates:
        tnum = self.modstates[i]
        if tnum > 0:
          self.api.get('output.msg')('Re-Enabling GMCP module %s' % i)
          cmd = 'Core.Supports.Set [ "%s %s" ]' % (i, 1)
          self.api.get('GMCP.sendpacket')(cmd)

    for i in self.gmcpqueue:
      self.api.get('GMCP.sendpacket')(i)
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
          self.api.get('GMCP.togglemodule')(modname, toggle)
    elif 'rawcolor' in data.lower() or 'group' in data.lower():
      #we only support rawcolor on right now, the json parser doesn't like
      #ascii codes, we also turn on group and leave it on
      return
    else:
      if not proxy.connected:
        if not (data in self.gmcpqueue):
          self.gmcpqueue.append(data)
      else:
        self.api.get('GMCP.sendpacket')(data)


