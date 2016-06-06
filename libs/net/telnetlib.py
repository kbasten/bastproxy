"""
TELNET client class.

Based on RFC 854: TELNET Protocol Specification, by J. Postel and
J. Reynolds
"""

from __future__ import print_function

import asyncore
import socket

from libs.api import API

__all__ = ["Telnet"]

# Tunable parameters
# 1 = a lot of debug
# ..
# 5 = less
DEBUGLEVEL = 3

# Telnet protocol defaults
TELNET_PORT = 23

# Telnet protocol characters (don't change)
IAC = chr(255) # "Interpret As Command"
DONT = chr(254)
DO = chr(253)
WONT = chr(252)
WILL = chr(251)
THENULL = chr(0)

SE = chr(240)  # Subnegotiation End
NOP = chr(241)  # No Operation
DM = chr(242)  # Data Mark
BRK = chr(243)  # Break
IP = chr(244)  # Interrupt process
AO = chr(245)  # Abort output
AYT = chr(246)  # Are You There
EC = chr(247)  # Erase Character
EL = chr(248)  # Erase Line
GA = chr(249)  # Go Ahead
SB = chr(250)  # Subnegotiation Begin


# Telnet protocol options code (don't change)
# These ones all come from arpa/telnet.h
BINARY = chr(0) # 8-bit data path
ECHO = chr(1) # echo
RCP = chr(2) # prepare to reconnect
SGA = chr(3) # suppress go ahead
NAMS = chr(4) # approximate message size
STATUS = chr(5) # give status
TM = chr(6) # timing mark
RCTE = chr(7) # remote controlled transmission and echo
NAOL = chr(8) # negotiate about output line width
NAOP = chr(9) # negotiate about output page size
NAOCRD = chr(10) # negotiate about CR disposition
NAOHTS = chr(11) # negotiate about horizontal tabstops
NAOHTD = chr(12) # negotiate about horizontal tab disposition
NAOFFD = chr(13) # negotiate about formfeed disposition
NAOVTS = chr(14) # negotiate about vertical tab stops
NAOVTD = chr(15) # negotiate about vertical tab disposition
NAOLFD = chr(16) # negotiate about output LF disposition
XASCII = chr(17) # extended ascii character set
LOGOUT = chr(18) # force logout
BM = chr(19) # byte macro
DET = chr(20) # data entry terminal
SUPDUP = chr(21) # supdup protocol
SUPDUPOUTPUT = chr(22) # supdup output
SNDLOC = chr(23) # send location
TTYPE = chr(24) # terminal type
EOR = chr(25) # end or record
TUID = chr(26) # TACACS user identification
OUTMRK = chr(27) # output marking
TTYLOC = chr(28) # terminal location number
VT3270REGIME = chr(29) # 3270 regime
X3PAD = chr(30) # X.3 PAD
NAWS = chr(31) # window size
TSPEED = chr(32) # terminal speed
LFLOW = chr(33) # remote flow control
LINEMODE = chr(34) # Linemode option
XDISPLOC = chr(35) # X Display Location
OLD_ENVIRON = chr(36) # Old - Environment variables
AUTHENTICATION = chr(37) # Authenticate
ENCRYPT = chr(38) # Encryption option
NEW_ENVIRON = chr(39) # New - Environment variables
# the following ones come from
# http://www.iana.org/assignments/telnet-options
# Unfortunately, that document does not assign identifiers
# to all of them, so we are making them up
TN3270E = chr(40) # TN3270E
XAUTH = chr(41) # XAUTH
CHARSET = chr(42) # CHARSET
RSP = chr(43) # Telnet Remote Serial Port
COM_PORT_OPTION = chr(44) # Com Port Control Option
SUPPRESS_LOCAL_ECHO = chr(45) # Telnet Suppress Local Echo
TLS = chr(46) # Telnet Start TLS
KERMIT = chr(47) # KERMIT
SEND_URL = chr(48) # SEND-URL
FORWARD_X = chr(49) # FORWARD_X
PRAGMA_LOGON = chr(138) # TELOPT PRAGMA LOGON
SSPI_LOGON = chr(139) # TELOPT SSPI LOGON
PRAGMA_HEARTBEAT = chr(140) # TELOPT PRAGMA HEARTBEAT
EXOPL = chr(255) # Extended-Options-List
NOOPT = chr(0)

# reverse lookup allowing us to see what's going on more easily
# when we're debugging.
# for a list of telnet options: http://www.freesoft.org/CIE/RFC/1700/10.htm
CODES = {255: "IAC",
         254: "DON'T",
         253: "DO",
         252: "WON'T",
         251: "WILL",
         250: "SB",
         249: "GA",
         240: "SE",
         239: "TELOPT_EOR",
         0:   "<IS>",
         1:   "[<ECHO> or <SEND/MODE>]",
         3:   "<SGA>",
         5:   "STATUS",
         24:  "<TERMTYPE>",
         25:  "<EOR>",
         31:  "<NegoWindoSize>",
         32:  "<TERMSPEED>",
         34:  "<Linemode>",
         35:  "<XDISPLAY>",
         36:  "<ENV>",
         39:  "<NewENV>",
        }


def addcode(code, codestr):
  """
  add a code into the CODE table
  """
  CODES[code] = codestr


class Telnet(asyncore.dispatcher):
  # have to keep up with a lot of things, so disabling pylint warning
  # pylint: disable=too-many-instance-attributes
  """
  Telnet interface class.

  read_sb_data()
      Reads available data between SB ... SE sequence. Don't block.

  set_option_negotiation_callback(callback)
      Each time a telnet option is read on the input flow, this callback
      (if set) is called with the following parameters :
      callback(command, option)
          option will be chr(0) when there is no option.
      No other action is done afterwards by telnetlib.

  """
  def __init__(self, host=None, port=0, sock=None):
    """
    Constructor.

    When called without arguments, create an unconnected instance.
    With a hostname argument, it connects the instance; port number
    and timeout are optional.
    """
    if sock:
      asyncore.dispatcher.__init__(self, sock)
    else:
      asyncore.dispatcher.__init__(self)
    self.sock = sock
    self.debuglevel = DEBUGLEVEL
    self.host = host
    self.port = port
    self.rawq = ''
    self.api = API()
    self.irawq = 0
    self.cookedq = ''
    self.eof = 0
    self.iacseq = '' # Buffer for IAC sequence.
    self.sbse = 0 # flag for SB and SE sequence.
    self.sbdataq = ''
    self.outbuffer = ''
    self.options = {}
    self.option_callback = self.handleopt
    self.option_handlers = {}
    self.connected = False
    self.ttype = 'Unknown'
    self.debug_types = []

  def handleopt(self, command, option):
    """
    handle an option
    """
    self.msg('Command:', ord(command), 'with option', ord(option), level=2)
    subc = NOOPT
    self.msg('SE', command == SE, level=2)

    if command == SE:
      if len(self.sbdataq) > 0:
        subc = self.sbdataq[0]
      self.msg('SE: got subc', ord(subc), level=2)

    if ord(option) in self.option_handlers:
      self.msg('calling handleopt for', ord(option), level=2)
      self.option_handlers[ord(option)].handleopt(command, '')
    elif command == SE and ord(subc) in self.option_handlers:
      self.msg('calling handleopt with SE for', ord(subc), level=2)
      self.option_handlers[ord(subc)].handleopt(SE, self.sbdataq[1:])
    elif command == WILL:
      self.msg('Sending IAC WONT %s' % ord(option), level=2)
      self.send(IAC + WONT + option)
    elif command == DO:
      self.msg('Sending IAC DONT %s' % ord(option), level=2)
      self.send(IAC + DONT + option)
    elif command == DONT or command == WONT:
      pass
    else:
      self.msg('Fallthrough:', ord(command), 'with option',
               option, ord(option), level=2)
      if command == SE:
        self.msg('sbdataq: %r' % self.sbdataq, level=2)

      self.msg('length of sbdataq', len(self.sbdataq), level=2)
      if len(self.sbdataq) == 1:
        self.msg('should look at the sbdataq', ord(self.sbdataq), level=2)
      else:
        self.msg('should look at the sbdataq', self.sbdataq, level=2)

  def readdatafromsocket(self):
    """
    read 1024 bytes from the socket
    """
    buf = self.recv(1024)
    self.msg("recv %r" % buf)
    return buf

  def __del__(self):
    """
    Destructor -- close the connection.
    """
    self.close()

  def msg(self, *args, **kwargs):
    """
    Print a debug message, when the debug level is > 0.

    If extra arguments are present, they are substituted in the
    message using the standard string formatting operator.

    """
    mtype = 'net'
    if 'level' not in kwargs:
      kwargs['level'] = 1
    if 'mtype' in kwargs:
      mtype = kwargs['mtype']
    if kwargs['level'] >= self.debuglevel or mtype in self.debug_types:
      self.api('send.msg')('Telnet(%-15s - %-5s %-7s %-5s): ' % \
                          (self.host, self.port, self.ttype, mtype), args)

  def set_debuglevel(self, debuglevel):
    """
    Set the debug level.

    The higher it is, the more debug output you get (on sys.stdout).

    """
    self.debuglevel = debuglevel

  def doconnect(self, hostname, hostport):
    """
    connect to a host and port
    """
    self.host = hostname
    self.port = hostport
    self.msg('doconnect')
    self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
    self.set_reuse_addr()
    self.connect((self.host, self.port))
    self.connected = True
    for i in self.option_handlers:
      self.option_handlers[i].onconnect()

  def handle_close(self):
    """
    Close the connection.
    """
    self.msg('closing connection')
    self.connected = False
    self.close()
    self.options = {}
    self.eof = 1
    self.iacseq = ''
    self.sbse = 0

  def handle_write(self):
    """
    write to a connection
    """
    self.msg('Handle_write', self.outbuffer)
    sent = self.send(self.outbuffer)
    self.outbuffer = self.outbuffer[sent:]

  def addtooutbuffer(self, outbuffer, raw=False):
    """
    Write a string to the socket, doubling any IAC characters.

    Can block if the connection is blocked.  May raise
    socket.error if the connection is closed.

    """
    self.msg('adding to buffer', raw, outbuffer)
    if not raw and IAC in outbuffer:
    #if not raw and outbuffer.find(IAC) >= 0:
      outbuffer = outbuffer.replace(IAC, IAC+IAC)

    outbuffer = self.convert_outdata(outbuffer)

    self.outbuffer = self.outbuffer + outbuffer

  def convert_outdata(self, outbuffer):
    """
    override this to convert something from the outbuffer
    """
    # this function can be overridden so disabling pylint warning
    # pylint: disable=no-self-use
    return outbuffer

  def writable(self):
    """
    find out if the connection has data to write
    """
    #self.msg( 'writable', self.ttype, len(self.outbuffer) > 0)
    return len(self.outbuffer) > 0

  def handle_error(self):
    """
    hand an error
    """
    self.api('send.traceback')("Telnet error: %s" % self.ttype)

  def handle_read(self):
    """
    Read readily available data.

    Raise EOFError if connection closed and no cooked data
    available.  Return '' if no cooked data available otherwise.
    Don't block unless in the midst of an IAC sequence.

    """
    self.process_rawq()
    self.fill_rawq()
    self.process_rawq()

  def getdata(self):
    """
    Return any data available in the cooked queue.

    Raise EOFError if connection closed and no data available.
    Return '' if no cooked data available otherwise.  Don't block.

    """
    if not self.connected:
      return None
    buf = self.cookedq
    self.cookedq = ''
    return buf

  def read_sb_data(self):
    """
    Return any data available in the SB ... SE queue.

    Return '' if no SB ... SE available. Should only be called
    after seeing a SB or SE command. When a new SB command is
    found, old unread SB data will be discarded. Don't block.

    """
    buf = self.sbdataq
    self.sbdataq = ''
    return buf

  def set_option_negotiation_callback(self, callback):
    """
    Provide a callback function called after each receipt of a telnet option.
    """
    self.option_callback = callback

  def process_rawq(self):
    """
    Transfer from raw queue to cooked queue.

    Set self.eof when connection is closed.  Don't block unless in
    the midst of an IAC sequence.

    """
    # parsing a string with subdata isn't easy, so disabling pylint warning
    # pylint: disable=too-many-nested-blocks,too-many-branches,too-many-statements
    buf = ['', '']
    try:
      while self.rawq:
        tchar = self.rawq_getchar()
        if not self.iacseq:
          if tchar == THENULL:
            continue
          if tchar == "\021":
            continue
          if tchar != IAC:
            buf[self.sbse] = buf[self.sbse] + tchar
            continue
          else:
            self.iacseq += tchar
        elif len(self.iacseq) == 1:
          # 'IAC: IAC CMD [OPTION only for WILL/WONT/DO/DONT]'
          if tchar in (DO, DONT, WILL, WONT):
            self.iacseq += tchar
            continue

          self.iacseq = ''
          if tchar == IAC:
            buf[self.sbse] = buf[self.sbse] + tchar
          else:
            if tchar == SB: # SB ... SE start.
              self.sbse = 1
              self.sbdataq = ''
            elif tchar == SE:
              self.sbse = 0
              self.sbdataq = self.sbdataq + buf[1]
              buf[1] = ''
              if len(self.sbdataq) == 1:
                self.msg('proccess_rawq: got an SE',
                         ord(self.sbdataq), level=2)
              else:
                self.msg('proccess_rawq: got an SE (2)',
                         self.sbdataq, level=2)
            if self.option_callback:
              # Callback is supposed to look into
              # the sbdataq
              self.option_callback(tchar, NOOPT)
            else:
              # We can't offer automatic processing of
              # suboptions. Alas, we should not get any
              # unless we did a WILL/DO before.
              self.msg('IAC %d not recognized' % ord(tchar))
        elif len(self.iacseq) == 2:
          cmd = self.iacseq[1]
          self.iacseq = ''
          opt = tchar
          if cmd in (DO, DONT):
            self.msg('IAC %s %d' %
                     (cmd == DO and 'DO' or 'DONT', ord(opt)))
            if self.option_callback:
              self.option_callback(cmd, opt)
            else:
              self.msg('Sending IAC WONT %s' % ord(opt), level=2)
              self.send(IAC + WONT + opt)
          elif cmd in (WILL, WONT):
            self.msg('IAC %s %d' %
                     (cmd == WILL and 'WILL' or 'WONT', ord(opt)))
            if self.option_callback:
              self.option_callback(cmd, opt)
          else:
            self.msg('Sending IAC DONT %s' % ord(opt))
            self.send(IAC + DONT + opt)
    except EOFError: # raised by self.rawq_getchar()
      self.iacseq = '' # Reset on EOF
      self.sbse = 0

    self.cookedq = self.cookedq + buf[0]
    self.sbdataq = self.sbdataq + buf[1]

  def rawq_getchar(self):
    """
    Get next char from raw queue.

    Block if no data is immediately available.  Raise EOFError
    when connection is closed.

    """
    if not self.rawq:
      self.fill_rawq()
      if self.eof:
        raise EOFError
    tchar = self.rawq[self.irawq]
    self.irawq = self.irawq + 1
    if self.irawq >= len(self.rawq):
      self.rawq = ''
      self.irawq = 0
    return tchar

  def fill_rawq(self):
    """
    Fill raw queue from exactly one recv() system call.

    Block if no data is immediately available.  Set self.eof when
    connection is closed.

    """
    if self.irawq >= len(self.rawq):
      self.rawq = ''
      self.irawq = 0
    # The buffer size should be fairly small so as to avoid quadratic
    # behavior in process_rawq() above
    buf = self.readdatafromsocket()
    #print 'fill_rawq', self.ttype, self.host, self.port, 'received', buf
    self.eof = (not buf)
    self.rawq = self.rawq + buf
    self.msg('rawq', self.rawq)

