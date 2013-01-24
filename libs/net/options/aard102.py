"""
$Id$

This module handles all things A102 (which is aardwolf 102)

SERVER handles all A102 communication to and from the MUD
CLIENT handles all A102 communication to and from a client

A102_MANAGER takes A102 data, caches it and then creates three events
A102
A102:<option>

The args for the event will look like
{'option': 100 , 
 'flag': 5}

It adds the following functions to exported
#TODO Test These
a102.sendpacket(what) - send a a102 packet to the mud with the specified contents
a102.toggleoption(optionname, mstate) - toggle the a102 option with optionname, mstate should be True or False

To get A102 data:
1: Save the data from the event

"""

from libs.net.options._option import TelnetOption
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs import exported

ON = chr(1)
OFF = chr(2)

A102 = chr(102)
A102MAN = None
canreload = True

class dotdict(dict):
    def __getattr__(self, attr):
      return self.get(attr, dotdict())
    __setattr__= dict.__setitem__
    __delattr__= dict.__delitem__
    
    
#IAC SB A102 <atcp message text> IAC SE
def a102sendpacket(what):
  exported.processevent('to_mud_event', {'data':'%s%s%s%s%s%s' % (IAC, SB, A102, what.replace(IAC, IAC+IAC), IAC, SE), 'raw':True, 'dtype':A102})  
    
    
# Server
class SERVER(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.debug_types.append('A102')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('A102:', ord(command), '- in handleopt', level=2, mtype='A102')
    if command == WILL:
      self.telnetobj.msg('A102: sending IAC DO A102', level=2, mtype='A102')
      self.telnetobj.send(IAC + DO + A102)
      
    elif command == SE:
      self.telnetobj.options[ord(A102)] = True
      tdata = {}
      tdata['option'] = ord(sbdata[0])
      tdata['flag'] = ord(sbdata[1])
      tdata['server'] = self.telnetobj
      self.telnetobj.msg('A102: got %s,%s from server' % (tdata['option'], tdata['flag']), level=2, mtype='A102')
      exported.processevent('to_client_event', {'todata':'%s%s%s%s%s%s' % (IAC, SB, A102, sbdata.replace(IAC, IAC+IAC), IAC, SE), 'raw':True, 'dtype':A102})      
      exported.processevent('A102_from_server', tdata)


# Client
class CLIENT(TelnetOption):
  def __init__(self, telnetobj):
    TelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.msg('A102: sending IAC WILL A102', mtype='A102')    
    self.telnetobj.addtooutbuffer(IAC + WILL + A102, True)
    self.cmdqueue = []
    
  def handleopt(self, command, sbdata):
    self.telnetobj.msg('A102:', ord(command), '- in handleopt', mtype='A102')
    if command == DO:
      self.telnetobj.msg('A102:setting options[A102] to True', mtype='A102')    
      self.telnetobj.options[ord(A102)] = True        
    elif command == SE:
      exported.processevent('A102_from_client', {'data': sbdata, 'client':self.telnetobj})
      
      
# Manager
class A102_MANAGER:
  def __init__(self):
    """
    Iniitilaize the class
    
    self.optionsstates - the current counter for what options have been enabled
    self.a102optionqueue - the queue of a102 options that were enabled by the client before connected to the server
    """
    self.name = 'A102'

    self.optionstates = {}
    self.a102optionqueue = []   
    
    self.reconnecting = False   

  def disconnect(self, args):
    exported.debug('setting reconnect to true')
    self.reconnecting = True    

  def a102toggleoption(self, aoption, mstate):
    if not (aoption in self.optionstates):
      if mstate:
        self.optionstates[aoption] = 0
      else:
        self.optionstates[aoption] = 1
    
    if mstate:
      mstate = 1
      if self.optionstates[aoption] == 0:
        exported.debug('Enabling A102 option', aoption)
        cmd = '%s,%s' % (aoption, mstate)
        a102sendpacket(cmd)
      self.optionstates[aoption] = self.optionstates[aoption] + 1
      
    else:
      mstate = 2
      self.optionstates[aoption] = self.optionstates[aoption] - 1
      if self.optionstates[aoption] == 0:
        exported.debug('Disabling A102 option', aoption)
        cmd = '%s,%s' % (aoption, mstate)
        a102sendpacket(cmd)
        
  def a102fromserver(self, args):    
    exported.processevent('A102', args)
    exported.processevent('A102:%s' % args['option'], args)
        
  def a102request(self, args):
    exported.debug('cleaning a102 queues')
    if not self.reconnecting:
      for i in self.a102optionqueue:
        self.a102toggleoption(i['option'],i['toggle'])
    else:
      reconnecting = False
      for i in self.optionstates:
        v = self.optionstates[i]
        if v > 0:
          exported.debug('Re-Enabling A102 option',i)
          cmd = '%s,%s' % (i, 1)
          a102sendpacket(cmd) 
        else:
          exported.debug('Re-Disabling A102 option', i)
          cmd = '%s,%s' % (i, 2)
          a102sendpacket(cmd) 
          
  
  def a102fromclient(self, args):
    data = args['data']
    option = ord(data[0])
    mstate = ord(data[1])
    if mstate == 1:
      mstate = True
    else:
      mstate = False
    if not exported.connected:
      self.a102optionqueue.append({'option':option, 'toggle':mstate})
    else:
      self.a102toggleoption(option, mstate)
         
  def load(self):
    exported.registerevent('A102_from_server', self.a102fromserver)
    exported.registerevent('A102_from_client', self.a102fromclient)
    exported.registerevent('mudconnect', self.a102request)
    exported.registerevent('muddisconnect', self.disconnect)
    exported.a102 = dotdict()
    exported.a102['sendpacket'] = a102sendpacket
    exported.a102['toggleoption'] = self.a102toggleoption  
    
  def unload(self):
    exported.unregisterevent('A102_from_server', self.a102fromserver)
    exported.unregisterevent('A102_from_client', self.a102fromclient)
    exported.unregisterevent('mudconnect', self.a102request)
    exported.unregisterevent('muddisconnect', self.disconnect)
    export.a102 = None  
  
    
def load():
  A102MAN = A102_MANAGER()
  A102MAN.load()


def unload():
  A102MAN.unload()
