"""
$Id$

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
#TODO Test These
gmcp.get(module) - get data that is in cache for the specified gmcp module
gmcp.sendpacket(what) - send a gmcp packet to the mud with the specified contents
gmcp.togglemodule(modname, mstate) - toggle the gmcp module with modname, mstate should be True or False

To get GMCP data:
1: Save the data from the event
2: Use exported.gmcp.get(module)

"""

from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs import exported
from plugins import BasePlugin

GMCP = chr(201)

canreload = True

name = 'GMCP'
sname = 'GMCP'
purpose = 'GMCP'
author = 'Bast'
version = 1
autoload = True

class dotdict(dict):
    def __getattr__(self, attr):
      return self.get(attr, dotdict())
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__
    
    
#IAC SB GMCP <atcp message text> IAC SE
def gmcpsendpacket(what):
  exported.processevent('to_mud_event', {'data':'%s%s%s%s%s%s' % (IAC, SB, GMCP, what.replace(IAC, IAC+IAC), IAC, SE), 'raw':True, 'dtype':GMCP})  
    
    
# Server
class SERVER(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', level=2, mtype='GMCP')
    if command == WILL:
      self.telnetobj.msg('GMCP: sending IAC DO GMCP', level=2, mtype='GMCP')
      self.telnetobj.send(IAC + DO + GMCP)
      self.telnetobj.options[ord(GMCP)] = True
      exported.processevent('GMCP:server-enabled', {})
      
    elif command == SE:
      if not self.telnetobj.options[ord(GMCP)]:
        # somehow we missed negotiation
        print '##BUG: Enabling GMCP, missed negotiation'
        self.telnetobj.options[ord(GMCP)] = True        
        exported.processevent('GMCP:server-enabled', {})
        
      data = sbdata
      modname, data = data.split(" ", 1)
      import json
      newdata = json.loads(data)
      self.telnetobj.msg(modname, data, level=2, mtype='GMCP')
      self.telnetobj.msg(type(newdata), newdata, level=2, mtype='GMCP')
      tdata = {}
      tdata['data'] = newdata
      tdata['module'] = modname
      tdata['server'] = self.telnetobj
      exported.processevent('to_client_event', {'todata':'%s%s%s%s%s%s' % (IAC, SB, GMCP, sbdata.replace(IAC, IAC+IAC), IAC, SE), 'raw':True, 'dtype':GMCP})      
      exported.processevent('GMCP_raw', tdata)


# Client
class CLIENT(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, GMCP)
    #self.telnetobj.debug_types.append('GMCP')    
    self.telnetobj.msg('GMCP: sending IAC WILL GMCP', mtype='GMCP')    
    self.telnetobj.addtooutbuffer(IAC + WILL + GMCP, True)
    self.cmdqueue = []
    
  def handleopt(self, command, sbdata):
    self.telnetobj.msg('GMCP:', ord(command), '- in handleopt', mtype='GMCP')
    if command == DO:
      self.telnetobj.msg('GMCP:setting options["GMCP"] to True', mtype='GMCP')    
      self.telnetobj.options[ord(GMCP)] = True        
    elif command == SE:
      exported.processevent('GMCP_from_client', {'data': sbdata, 'client':self.telnetobj})
      
      
# Plugin
class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    """
    Iniitialize the class
    
    self.gmcpcache - the cache of values for different GMCP modules
    self.modstates - the current counter for what modules have been enabled
    self.gmcpqueue - the queue of gmcp commands that the client sent before connected to the server
    self.gmcpmodqueue - the queue of gmcp modules that were enabled by the client before connected to the server
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)

    self.gmcpcache = {}
    self.modstates = {}
    self.gmcpqueue = []
    self.gmcpmodqueue = []   
    
    self.reconnecting = False   

  def disconnect(self, args):
    exported.debug('setting reconnect to true')
    self.reconnecting = True    

  def gmcptogglemodule(self, modname, mstate):     
    if not (modname in self.modstates):
      self.modstates[modname] = 0
    
    if mstate:
      if self.modstates[modname] == 0:
        exported.debug('Enabling GMCP module', modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 1)
        gmcpsendpacket(cmd)
      self.modstates[modname] = self.modstates[modname] + 1
      
    else:
      self.modstates[modname] = self.modstates[modname] - 1
      if self.modstates[modname] == 0:
        exported.debug('Disabling GMCP module', modname)
        cmd = 'Core.Supports.Set [ "%s %s" ]' % (modname, 0)
        gmcpsendpacket(cmd)       
    
  def gmcpget(self, module):
    mods = module.split('.')  
    mods = [x.lower() for x in mods]
    tlen = len(mods)
      
    currenttable = self.gmcpcache
    previoustable = dotdict()
    for i in range(0,tlen):
      if not (mods[i] in currenttable):
        return None
      
      previoustable = currenttable
      currenttable = currenttable[mods[i]]
      
    return currenttable
    
  def gmcpfromserver(self, args):
    modname = args['module'].lower()

    mods = modname.split('.')  
    mods = [x.lower() for x in mods]    
    tlen = len(mods)
      
    currenttable = self.gmcpcache
    previoustable = dotdict()
    for i in range(0,tlen):
      if not (mods[i] in currenttable):
        currenttable[mods[i]] = dotdict()
      
      previoustable = currenttable
      currenttable = currenttable[mods[i]]
      
    previoustable[mods[tlen - 1]] = dotdict()  
    datatable = previoustable[mods[tlen - 1]]
    
    for i in args['data']:
      try:
        datatable[i] = args['data'][i]
      except TypeError:
        print "TypeError: string indices must be integers"
        print 'i', i
        print 'datatable', datatable
        print 'args[data]', args['data']
    
    exported.processevent('GMCP', args)
    exported.processevent('GMCP:%s' % modname, args)
    exported.processevent('GMCP:%s' % mods[0], args)
    
  def gmcprequest(self, args):
    if not self.reconnecting:
      for i in self.gmcpmodqueue:
        self.gmcptogglemodule(i['modname'],i['toggle'])
    else:
      reconnecting = False
      for i in self.modstates:
        v = self.modstates[i]
        if v > 0:
          exported.debug('Re-Enabling GMCP module',i)
          cmd = 'Core.Supports.Set [ "%s %s" ]' % (i, 1)
          gmcpsendpacket(cmd)        
        
    for i in self.gmcpqueue:
      gmcpsendpacket(i)    
  
  def gmcpfromclient(self, args):
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
            
        if not exported.connected:
          self.gmcpmodqueue.append({'modname':modname, 'toggle':toggle})
        else:
          self.gmcptogglemodule(modname, toggle)
    else:
      if not exported.connected:
        self.gmcpqueue.append(data)
      else:
        gmcpsendpacket(data)  
  
  def load(self):
    exported.registerevent('GMCP_raw', self.gmcpfromserver)
    exported.registerevent('GMCP_from_client', self.gmcpfromclient)
    exported.registerevent('GMCP:server-enabled', self.gmcprequest)
    exported.registerevent('muddisconnect', self.disconnect)
    exported.gmcp = dotdict()
    exported.gmcp['getv'] = self.gmcpget
    exported.gmcp['sendpacket'] = gmcpsendpacket
    exported.gmcp['togglemodule'] = self.gmcptogglemodule    
    
  def unload(self):
    exported.unregisterevent('GMCP_raw', self.gmcpfromserver)
    exported.unregisterevent('GMCP_from_client', self.gmcpfromclient)
    exported.unregisterevent('GMCP:server-enabled', self.gmcprequest)
    exported.unregisterevent('muddisconnect', self.disconnect)
    exported.gmcp = None  
  
