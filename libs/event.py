"""
$Id$

This plugin handles events.
  You can register/unregister with events, raise events
"""
import inspect
from libs.api import API
from libs import utils

class Event(object):
  """
  a basic event class
  """
  def __init__(self, name, plugin):
    """
    init the class
    """
    self.name = name
    self.plugin = plugin

  def execute(self):
    """
    execute the event
    """
    self.func()

  def __str__(self):
    """
    return a string representation of the timer
    """
    return 'Event %-10s : %-15s' % (self.name, self.plugin)

