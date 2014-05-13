"""
This plugin handles Aardwolf 102 telnet option
"""
from plugins._baseplugin import BasePlugin
from libs.net.telnetlib import WILL, DO, IAC, SE, SB
from libs.net._basetelnetoption import BaseTelnetOption

NAME = 'A102'
SNAME = 'A102'
PURPOSE = 'Handle telnet option 102, Aardwolf specific'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 35

AUTOLOAD = True

AOPTIONS = {}
AOPTIONS['STATMON'] = 1
AOPTIONS['BIGMAPTAGS'] = 2
AOPTIONS['HELPTAGS'] = 3
AOPTIONS['MAPTAGS'] = 4
AOPTIONS['CHANNELTAGS'] = 5
AOPTIONS['TELLTAGS'] = 6
AOPTIONS['SPELLUPTAGS'] = 7
AOPTIONS['SKILLGAINTAGS'] = 8
AOPTIONS['SAYTAGS'] = 9
AOPTIONS['SCORETAGS'] = 11
AOPTIONS['ROOMNAME'] = 12
AOPTIONS['EXITS'] = 14
AOPTIONS['EDITORTAGS'] = 15
AOPTIONS['EQTAGS'] = 16
AOPTIONS['INVTAGS'] = 17
AOPTIONS['ROOMDESCTAGS'] =  18
AOPTIONS['ROOMNAMETAGS'] = 19
AOPTIONS['REPOPTAGS'] = 21

AOPTIONS['QUIETTAGS'] = 50
AOPTIONS['AUTOTICK'] =  51
AOPTIONS['PROMPT'] = 52
AOPTIONS['PAGING'] = 53
AOPTIONS['AUTOMAP'] = 54
AOPTIONS['SHORTMAP'] = 55

AOPTIONREV = {}
for optionn in AOPTIONS:
  AOPTIONREV[AOPTIONS[optionn]] = optionn

ON = chr(1)
OFF = chr(2)

A102 = chr(102)

# Plugin
class Plugin(BasePlugin):
  """
  the plugin to handle external a102 stuff
  """
  def __init__(self, tname, tsname, filename, directory, importloc):
    """
    Iniitilaize the class

    self.optionsstates - the current counter for what
                            options have been enabled
    self.a102optionqueue - the queue of a102 options
                            that were enabled by the client before
                             connected to the server
    """
    BasePlugin.__init__(self, tname, tsname, filename, directory, importloc)

    self.canreload = False

    self.optionstates = {}
    self.a102optionqueue = []

    self.reconnecting = False

    self.api.get('api.add')('sendpacket', self.api_sendpacket)
    self.api.get('api.add')('toggle', self.api_toggle)

  def load(self):
    """
    load the plugins
    """
    BasePlugin.load(self)

    self.api.get('events.register')('A102_from_server', self.a102fromserver)
    self.api.get('events.register')('A102_from_client', self.a102fromclient)
    self.api.get('events.register')('A102:server-enabled', self.a102request)
    self.api.get('events.register')('muddisconnect', self.disconnect)

    self.api.get('options.addserveroption')(self.sname, SERVER)
    self.api.get('options.addclientoption')(self.sname, CLIENT)

  # Send an A102 packet
  def api_sendpacket(self, message):
    """  send an A102 packet
    @Ymessage@w  = the message to send

    Format: IAC SB A102 <atcp message text> IAC SE

    this function returns no values"""
    from libs.api import API
    api = API()
    api.get('events.eraise')('to_mud_event', {'data':'%s%s%s%s%s%s' % \
          (IAC, SB, A102, message.replace(IAC, IAC+IAC), IAC, SE),
          'raw':True, 'dtype':A102})

  def disconnect(self, _=None):
    """
    this function is registered with the muddisconnect hook
    """
    self.api.get('send.msg')('setting reconnect to true')
    self.reconnecting = True

  # toggle an a102 option
  def api_toggle(self, aoption, mstate):
    """  toggle an A102 option
    @Yaoption@w  = the A102 option to toggle
    @Ymstate@w  = the state, either True or False

    this function True if the option was toggled, False if it didn't
    exist"""
    if aoption in AOPTIONS:
      self.a102toggleoption(AOPTIONS[aoption], mstate)
      return True
    else:
      return False

  def a102toggleoption(self, aoption, mstate):
    """
    toggle an a102 option
    """
    if not (aoption in self.optionstates):
      if mstate:
        self.optionstates[aoption] = 0
      else:
        self.optionstates[aoption] = 1

    if mstate:
      mstate = 1
      if self.optionstates[aoption] == 0:
        self.api.get('send.msg')('Enabling A102 option: %s' % \
                                              AOPTIONREV[aoption])
        cmd = '%s%s' % (chr(aoption), ON)
        self.api.get('A102.sendpacket')(cmd)
      self.optionstates[aoption] = self.optionstates[aoption] + 1

    else:
      mstate = 2
      self.optionstates[aoption] = self.optionstates[aoption] - 1
      if self.optionstates[aoption] == 0:
        self.api.get('send.msg')('Disabling A102 option: %s' % \
                                              AOPTIONREV[aoption])
        cmd = '%s%s' % (chr(aoption), OFF)
        self.api.get('A102.sendpacket')(cmd)

  def a102fromserver(self, args):
    """
    handle stuff from the server
    """
    self.api.get('events.eraise')('A102', args)
    self.api.get('events.eraise')('A102:%s' % args['option'], args)

  def a102request(self, _=None):
    """
    this function is called when the a102 option is enabled
    """
    self.api.get('send.msg')('cleaning a102 queues')
    if not self.reconnecting:
      for i in self.a102optionqueue:
        self.a102toggleoption(i['option'], i['toggle'])
    else:
      self.reconnecting = False
      for i in self.optionstates:
        tnum = self.optionstates[i]
        if tnum > 0:
          self.api.get('send.msg')('Re-Enabling A102 option: %s' % \
                                                    AOPTIONREV[i])
          cmd = '%s%s' % (i, 1)
          self.api.get('A102.sendpacket')(cmd)
        else:
          self.api.get('send.msg')('Re-Disabling A102 option: %s' % \
                                                    AOPTIONREV[i])
          cmd = '%s%s' % (i, 2)
          self.api.get('A102.sendpacket')(cmd)

  def a102fromclient(self, args):
    """
    this function is called when we receive an a102 option from the client
    """
    proxy = self.api.get('managers.getm')('proxy')
    data = args['data']
    option = ord(data[0])
    mstate = ord(data[1])
    if mstate == 1:
      mstate = True
    else:
      mstate = False
    if not proxy.connected:
      self.a102optionqueue.append({'option':option, 'toggle':mstate})
    else:
      self.a102toggleoption(option, mstate)

# Server
class SERVER(BaseTelnetOption):
  """
  a class to handle aard102 for the server
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.debug_types.append('A102')

  def handleopt(self, command, sbdata):
    """
    handle the a102 option from the server
    """
    self.telnetobj.msg('A102:', ord(command), '- in handleopt',
                        level=2, mtype='A102')
    if command == WILL:
      self.telnetobj.msg('A102: sending IAC DO A102', level=2, mtype='A102')
      self.telnetobj.send(IAC + DO + A102)
      self.telnetobj.options[ord(A102)] = True
      self.api.get('events.eraise')('A102:server-enabled', {})

    elif command == SE:
      if not self.telnetobj.options[ord(A102)]:
        print '##BUG: Enabling A102, missed negotiation'
        self.telnetobj.options[ord(A102)] = True
        self.api.get('events.eraise')('A102:server-enabled', {})

      tdata = {}
      tdata['option'] = ord(sbdata[0])
      tdata['flag'] = ord(sbdata[1])
      tdata['server'] = self.telnetobj
      self.telnetobj.msg('A102: got %s,%s from server' % \
              (tdata['option'], tdata['flag']), level=2, mtype='A102')
      self.api.get('events.eraise')('to_client_event',
                  {'original':'%s%s%s%s%s%s' % (IAC, SB, A102,
                  sbdata.replace(IAC, IAC+IAC), IAC, SE),
                  'raw':True, 'dtype':A102})
      self.api.get('events.eraise')('A102_from_server', tdata)

# Client
class CLIENT(BaseTelnetOption):
  """
  a class to handle a102 options from the client
  """
  def __init__(self, telnetobj):
    """
    initialize the instance
    """
    BaseTelnetOption.__init__(self, telnetobj, A102)
    self.telnetobj.msg('A102: sending IAC WILL A102', mtype='A102')
    self.telnetobj.addtooutbuffer(IAC + WILL + A102, True)
    self.cmdqueue = []

  def handleopt(self, command, sbdata):
    """
    handle the a102 option for the client
    """
    self.telnetobj.msg('A102:', ord(command), '- in handleopt', mtype='A102')
    if command == DO:
      self.telnetobj.msg('A102:setting options[A102] to True', mtype='A102')
      self.telnetobj.options[ord(A102)] = True
    elif command == SE:
      self.api.get('events.eraise')('A102_from_client',
                                {'data': sbdata, 'client':self.telnetobj})

