"""
$Id$

this module holds utility functions that are seperate from the internal
"""
class DotDict(dict):
  """
  a class to create dictionaries that can be accessed like dict.key
  """
  def __getattr__(self, attr):
    """
    override __getattr__ to use get
    """
    return self.get(attr, DotDict())
  __setattr__ = dict.__setitem__
  __delattr__ = dict.__delitem__

