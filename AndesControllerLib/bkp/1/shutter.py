#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package shutter
#
# Module to interact with the camera shutter
#
# It just contains and object with a shutter time member.

## Has shutter-related information.
class Shutter:

  ## Initializes a Shutter.
  #
  # @param self An instance of Shutter
  # @param expose_time_ms (int) The time (in miliseconds) the the picture will be exposed.
  # @param open (bool) Whenever to open or not the shutter at exposition time.
  def __init__(self, expose_time_ms = 30, open = True):
    self.expose_time_ms = expose_time_ms;
    self.open = True;

  ## @var expose_time_ms
  #  (int) The time (in miliseconds) the shutter is open.

  ## @var open
  #  (bool) Whenever to open or not the shutter at exposition time.
