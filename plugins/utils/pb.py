"""
This plugin sends messages through the pushbullet api

## Usage
 * You must install [pushbullet.py](https://pypi.python.org/pypi/pushbullet.py)
 * Enter your api key with the apikey command

"""
import smtplib
import os
import argparse
import stat
from datetime import datetime

from plugins._baseplugin import BasePlugin


#these 5 are required
NAME = 'Pushbullet'
SNAME = 'pb'
PURPOSE = 'send info through Pushbullet'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = False


class Plugin(BasePlugin):
  """
  a plugin to send email
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.api('api.add')('note', self.api_note)
    self.api('api.add')('link', self.api_link)

    global Pushbullet
    from pushbullet import Pushbullet

  def getapikey(self):
    """
    read the api key from a file
    """
    first_line = ''
    filen = os.path.join(self.savedir, 'pushbullet')
    try:
      with open(filen, 'r') as f:
        first_line = f.readline()

      return first_line.strip()
    except IOError:
      self.api('send.error')('Please setup your password with #bp.pb.apikey')

    return ''

  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)

    self.api('setting.add')('channel', '', str,
                        'the channel to send to')

    parser = argparse.ArgumentParser(add_help=False,
                 description='send a note')
    parser.add_argument('title',
                        help='the title of the note',
                        default='Pushbullet note from bastproxy',
                        nargs='?')
    parser.add_argument('body',
                        help='the body of the note',
                        default='A Pushbullet note sent through bastproxy',
                        nargs='?')
    parser.add_argument('-c', "--channel",
          help="the pushbullet channel to send to",
              default='')
    self.api('commands.add')('note', self.cmd_note,
                                        parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='send a link')
    parser.add_argument('title',
                        help='the title of the link',
                        default='Pushbullet link from bastproxy',
                        nargs='?')
    parser.add_argument('url',
                        help='the url of the link',
                        default='https://github.com/endavis/bastproxy',
                        nargs='?')
    parser.add_argument('-c', "--channel",
          help="the pushbullet channel to send to",
              default='')
    self.api('commands.add')('link', self.cmd_link,
                                        parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='add the apikey')
    parser.add_argument('apikey',
                        help='an apikey from pushbullet',
                        default='',
                        nargs='?')
    self.api('commands.add')('apikey', self.cmd_apikey, history=False,
                                        parser=parser)

    parser = argparse.ArgumentParser(add_help=False,
                 description='show channels associated with pb')
    self.api('commands.add')('channels', self.cmd_channels,
                                        parser=parser)

  # send a note through pushbullet
  def api_note(self, title, body, channel=None):
    """ send a note through pushbullet

    @Ytitle@w     = the title of the note
    @Ybody@w      = the body of the note
    @Ychannel@w   = the pushbullet channel to send to

    this function returns True if sent, False otherwise"""
    apikey = self.getapikey()

    if not apikey:
      return False

    pb = Pushbullet(apikey)

    rval = {}
    found = False
    nchannel = channel or self.api.get('setting.gets')('channel')
    if nchannel:
      for i in pb.channels:
        if str(i.channel_tag) == nchannel:
          found = True
          rval = i.push_note(title, body)
          break

      if not found:
        self.api('send.error')('There was no channel %s' % nchannel)
        return False

    else:
      rval = pb.push_note(title, body)

    pb._session.close()

    if 'error' in rval:
      self.api('send.error')('Pushbullet send failed with %s' % rval)
      return False
    else:
      self.api('send.msg')('pb returned %s' % rval)
      return True

  # send a url through pushbullet
  def api_link(self, title, url, channel=None):
    """ send a link through pushbullet

    @Ytitle@w  = the title of the note
    @Yurl@w      = the body of the note
    @Ychannel@w   = the pushbullet channel to send to

    this function returns True if sent, False otherwise"""
    apikey = self.getapikey()

    if not apikey:
      return False

    pb = Pushbullet(apikey)

    rval = {}
    nchannel = channel or self.api.get('setting.gets')('channel')
    if nchannel:
      for i in pb.channels:
        if str(i.channel_tag) == nchannel:
          found = True
          rval = i.push_link(title, url)
          break

      if not found:
        self.api('send.error')('There was no channel %s' % nchannel)
        return False

    else:
      rval = pb.push_link(title, url)

    pb._session.close()

    if 'error' in rval:
      self.api('send.error')('Pushbullet send failed with %s' % rval)
      return False
    else:
      self.api('send.msg')('pb returned %s' % rval)
      return True

  def cmd_channels(self, args):
    """
    list the channels
    """
    tmsg = []
    apikey = self.getapikey()

    if not apikey:
      return False

    pb = Pushbullet(apikey)

    for i in pb.channels:
      tmsg.append(str(i.channel_tag))

    return True, tmsg

  def cmd_apikey(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    enter the apikey
    @CUsage@w: @B%(cmdname)s@w @Yapikey@x
      @Yapikey@w   = the apikey from pushbullet.com
    """
    if args['apikey']:
      filen = os.path.join(self.savedir, 'pushbullet')
      apifile = open(filen, 'w')
      apifile.write(args['apikey'])
      os.chmod(filen, stat.S_IRUSR | stat.S_IWUSR)
      return True, ['APIkey saved']
    else:
      return True, ['Please enter the apikey']

  def cmd_note(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    Send a note
    @CUsage@w: @B%(cmdname)s@w @Ytitle@x @Ybody@x
      @Ytitle@w   = the title of the note
      @Ybody@w    = the body of the note
      @Ychannel@w    = the channel the note should be sent to
    """
    title = args['title']
    body = args['body']
    channel = args['channel']
    if self.api('pb.note')(title, body, channel):
      return True, ['Pushbullet note sent']
    else:
      return True, ['Attempt failed, please see error message']

  def cmd_link(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    Send a link
    @CUsage@w: @B%(cmdname)s@w @Ytitle@x @Ybody@x
      @Ytitle@w   = the title of the link
      @Yurl@w    = the url of the link
      @Ychannel@w    = the channel the note should be sent to
    """
    title = args['title']
    body = args['url']
    channel = args['channel']
    if self.api('pb.link')(title, body, channel):
      return True, ['Pushbullet link sent']
    else:
      return True, ['Attempt failed, please see error message']
