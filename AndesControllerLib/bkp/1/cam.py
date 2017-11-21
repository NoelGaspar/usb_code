#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package cam
# High level camera interaction
#
# Use this module to interact with the Andes Controller
#


import time as time;
import six as six;
import struct as struct;
import numpy as num;

from . import usb as usbEasy;
usb = usbEasy.usb;

import log as log;
import ccd as ccd;
import binary as binary;
import temperature as temperature;
import shutter as shutter;

## What is to be expected to get as a camera response for each instruction of configuration.
# @note For internal use only.
_success_cache = '\x55'*4 + '\x00'*(512 - 4);

## Wrapper for camera comunication
#
# @note This object must be used in a python's context fashion. See <a href='https://www.python.org/dev/peps/pep-0343/'>Context managers</a>.
#
# @warning Do not call any method that communicates with the camera (configure, configure_temperature, take_picture, get_current_temprature) while there is another communication method executing. To prevent this just avoid having multiple threads using the camera at the same time.
#
class Camera:

  ## The USB vendor ID of the camera.
  _vid = 0x04B4;
  ## The USB product ID of the camera.
  _pid = 0x00F1;

  ## The USB bulk endpoint used for reading data from the camera.
  _read_address = 0x81;
  ## The USB bulk endpoint used for writing data into camera.
  _write_address = 0x01;

  ## The USB interface number the camera uses
  _interface = 0;

  ## Initializes a new camera
  # @param self An instance of Camera.
  # @param ccd A _CCD object to manage ccd configuration and usage.
  # @param temperature A TemperatureControl object to manage temperature configuration and usage.
  # @param log A log context for logging.
  def __init__(\
    self,
    ccd         = ccd.CCD_230_42(),                  #CCD_47_10(),
    temperature = temperature.TemperatureControl(),
    shutter     = shutter.Shutter(),
    log         = log.get_default_context(),
    formatter   = binary.ByteCode() \
  ):
    self.context = usb.USBContext();
    self.log = log;
    self.ccd = ccd;
    self.shutter = shutter;
    self.temperature = temperature;
    self.formatter = formatter;

  ## Context manager interface __enter__ method.
  # It enters the libusb1 context. And prepares for event handling.
  # @param self An instance of Camera.
  def __enter__(self):
    self.context = self.context.__enter__();
    
    def event_handling(context, device, event):
        self._handle_usb_event(context, device, event);

    if self.context.hasCapability(usb.CAP_HAS_HOTPLUG):
      opaque = self.context.hotplugRegisterCallback(event_handling);

    return self;

  ## Context manager interface __exit__ method.
  # It exits the libusb1 context.
  # @param self An instance of Camera.
  # @param exception_type The type of the raised exception. None if no error happened.
  # @param exception_value The object of the raised exception. None if no error happened.
  # @param traceback The stack information of the raised exception. None if no error happened.
  def __exit__(self, exception_type, exception_value, traceback):
    self.context.__exit__(exception_type, exception_value, traceback);
    return self;

  ## Function to call when the camera is plugged-in.
  # @param self An instance of Camera.
  # @param fn A parameter-less function (or an object-bounded function with just 'self').
  def set_camera_on_connect_function(self, fn):
    self.on_connect_fn = fn;

  ## Function to call when the camera is unplugged.
  # @param self An instance of Camera.
  # @param fn A parameter-less function (or an object-bounded function with just 'self').
  def set_camera_on_disconnect_function(self, fn):
    self.on_disconnect_fn = fn;

  ## Function called every time libusb1 emits an event.
  #
  # If you want to subscribe to camera plugging/unplugging
  # see set_camera_on_connect_function and set_camera_on_disconnect_function.
  #
  # @param self An instance of Camera.
  # @param context The current libusb1 context.
  # @param device The USB device that emitted the event.
  # @param event The event emitted.
  def _handle_usb_event(self, context, device, event):
    if(device.getVendorID() == self._vid and device.getProductID() == self._pid):
      if(event == usb.HOTPLUG_EVENT_DEVICE_ARRIVED):
        if(hasattr(self, 'on_connect_fn')):
          self.on_connect_fn();
      elif(event == usb.HOTPLUG_EVENT_DEVICE_LEFT):
        if(hasattr(self, 'on_disconnect_fn')):
          self.on_disconnect_fn();

  ## Configure the camera ccd for current self.ccd settings
  #
  # @warning Look at the Camera class warning
  #
  # @param self An instance of Camera.
  def configure(self):
    formatter = self.formatter;
    self.ccd.compile_configured_program();
    bytecode_lines = self.ccd.get_configuration_bytecode(formatter);
    expose_line = formatter.seq_set_exposition_time(self.shutter.expose_time_ms);
    bytecode_lines.append(expose_line);

    successful_transfers = 0;

    with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
      port_write = dev.open_port(self._write_address);
      port_read = dev.open_port(self._read_address);
      for line in bytecode_lines:
        self.log.info('Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]), 4);
        successful_transfers += port_write.write_sync(line);
        response = port_read.read_sync(512);

        if(response == _success_cache):
          self.log.info('Received SUCCESS', 10);              
        else:
          self.log.error('Received: (len ' + str(len(response)) + ') ' + str(list(response[:4])), 1);

  ## Get the camera temperatures
  #
  # @warning Look at the Camera class warning
  #
  # @param self An instance of Camera.
  #
  # @returns ({str:float..}) An dict of all the sensed temperatures.
  def get_temperatures(self):
    formatter = self.formatter;
    bytecode_lines = self.temperature.get_temperature_bytecode(formatter);

    result = [];
    with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
      port_write = dev.open_port(self._write_address);
      port_read = dev.open_port(self._read_address);
      for line in bytecode_lines:
        self.log.info('Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]), 10);
        successful_transfer = port_write.write_sync(line);
        response = port_read.read_sync(512);
        result.append(response);

    to_return = {};
    if(len(result) != 1):
      self.log.error('Received different number of temperature reads ( ' + str(len(result)) + ' ) than expected (1).');
    else:
      self.log.info('Received: (len ' + str(len(result)) + ')', 10);
      to_return['CCD'] = struct.unpack(formatter.endianess + 'i', result[0][:4])[0];
      to_return['CCD'] = self.temperature.temperature_code_to_celcius(to_return['CCD']);

    return to_return;

  ## Configure the camera temperature control for current self.temperature settings
  #
  # @warning Look at the Camera class warning
  #
  # @param self An instance of Camera.
  def configure_temperature(self):
    formatter = self.formatter;
    bytecode_lines = self.temperature.get_configuration_bytecode(formatter);

    successful_transfers = 0;
    with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
      port_write = dev.open_port(self._write_address);
      port_read = dev.open_port(self._read_address);
      for line in bytecode_lines:
        self.log.info('Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]), 10);
        successful_transfers += port_write.write_sync(line);
        response = port_read.read_sync(512);

        if(response == _success_cache):
          self.log.info('Received SUCCESS', 10);              
        else:
          self.log.error('Received: (len ' + str(len(response)) + ') ' + str(response), 1);

  ## Takes a picture using the ccd's settings.
  #
  # @warning You must first call configure to ensure correct ccd operation.
  # @warning Look at the Camera class warning
  #
  # @param self An instance of Camera.
  #
  # @returns A numpy array containing the image.
  def take_picture(self):
    formatter = binary.ByteCode();
    
    take_photo_mode = self.ccd.get_take_photo_mode_name();
    take_photo_mode_address = self.ccd.get_configured_program().get_address(take_photo_mode);
    take_photo_bytecode = formatter.seq_take_photo(take_photo_mode_address);

    stop_cleaning_mode = self.ccd.get_stop_cleaning_mode_name();
    stop_cleaning_address = self.ccd.get_configured_program().get_address(stop_cleaning_mode);
    stop_cleaning_bytecode = formatter.seq_move_to_mode(stop_cleaning_address);
    expose_bytecode = formatter.seq_expose(self.shutter.open);
    expose_line = formatter.seq_set_exposition_time(self.shutter.expose_time_ms);

    raw_data = None;
    with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
      port_write = dev.open_port(self._write_address);
      port_read = dev.open_port(self._read_address, self.shutter.expose_time_ms + 500);

      successful_transfer = port_write.write_sync(expose_line); # Set Exposition time
      response0 = port_read.read_sync(512);

      successful_transfer = port_write.write_sync(stop_cleaning_bytecode);
      response1 = port_read.read_sync(512);

      successful_transfer = port_write.write_sync(expose_bytecode);
      response2 = port_read.read_sync(512);

      port_read = dev.open_port(self._read_address, 100);
      async_reader = port_read.read_async(512);

      if(response1 != _success_cache):
        self.log.error('Could not send expose instruction, response: ' + str(_success_cache));
        return num.array([]);
      if(response2 != _success_cache):
        self.log.error('Could not send expose instruction, response: ' + str(_success_cache));
        return num.array([]);

      successful_transfer = port_write.write_sync(take_photo_bytecode);
      raw_data = async_reader();
    
    resolution = self.ccd.get_image_resolution();
    fmt = '>' + 'H'*(resolution[0]*resolution[1]);
    if len(raw_data) < struct.calcsize(fmt):
      raise RuntimeError( 'The amount of Received bytes (' + str(len(raw_data)) + ') ' + \
                          'is less than the needed to form an image (' + str(struct.calcsize(fmt)) + ').');

    unpacked_data = struct.unpack(fmt, raw_data[:(2*resolution[0]*resolution[1])]);
    image = num.array(unpacked_data).reshape(resolution);
    return image;

  ## @var context
  # The camera libusb1 context. For internal use only.
  ## @var log
  # The camera logging context. For internal use only.
  ## @var ccd
  # The camera _CCD object, interact with it to configure image's parameters.
  # @see _CCD
  ## @var temperature
  # The camera TemperatureControl object, interact with it to configure temperature control.
  # @see TemperatureControl
  ## @var on_connect_fn
  # The function to call when the camera is plugged-in. For internal use only.
  # @see set_camera_on_connect_function.
  ## @var on_disconnect_fn
  # The function to call when the camera is unplugged. For internal use only.
  # @see set_camera_on_connect_function.
