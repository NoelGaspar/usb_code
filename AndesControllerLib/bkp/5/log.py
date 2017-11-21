#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package log
# Basic logging
#
# This module enables having logging in different contexts. The default context
# just prints the messages to stdout, appending [INFO   ], [WARNING] or [ERROR  ] 
# depending on the message type.

import six as six;

## Holder of logging functions. Serves as a context for logging.
class _Log:
  ## Initializes a _Log
  #  @param self An instance of _Log.
  #  @note Use the methods log.get_default_context and log.new_context to get a logger.
  def __init__(self):

    self.info_fn    = lambda m : six.print_('[INFO   ] : ' + str(m));
    self.warning_fn = lambda m : six.print_('[WARNING] : ' + str(m));
    self.error_fn   = lambda m : six.print_('[ERROR  ] : ' + str(m));
    self.verbosity  = 5;

  ## Sets the info logging function.
  #  @param self An instance of _Log.
  #  @param info_fn A function(msg:str) to call every time the info method is invoked.
  def set_info_fn(self, info_fn):
    self.info_fn = info_fn;

  ## Sets the warning logging function.
  #  @param self An instance of _Log.
  #  @param warning_fn: A function(msg:str) to call every time the warning method is invoked.
  def set_warning_fn(self, warning_fn):
    self.warning_fn = warning_fn;

  ## Sets the error logging function.
  #  @param self An instance of _Log.
  #  @param error_fn A function(msg:str) to call every time the error method is invoked.
  def set_error_fn(self, error_fn):
    self.error_fn = error_fn;

  ## Calls the info function.
  #
  #  If self.verbosity level is less or equal than the verbosity parameter, the message is ommited.
  #
  #  @param self An instance of _Log.
  #  @param message (str) The message to display.
  #  @param verbosity (int) The verbosity level associated with this message.
  def info(self, message, verbosity=0):
    if(verbosity < self.verbosity):
      self.info_fn(message);

  ## Calls the warning function.
  #
  #  If self.verbosity level is less or equal than the verbosity parameter, the message is ommited.
  #
  #  @param self An instance of _Log.
  #  @param message (str) The message to display.
  #  @param verbosity (int) The verbosity level associated with this message.
  def warning(self, message, verbosity=0):
    if(verbosity < self.verbosity):
      self.warning_fn(message);

  ## Calls the error function.
  #
  #  If self.verbosity level is less or equal than the verbosity parameter, the message is ommited.
  #
  #  @param self An instance of _Log.
  #  @param message (str) The message to display.
  #  @param verbosity (int) The verbosity level associated with this message.
  def error(self, message, verbosity=0):
    if(verbosity < self.verbosity):
      self.error_fn(message);

  ## @var info_fn
  #  (function(msg:str)) The function that will be called on a self.info call.

  ## @var warning_fn
  #  (function(msg:str)) The function that will be called on a self.warning call.
  
  ## @var error_fn
  #  (function(msg:str)) The function that will be called on a self.error call.

  ## @var verbosity
  #  (int) Mimimum verbosity level of messages that will NOT be logged.

## The default _Log context.
_log = _Log();

## Obtains the default logging context.
# @returns The default logging context.
def get_default_context():
  return _log;

## Obtains new logging context.
# @returns A new logging context.
def new_context():
  return _Log();

## Calls the info function of the default logging context.
# @param message (str) The message to display.
# @param verbosity (int) The verbosity level associated with this message.
# @param context (log._Log) The context to call info on. Uses the default context if ommited.
def info(message, verbosity=0, context=_log):
  context.info(message, verbosity);

## Calls the warning function of the default logging context.
# @param message (str) The message to display.
# @param verbosity (int) The verbosity level associated with this message.
# @param context (log._Log) The context to call info on. Uses the default context if ommited.
def warning(message, verbosity=0, context=_log):
  context.warning(message, verbosity);

## Calls the error function of the default logging context.
# @param message (str) The message to display.
# @param verbosity (int) The verbosity level associated with this message.
# @param context (log._Log) The context to call info on. Uses the default context if ommited.
def error(message, verbosity=0, context=_log):
  context.error(message, verbosity);
