"""
This plugin shows and clears errors seen during plugin execution
"""
import argparse
from plugins._baseplugin import BasePlugin

NAME = 'Error Plugin'
SNAME = 'errors'
PURPOSE = 'show and manage errors'
AUTHOR = 'Bast'
VERSION = 1
PRIORITY = 12

AUTOLOAD = True

class Plugin(BasePlugin):
  """
  a plugin to handle errors
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)

  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show errors')
    parser.add_argument('number', help='list the last <number> errors',
                        default='-1', nargs='?')
    self.api.get('commands.add')('show', self.cmd_show, parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='clear errors')
    self.api.get('commands.add')('clear', self.cmd_clear, parser=parser)

  def cmd_show(self, args=None):
    """
    @G%(name)s@w - @B%(cmdname)s@w
      show the error queue
      @CUsage@w: show
    """
    msg = []
    try:
      number = int(args['number'])
    except ValueError:
      msg.append('Please specify a number')
      return False, msg

    errors = self.api.get('errors.gete')()

    if len(errors) == 0:
      msg.append('There are no errors')
    else:
      if args and number > 0:
        for i in errors[-int(number):]:
          msg.append('')
          msg.append('Time: %s' % i['timestamp'])
          msg.append('Error: %s' % i['msg'])

      else:
        for i in errors:
          msg.append('')
          msg.append('Time: %s' % i['timestamp'])
          msg.append('Error: %s' % i['msg'])

    return True, msg

  def cmd_clear(self, args=None):
    """
    clear errors
    """
    self.api.get('errors.clear')()

    return True, ['Errors cleared']

