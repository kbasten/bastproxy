"""
$Id$

TODO: test this extensively because of the fork.
"""
import smtplib, os
import sys
from datetime import datetime
from plugins import BasePlugin
from libs import utils, exported
from libs.timing import timeit
from libs.persistentdict import PersistentDict


#these 5 are required
name = 'Mail'
sname = 'mail'
purpose = 'hold mail settings and provide functions to send mail'
author = 'Bast'
version = 1

# This keeps the plugin from being autoloaded if set to False
autoload = True


class Plugin(BasePlugin):
  def __init__(self, name, sname, filename, directory, importloc):
    BasePlugin.__init__(self, name, sname, filename, directory, importloc)
    self.password = ''
    self.events['client_connected'] = {'func':self.checkpassword}
    self.cmds['password'] = {'func':self.cmd_pw, 'shelp':'set the password'}
    self.cmds['test'] = {'func':self.cmd_test, 'shelp':'send a test email'}
    self.addsetting('server', '', str, 'the smtp server to send mail through')
    self.addsetting('port', '', int, 'the port to use when sending mail')
    self.addsetting('username', '', str, 'the username to connect as')
    self.addsetting('to', '', str, 'the address to send mail to')
    self.addsetting('from', '', str, 'the address to send mail from')
    self.addsetting('ssl', '', bool, 'set this to True if the connection will use ssl')
    
  def check(self):
    if not self.variables['server']:
      return False
    
    if not self.variables['port']:
      return False

    if not self.variables['username']:
      return False

    if not self.password:
      return False

    if not self.variables['from']:
      return False

    if not self.variables['to']:
      return False
      
    return True
    
  def send(self, subject, msg):
    """send an email
argument 1: the name of the event
argument 2: the argument list"""    
    if self.check():
      senddate=datetime.strftime(datetime.now(), '%Y-%m-%d')
      m="Date: %s\r\nFrom: %s\r\nTo: %s\r\nSubject: %s\r\nX-Mailer: My-Mail\r\n\r\n%s" % (senddate, 
          self.variables['from'], self.variables['to'], subject, msg)
      try:
        pid = os.fork()
        if pid == 0:
          server = '%s:%s' % (self.variables['server'], self.variables['port'])
          server = smtplib.SMTP(server)
          if 'ssl' in self.variables and self.variables['ssl']:
            server.starttls()
          server.login(self.variables['username'], self.password)
          server.sendmail(self.variables['from'], self.variables['to'], m)
          server.quit()
          os._exit(0)
      except:
        server = '%s:%s' % (self.variables['server'], self.variables['port'])
        server = smtplib.SMTP(server)
        if 'ssl' in self.variables and self.variables['ssl']:
          server.starttls()
        server.login(self.variables['username'], self.password)
        server.sendmail(self.variables['from'], self.variables['to'], m)
        server.quit()
      
  def checkpassword(self, args):
    if 'username' in self.variables:
      if not self.password:
        exported.sendtoclient('Please set the email password for account: %s' % self.variables['username'])
        
  def cmd_pw(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  Set the password for the smtp server
  @CUsage@w: pw @Y<password>@w
    @Ypassword@w    = the password for the smtp server"""    
    if len(args) == 1:
      self.password = args[0]
      return True, ['Password is set']

  def load(self):
    BasePlugin.load(self)
    if self.variables['username']:
      exported.sendtoclient('Please set the mail password')
      
    exported.mail = utils.dotdict()
    exported.mail['send'] = self.send
    
  def cmd_test(self, args):
    """@G%(name)s@w - @B%(cmdname)s@w
  Send a test email
  @CUsage@w: test @YSubject@x @Ymessage@x
    @Ysubject@w    = the subject of the email
    @Ymessage@w    = the message to put in the email"""      
    if len(args) == 2:
      subject = args[0]
      msg = args[1]
      if self.check():
        self.send(subject, msg)
        return True, ['Attempted to send test message', 'Please check your email']
      else:
        msg = []
        msg.append('There is not enough information to send mail, please check all info')
        return True, msg
    