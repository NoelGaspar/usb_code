#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package json2
# Generic json packing/unpacking
#
# This module implemnets a json encoder and a decoder. Both will format python data structures
# as default. Classes will be encoded like dictonaries but appending the attribute
# __class__, for easy identification on decoding.
#
# @see JSONEncoder
# @see JSONDecoder

import json as json

## Just an alias for python's json.dumps;
dumps = json.dumps;

## Just an alias for python's json.loads;
loads = json.loads;

## This Encoder encodes just like python's json.JSONEncoder with some exceptions
# @see default 
class JSONEncoder(json.JSONEncoder):

  ## The encoding function.
  #
  # This function expects the object to contain a ._to_dict() that returns a dictionary of
  # it's json representation. If this function is not present and the encoder object has
  # the attribute fail_on_missing_interface set to true, the default encoding will be used.
  # If none of the above applies, the encoder will return the object dictionary plus a __class__
  # atribute, storing the class name of the object.
  #
  # @param self An instance of JSONEncoder
  # @param obj The object to be encoded.
  #
  def default(self, obj):
    if hasattr(obj,'_to_dict'):
      return obj._to_dict()
    elif hasattr(self, 'fail_on_missing_interface') and self.fail_on_missing_interface:
      return json.Encoder.default(self, obj)
    else:
      result = dict(obj.__dict__);
      result['__class__'] = obj.__class__.__name__;
      return result;
  # @var fail_on_missing_interface (optional) if set to true the encoder will use python's default encoding when the object does not have the expected ._to_dict() function.

## A dummy class just so JSONDecoder can instance an object before setting it's class.   
class _Dummy:
  pass;

## This Encoder encodes just like python's json.JSONDecoder with some exceptions
# @see __call__ 
class JSONDecoder(json.JSONDecoder):
  ## Initializes a decoder
  #
  # @param self An instance of JSONDecoder.
  # @param cls The class of the object to decode.
  #
  def __init__(self, cls = None):
    self.cls = cls;

  ## The decoding function.
  #
  # This function expects the class to contain a ._from_dict() that recieves a dictionary of
  # it's json representation. If this function is not present and the encoder object has
  # a cls attribute having the same name as the __class__ key in dct, a object will be created
  # overwriting its __dict__ with dct and __class__ with cls. If none of the above applies, 
  # dct will be returned as-is.
  #
  # @param self An instance of JSONDecoder
  # @param dct A dictionary containig the json data.
  #
  def __call__(self, dct):
    cls = self.cls;
    if(cls and hasattr(cls, '_from_dict')):
      return cls._from_dict(dct);
    else:
      if'__class__' in dct and dct['__class__'] == cls.__name__:
        result = _Dummy();
        result.__class__ = cls;
        del dct['__class__'];
        result.__dict__.update(dct);
        return result;
      return dct;
  ## @var cls
  # The class of the object to decode.

