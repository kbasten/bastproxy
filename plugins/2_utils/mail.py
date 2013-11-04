"""
$Id$

This plugin sends mail
"""
import smtplib
import os
from datetime import datetime
from plugins._baseplugin import BasePlugin


#these 5 are required
NAME = 'Mail'
SNAME = 'mail'
PURPOSE = 'setup and send mail'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to send email
  """
  def __init__(self, *args, **kwargs):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, *args, **kwargs)
    self.password = ''
    self.api.get('api.add')('send', self.api_send)

  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)

    self.api.get('events.register')('client_connected', self.checkpassword)
    self.api.get('commands.add')('password', self.cmd_pw,
                                        shelp='set the password')
    self.api.get('commands.add')('test', self.cmd_test,
                                        shelp='send a test email')
    self.api.get('commands.add')('check', self.cmd_check,
                      shelp='check to make sure all settings are applied')

    self.api.get('setting.add')('server', '', str, 'the smtp server to send mail through')
    self.api.get('setting.add')('port', '', int, 'the port to use when sending mail')
    self.api.get('setting.add')('username', '', str, 'the username to connect as',
                  nocolor=True)
    self.api.get('setting.add')('to', '', str, 'the address to send mail to',
                  nocolor=True)
    self.api.get('setting.add')('from', '', str, 'the address to send mail from',
                  nocolor=True)
    self.api.get('setting.add')('ssl', '', bool,
                          'set this to True if the connection will use ssl')

    if self.api.get('setting.gets')('username') != '':
      self.api.get('output.client')('Please set the mail password')

  def check(self):
    """
    check to make sure all data need to send mail is available
    """
    self.api.get('setting.gets')('server')
    if not self.api.get('setting.gets')('server') or \
       not self.api.get('setting.gets')('port') or \
       not self.api.get('setting.gets')('username') or \
       not self.password or \
       not self.api.get('setting.gets')('from') or \
       not self.api.get('setting.gets')('to'):
      return False

    return True

  # send an email
  def api_send(self, subject, msg, mailto=None):
    """  send an email
    @Ysubject@w  = the subject of the message
    @Ymsg@w      = the msg to send
    @Ymailto@w   = the email address to send to (default: the to
      setting of the mail plugin)

    this function returns no values"""
    if self.check():
      senddate = datetime.strftime(datetime.now(), '%Y-%m-%d')
      if not mailto:
        mailto = self.api.get('setting.gets')('to')
      mhead = """Date: %s
From: %s
To: %s
Subject: %s
X-Mailer: My-Mail

%s""" % (senddate,
          self.api.get('setting.gets')('from'), mailto, subject, msg)

      try:

        pid = os.fork()
        if pid == 0:
          server = '%s:%s' % (self.api.get('setting.gets')('server'),
                                    self.api.get('setting.gets')('port'))
          server = smtplib.SMTP(server)
          if self.api.get('setting.gets')('ssl'):
            server.starttls()
          server.login(self.api.get('setting.gets')('username'), self.password)
          server.sendmail(self.api.get('setting.gets')('from'), mailto, mhead)
          server.quit()
          os._exit(os.EX_OK)


      except:
        server = '%s:%s' % (self.api.get('setting.gets')('server'),
                              self.api.get('setting.gets')('port'))
        server = smtplib.SMTP(server)
        if self.api.get('setting.gets')('ssl'):
          server.starttls()
        server.login(self.api.get('setting.gets')('username'), self.password)
        server.sendmail(self.api.get('setting.gets')('from'), mailto, mhead)
        server.quit()

  def checkpassword(self, _):
    """
    check the password
    """
    if self.api.get('setting.gets')('username'):
      if not self.password:
        self.api.get('output.client')(
                      '@CPlease set the email password for account: @M%s@w' \
                             % self.api.get('setting.gets')('username').replace('@', '@@'))

  def cmd_pw(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    Set the password for the smtp server
    @CUsage@w: pw @Y<password>@w
      @Ypassword@w    = the password for the smtp server
    """
    if len(args) == 1:
      self.password = args[0]
      return True, ['Password is set']

  def cmd_check(self, _=None):
    """
    check for all settings to be correct
    """
    msg = []
    items = []
    if not self.api.get('setting.gets')('server'):
      items.append('server')
    if not self.api.get('setting.gets')('port'):
      items.append('port')
    if not self.api.get('setting.gets')('username'):
      items.append('username')
    if not self.password:
      items.append('password')
    if not self.api.get('setting.gets')('from'):
      items.append('from')
    if not self.api.get('setting.gets')('to'):
      items.append('to')
    if items:
      msg.append('Please set the following:')
      msg.append(', '.join(items))
    else:
      msg.append('Everything is ready to send a test email')
    return True, msg

  def cmd_test(self, args):
    """
    @G%(name)s@w - @B%(cmdname)s@w
    Send a test email
    @CUsage@w: test @YSubject@x @Ymessage@x
      @Ysubject@w    = the subject of the email
      @Ymessage@w    = the message to put in the email
    """
    if len(args) == 2:
      subject = args[0]
      msg = args[1]
      if self.check():
        self.api.get('mail.send')(subject, msg)
        return True, ['Attempted to send test message',
                                'Please check your email']
      else:
        msg = []
        msg.append('There is not enough information to send mail')
        msg.append('Please check all info')
        return True, msg
