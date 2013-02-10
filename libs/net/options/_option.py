"""
$Id$
"""
class TelnetOption(object):
  def __init__(self, telnetobj, option):
    self.telnetobj = telnetobj
    self.option = option    
    self.telnetobj.option_handlers[ord(self.option)] = self
    #self.telnetobj.debug_types.append(self.option)

  def onconnect(self):
    self.telnetobj.msg('onconnect for option', ord(self.option), mtype='option')

  def handleopt(self, command, sbdata):
    self.telnetobj.msg('handleopt for option', ord(self.option), mtype='option')

  def reset(self, onclose=False):
    self.telnetobj.msg('reset for option', ord(self.option), mtype='option')
    self.telnetobj.options[ord(self.option)] = False