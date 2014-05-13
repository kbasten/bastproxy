"""
This plugin sends emails when certain events happen in aardwolf
"""
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Alerts'
SNAME = 'alerts'
PURPOSE = 'Alert for Aardwolf Events'
AUTHOR = 'Bast'
VERSION = 1

AUTOLOAD = False

class Plugin(AardwolfBasePlugin):
  """
  a plugin to handle aardwolf quest events
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    AardwolfBasePlugin.__init__(self, *args, **kwargs)
    self.api.get('dependency.add')('aardwolf.gq')
    self.api.get('dependency.add')('aardwolf.quest')


  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('email', '', str,
                        'the email to send the alerts', nocolor=True)
    self.api.get('events.register')('aard_gq_declared', self._gqdeclared)
    self.api.get('events.register')('aard_quest_ready', self._quest)

  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    proxy = self.api.get('managers.getm')('proxy')
    msg = '%s:%s - A GQuest has been declared for levels %s to %s.' % (
              proxy.host, proxy.port,
              args['lowlev'], args['highlev'])
    email = self.api.get('setting.gets')('email')
    if email:
      self.api.get('mail.send')('New GQuest', msg,
              email)
    else:
      self.api.get('mail.send')('New GQuest', msg)

  def _quest(self, _=None):
    """
    do something when you can quest
    """
    proxy = self.api.get('managers.getm')('proxy')
    msg = '%s:%s - Time to quest!' % (
              proxy.host, proxy.port)
    email = self.api.get('setting.gets')('email')
    if email:
      self.api.get('mail.send')('Quest Time', msg,
              email)
    else:
      self.api.get('mail.send')('Quest Time', msg)
