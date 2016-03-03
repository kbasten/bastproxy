"""
This plugin adds events for Aardwolf Ice Ages.
"""
import time
import argparse
from plugins.aardwolf._aardwolfbaseplugin import AardwolfBasePlugin

NAME = 'Aardwolf Daily blessing'
SNAME = 'daily'
PURPOSE = 'Send event when daily blessing is available'
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

    self.seconds = -1
    self.nextdaily = -1

  def load(self):
    """
    load the plugins
    """
    AardwolfBasePlugin.load(self)

    self.api('triggers.add')('daily1',
      "^You can receive a new daily blessing in (?P<hours>[\d]*) hour[s]*, (?P<minutes>[\d]*) minute[s]* and (?P<seconds>[\d]*) second[s]*.$")

    self.api('triggers.add')('daily2',
      "^You can receive a new daily blessing in (?P<minutes>[\d]*) minute[s]* and (?P<seconds>[\d]*) second[s]*.$")

    self.api('triggers.add')('daily3',
      "^You can receive a new daily blessing in (?P<seconds>[\d]*) second[s]*.$")

    self.api('triggers.add')('dailynow',
      "^You are ready to receive a new daily blessing.$")

    self.api('triggers.add')('tookdaily',
      "^You bow your head to Ayla and receive your daily blessing.$")

    parser = argparse.ArgumentParser(add_help=False,
                 description='show next daily')
    self.api.get('commands.add')('next', self.cmd_next,
                                parser=parser)

    self.api('events.register')('trigger_daily1', self.dailytime)
    self.api('events.register')('trigger_daily2', self.dailytime)
    self.api('events.register')('trigger_daily3', self.dailytime)
    self.api('events.register')('trigger_tookdaily', self.tookdaily)
    self.api('events.register')('trigger_dailynow', self.dailyavailable)

    self.checkdaily()

  def cmd_next(self, args):
    """
    show nex daily
    """
    msg = []

    if self.nextdaily != -1:
      ntime = time.localtime(self.nextdaily)
      msg.append('Your next daily is at: ' + time.strftime('%a, %d %b %Y %H:%M:%S', ntime))
    else:
      msg.append('Please type daily to update plugin')

    return True, msg

  def dailytime(self, args):
    """
    saw the message about daily time
    """
    hours = 0
    minutes = 0
    seconds = 0
    if 'hours' in args:
      hours = int(args['hours'])

    if 'minutes' in args:
      minutes = int(args['minutes'])

    if 'seconds' in args:
      seconds = int(args['seconds'])

    self.seconds = hours * 60 * 60 + minutes * 60 + seconds

    self.nextdaily = time.time() + self.seconds

    self.updatedaily()

  def tookdaily(self, args):
    """
    took a daily
    """
    self.seconds = 23 * 60 * 60
    self.nextdaily = time.time() + self.seconds

    self.updatedaily()

  def updatedaily(self, args=None):
    """
    update the daily timer
    """
    self.api('send.msg')('updating daily blessing timer')
    self.api('timers.remove')('dailyblessing')
    self.api('timers.add')('dailyblessing', self.dailyavailable,
                              self.seconds, onetime=True)

  def dailyavailable(self, args=None):
    """
    send a daily available event
    """
    self.api('timers.remove')('dailyblessing')
    self.api('events.eraise')('aard_daily_available')

  def afterfirstactive(self, _=None):
    """
    do something on connect
    """
    AardwolfBasePlugin.afterfirstactive(self)

    self.checkdaily()

  def checkdaily(self):
    """
    check to see if daily has been seen
    """
    if self.nextdaily == -1:
      state = self.api.get('GMCP.getv')('char.status.state')
      if state == 3:
        self.api('send.execute')('daily')
