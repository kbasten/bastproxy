"""
This plugin sends emails when certain events happen in aardwolf

It sends alerts for the following:

 * quests available
 * gq available
 * ice age
"""
import time

from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Email Alerts'
SNAME = 'malerts'
PURPOSE = 'Email Alerts for Aardwolf Events'
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
    self.api.get('dependency.add')('aardwolf.iceage')

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api.get('setting.add')('email', '', str,
                        'the email to send the alerts', nocolor=True)
    self.api.get('events.register')('aard_gq_declared', self._gqdeclared)
    self.api.get('events.register')('aard_quest_ready', self._quest)
    self.api.get('events.register')('aard_iceage', self._iceage)

  def _gqdeclared(self, args):
    """
    do something when a gq is declared
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - A GQuest has been declared for levels %s to %s. (%s)' % (
              proxy.host, proxy.port,
              args['lowlev'], args['highlev'], times)
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
    times = time.asctime(time.localtime())
    msg = '%s:%s - Time to quest! (%s)' % (
              proxy.host, proxy.port, times)
    email = self.api.get('setting.gets')('email')
    if email:
      self.api.get('mail.send')('Quest Time', msg,
              email)
    else:
      self.api.get('mail.send')('Quest Time', msg)

  def _iceage(self, _=None):
    """
    send an email that an iceage approaches
    """
    proxy = self.api.get('managers.getm')('proxy')
    times = time.asctime(time.localtime())
    msg = '%s:%s - An ice age approaches! (%s)' % (
              proxy.host, proxy.port, times)
    email = self.api.get('setting.gets')('email')
    if email:
      self.api.get('mail.send')('Ice Age', msg,
              email)
    else:
      self.api.get('mail.send')('Ice Age', msg)
