"""
$Id$

TODO: test this extensively because of the fork.
"""
import smtplib, os
from datetime import datetime
from plugins import BasePlugin
from libs import exported


#these 5 are required
NAME = 'Mail'
SNAME = 'mail'
PURPOSE = 'hold mail settings and provide functions to send mail'
AUTHOR = 'Bast'
VERSION = 1

# This keeps the plugin from being autoloaded if set to False
AUTOLOAD = True


class Plugin(BasePlugin):
  """
  a plugin to send email
  """
  def __init__(self, name, sname, filename, directory, importloc):
    """
    initialize the instance
    """
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.password = ''
    self.events['client_connected'] = {'func':self.checkpassword}
    self.cmds['password'] = {'func':self.cmd_pw, 'shelp':'set the password'}
    self.cmds['test'] = {'func':self.cmd_test, 'shelp':'send a test email'}
    self.exported['send'] = {'func':self.send}
    self.addsetting('server', '', str, 'the smtp server to send mail through')
    self.addsetting('port', '', int, 'the port to use when sending mail')
    self.addsetting('username', '', str, 'the username to connect as')
    self.addsetting('to', '', str, 'the address to send mail to')
    self.addsetting('from', '', str, 'the address to send mail from')
    self.addsetting('ssl', '', bool, 
                          'set this to True if the connection will use ssl')
    
  def check(self):
    """
    check to make sure all data need to send mail is available
    """
    if not self.variables['server'] or \
       not self.variables['port'] or \
       not self.variables['username'] or \
       not self.password or \
       not self.variables['from'] or \
       not self.variables['to']:
      return False
    
    return True
    
  def send(self, subject, msg):
    """
    send an email
      argument 1: the name of the event
      argument 2: the argument list
    """    
    if self.check():
      senddate = datetime.strftime(datetime.now(), '%Y-%m-%d')
      mhead = """Date: %s
From: %s
To: %s
Subject: %s
X-Mailer: My-Mail
%s""" % (senddate, 
          self.variables['from'], self.variables['to'], subject, msg)
      try:
        pid = os.fork()
        if pid == 0:
          server = '%s:%s' % (self.variables['server'], 
                                    self.variables['port'])
          server = smtplib.SMTP(server)
          if 'ssl' in self.variables and self.variables['ssl']:
            server.starttls()
          server.login(self.variables['username'], self.password)
          server.sendmail(self.variables['from'], self.variables['to'], mhead)
          server.quit()
          os._exit(0)
      except:
        server = '%s:%s' % (self.variables['server'], self.variables['port'])
        server = smtplib.SMTP(server)
        if 'ssl' in self.variables and self.variables['ssl']:
          server.starttls()
        server.login(self.variables['username'], self.password)
        server.sendmail(self.variables['from'], self.variables['to'], mhead)
        server.quit()
      
  def checkpassword(self, args):
    """
    check the password
    """
    if 'username' in self.variables:
      if not self.password:
        exported.sendtoclient(
                        'Please set the email password for account: %s' \
                                      % self.variables['username'])
        
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

  def load(self):
    """
    load the plugin
    """
    BasePlugin.load(self)
    if self.variables['username'] != '':
      exported.sendtoclient('Please set the mail password')
      
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
        self.send(subject, msg)
        return True, ['Attempted to send test message', 
                                'Please check your email']
      else:
        msg = []
        msg.append('There is not enough information to send mail')
        msg.append('Please check all info')
        return True, msg
    