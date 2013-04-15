"""
$Id$

#BUG: errors when decoding ansi data when rawcolors is off

This module handles all things GMCP

SERVER handles all GMCP communication to and from the MUD
CLIENT handles all GMCP communication to and from a client

GMCP_MANAGER takes GMCP data, caches it and then creates three events
GMCP
GMCP:<base module name>
GMCP:<full module name>

The args for the event will look like
{'data': {u'clan': u'', u'name': u'Bast', u'perlevel': 6000, 
          u'remorts': 1, u'subclass': u'Ninja', u'race': u'Shadow', 
          u'tier': 6, u'class': u'Thief', u'redos': u'0', u'pretitle': u''}, 
 'module': 'char.base'}

It adds the following functions to exported

gmcp.get(module) - get data that is in cache for the specified gmcp module
gmcp.sendpacket(what) - send a gmcp packet to 
                the mud with the specified contents
gmcp.togglemodule(modname, mstate) - toggle the gmcp module 
                with modname, mstate should be True or False

To get GMCP data:
1: Save the data from the event
2: Use exported.gmcp.get(module)

"""

from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs import exported
from libs.utils import convert, DotDict
from plugins import BasePlugin

GMCP = chr(201)

NAME = 'GMCP'
SNAME = 'GMCP'
PURPOSE = 'GMCP'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = True

    
#IAC SB GMCP <gmcp message text> IAC SE
def gmcpsendpacket(what):
  """
  send a gmcp packet
  only argument is what to send
  """
  exported.event.eraise('to_mud_event', {'data':'%s%s%s%s%s%s' % \
              (IAC, SB, GMCP, what.replace(IAC, IAC+IAC), IAC, SE), 
              'raw':True, 'dtype':GMCP})  
    
    
# Server
class SERVER(TelnetOption):
  """
  a class to handle gmcp data from the server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')

  def handleopt(self, command, sbdata):
    """
    handle the gmcp option
    """
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', 
                              level=2, mtype='GMCP')
    if command == WILL:
      self.telnetobj.msg('GMCP: sending IAC DO GMCP', level=2, mtype='GMCP')
      self.telnetobj.send(IAC + DO + GMCP)
      self.telnetobj.options[ord(GMCP)] = True
      exported.event.eraise('GMCP:server-enabled', {})
      
    elif command == SE:
      if not self.telnetobj.options[ord(GMCP)]:
        # somehow we missed negotiation
        self.telnetobj.msg('##BUG: Enabling GMCP, missed negotiation', 
                                                  level=2, mtype='GMCP')
        self.telnetobj.options[ord(GMCP)] = True        
        exported.event.eraise('GMCP:server-enabled', {})
        
      data = sbdata
      modname, data = data.split(" ", 1)
      try:
        import json
        newdata = json.loads(data.decode('utf-8','ignore'), object_hook=convert)
      except (UnicodeDecodeError, ValueError) as e:
        newdata = {}
        exported.write_traceback('Could not decode: %s' % data)
      self.telnetobj.msg(modname, data, level=2, mtype='GMCP')
      self.telnetobj.msg(type(newdata), newdata, level=2, mtype='GMCP')
      tdata = {}
      tdata['data'] = newdata
      tdata['module'] = modname
      tdata['server'] = self.telnetobj
      exported.event.eraise('to_client_event', {'todata':'%s%s%s%s%s%s' % \
                      (IAC, SB, GMCP, sbdata.replace(IAC, IAC+IAC), IAC, SE), 
                      'raw':True, 'dtype':GMCP})      
      exported.event.eraise('GMCP_raw', tdata)


# Client
class CLIENT(TelnetOption):
  """
  a class to handle gmcp data from a client
  """
  def __init__(self, telnetobj):
    """
    initalize the instance
    """
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')    
    self.telnetobj.msg('GMCP: sending IAC WILL GMCP', mtype='GMCP')    
    self.telnetobj.addtooutbuffer(IAC + WILL + GMCP, True)
    self.cmdqueue = []
    
  def handleopt(self, command, sbdata):
    """
    handle gmcp data from a client
    """
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', mtype='GMCP')
    if command == DO:
      self.telnetobj.msg('GMCP:setting options["GMCP"] to True', 
                                    mtype='GMCP')    
      self.telnetobj.options[ord(GMCP)] = True        
    elif command == SE:
      exported.event.eraise('GMCP_from_client', 
                      {'data': sbdata, 'client':self.telnetobj})
      
      
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
    self.exported['getv'] = {'func':self.gmcpget}
    self.exported['togglemodule'] = {'func':self.gmcptogglemodule}
    self.exported['sendmodule'] = {'func':self.sendmoduletoclients}
    self.exported['sendpacket'] = {'func':gmcpsendpacket}
    self.events['GMCP_raw'] = {'func':self.gmcpfromserver}
    self.events['GMCP_from_client'] = {'func':self.gmcpfromclient}
    self.events['GMCP:server-enabled'] = {'func':self.gmcprequest}
    self.events['muddisconnect'] = {'func':self.disconnect}     
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
    self.msg('setting reconnect to true')
    self.reconnecting = True    

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
        self.msg('Enabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 1)
        gmcpsendpacket(cmd)
      self.modstates[modname] = self.modstates[modname] + 1
      
    else:
      self.modstates[modname] = self.modstates[modname] - 1
      if self.modstates[modname] == 0:
        self.msg('Disabling GMCP module: %s' % modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 0)
        gmcpsendpacket(cmd)       
    
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
    
  def sendmoduletoclients(self, modname):
    """
    send a gmcp module
    """
    data = self.gmcpget(modname)
    if data:
      import json
      tdata = json.dumps(data)
      tpack = '%s %s' % (modname, tdata)
      exported.event.eraise('to_client_event', {'todata':'%s%s%s%s%s%s' % \
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
          exported.write_traceback('\n'.join(msg))

    
    exported.event.eraise('GMCP', args)
    exported.event.eraise('GMCP:%s' % modname, args)
    exported.event.eraise('GMCP:%s' % mods[0], args)
    
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
          self.msg('Re-Enabling GMCP module %s' % i)
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
            
        if not exported.CONNECTED:
          self.gmcpmodqueue.append({'modname':modname, 'toggle':toggle})
        else:
          self.gmcptogglemodule(modname, toggle)
    elif 'rawcolor' in data.lower() or 'group' in data.lower():
      #we only support rawcolor on right now, the json parser doesn't like
      #ascii codes, we also turn on group and leave it on
      return          
    else:
      if not exported.CONNECTED:
        if not (data in self.gmcpqueue):
          self.gmcpqueue.append(data)
      else:
        gmcpsendpacket(data)  
   
  
