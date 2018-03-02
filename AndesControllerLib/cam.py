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
import numpy as np;

import log as log;
import ccd as ccd;
import binary as binary;
import shutter as shutter;

## What is to be expected to get as a camera response for each instruction of configuration.
# @note For internal use only.
_success_cache = '\x55'*4 + '\x00'*(512 - 4);     # It reads 512 bytes at once


## USB/DEBUG. In debug mode, the program doesn't try to connect to the real USB camera.
USB_MODE = True
VERBOSE  = True   # Print everything

if USB_MODE:
	import usb as usbEasy;
	usb = usbEasy.usb;


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
	# @param log A log context for logging.
	def __init__( \
		self,
		ccd       = ccd.CCD_230_42(),                  #CCD_47_10(),
		shutter   = shutter.Shutter(),
		log       = log.get_default_context(),
		formatter = binary.ByteCode() \
		):
		self.log         = log;
		self.ccd         = ccd;
		self.shutter     = shutter;
		self.formatter   = formatter;
		if USB_MODE:
			self.context = usb.USBContext();


	## Context manager interface __enter__ method.
	# It enters the libusb1 context. And prepares for event handling.
	# @param self An instance of Camera.
	def __enter__(self):
		if USB_MODE:
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
		if USB_MODE:
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

	## Enable regulators for debug
	# #Author: WAC
	# @warning Look at the Camera class warning
	#
	# @param self An instance of Camera
	# @param state state of the enable regulartor of the AC. if 
	# 		state= True, enable of regulator = 1;
	#		Default power regulators = on. 
	def camera_on(self,state= True):
		formatter = self.formatter;
		line = formatter.configurator_power_on(state);
		successful_transfers = 0;		
		
		if USB_MODE:
			with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
				port_write = dev.open_port(self._write_address);
				port_read  = dev.open_port(self._read_address);
				if VERBOSE:
					self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
				successful_transfers += port_write.write_sync(line);
				if VERBOSE:
					self.log.info( 'Sent [bytes]: ' + str(successful_transfers) )
				response = port_read.read_sync(1024)
				if VERBOSE:
					self.log.info( 'Received: ' + str(response) )
				if(response == _success_cache):
					self.log.info('Received SUCCESS !', 10);
				else:
					self.log.error('Received ERROR !: (len ' + str(len(response)) + ') ' + str(list(response[:4])), 1);
		else:
			self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
	




	# function to debbug DAC behaviour
	# created 03-02-18 by WAC
	#
	def set_specific_voltaje_DAC(self, label , value = 1 ):
		formatter = self.formatter;
		dac_p= self.ccd._default_bias_params[label];
		code = _dac_bias_volt_to_code(value,dac_p['voltType']);
		line = formatter.configurator_spi_bias_clocks(dac_p[´device´], dac_p[´ polarity´] , dac_p[´nbits´], dac_p[´address´], code );
		print line
		successful_transfers = 0;		
		
		# if USB_MODE:
		# 	with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
		# 		port_write = dev.open_port(self._write_address);
		# 		port_read  = dev.open_port(self._read_address);
		# 		if VERBOSE:
		# 			self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
		# 		successful_transfers += port_write.write_sync(line);
		# 		if VERBOSE:
		# 			self.log.info( 'Sent [bytes]: ' + str(successful_transfers) )
		# 		response = port_read.read_sync(1024)
		# 		if VERBOSE:
		# 			self.log.info( 'Received: ' + str(response) )
		# 		if(response == _success_cache):
		# 			self.log.info('Received SUCCESS !', 10);
		# 		else:
		# 			self.log.error('Received ERROR !: (len ' + str(len(response)) + ') ' + str(list(response[:4])), 1);
		# else:
		# 	self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
	




	## Configure the camera ccd for current self.ccd settings.
	#
	# @warning Look at the Camera class warning.
	#
	# @param self An instance of Camera.
	def configure(self):
		formatter = self.formatter;
		self.ccd.compile_configured_program();
		bytecode_lines = self.ccd.get_configuration_bytecode(formatter);
		expose_line = formatter.write_exposition_time(self.shutter.expose_time_ms);
		bytecode_lines.append(expose_line);
		successful_transfers = 0;

		if USB_MODE:
			with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
				port_write = dev.open_port(self._write_address);
				port_read  = dev.open_port(self._read_address);
				for line in bytecode_lines:
					if VERBOSE:
						self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
					successful_transfers += port_write.write_sync(line);
					if VERBOSE:
						self.log.info( 'Sent [bytes]: ' + str(successful_transfers) )
					response = port_read.read_sync(1024)
					if VERBOSE:
						self.log.info( 'Received: ' + str(response) )
					if(response == _success_cache):
						self.log.info('Received SUCCESS !', 10);
					else:
						self.log.error('Received ERROR !: (len ' + str(len(response)) + ') ' + str(list(response[:4])), 1);
		else:
			for line in bytecode_lines:
				self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );


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
		
		# Get command bytecodes for taking a picture
		# Write exposition time
		write_exposition_time_bytecode = formatter.write_exposition_time(self.shutter.expose_time_ms);

		# Get image (get the mode name then transform it to the sequencer memory address)
		stop_cleaning_mode_name    = self.ccd.get_stop_cleaning_mode_name();
		stop_cleaning_mode_address = self.ccd.get_configured_program().get_address(stop_cleaning_mode_name);
		get_image_mode_name        = self.ccd.get_test_serial_clocks_mode_name();
		#test: get_image_mode_name        = self.ccd.get_get_image_mode_name();
		get_image_mode_address     = self.ccd.get_configured_program().get_address(get_image_mode_name);
		get_image_bytecode         = formatter.get_image(stop_cleaning_mode_address, get_image_mode_address, open_shutter=self.shutter.open);

		# Take the picture
		raw_data   = None;
		resolution = self.ccd.get_image_resolution();

		# USB Mode
		if USB_MODE:
			with usbEasy.Device(vid = self._vid, pid = self._pid, context = self.context) as dev:
				port_write = dev.open_port(self._write_address);
				port_read  = dev.open_port(self._read_address, self.shutter.expose_time_ms + 500);

				# Set exposition time
				line = write_exposition_time_bytecode
				self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
				successful_transfer = port_write.write_sync(line);
				response0 = port_read.read_sync(1024);
				##if (response0 != _success_cache):
				##	self.log.error( 'Could not set exposition time, response: ' + str(response0) );
				##	return np.array([]);

				# Instance image reader
				port_read = dev.open_port(self._read_address, 100);
				async_reader = port_read.read_async(1024);

				# Send Get Image command (stop cleaning, start exposition, and retrieve the captured image)
				line = get_image_bytecode
				self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );
				successful_transfer = port_write.write_sync(line);

				self.log.info( 'Exposing for ' + str(self.shutter.expose_time_ms) + ' ms . . .' )

				# Receive image
				raw_data = async_reader();

				# End with (USB communication)

			# Format data received
			fmt = '>' + 'H'*(resolution[0]*resolution[1]);
			if len(raw_data) < struct.calcsize(fmt):
				raise RuntimeError( 'The amount of Received bytes (' + str(len(raw_data)) + ') ' + \
									'is less than the needed to form an image (' + str(struct.calcsize(fmt)) + ').');

			unpacked_data = struct.unpack(fmt, raw_data[:(2*resolution[0]*resolution[1])]);
			image = np.array(unpacked_data).reshape(resolution);
			return image

		# Debug Mode
		else:
			# Set exposition time
			line = write_exposition_time_bytecode
			self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );

			# Get image
			line = get_image_bytecode
			self.log.info( 'Sending: (len ' + str(len(line)) + ') '+ formatter.as_legacy_file([line]) );

			# Simulate exposition time
			self.log.info( 'Exposing for ' + str(self.shutter.expose_time_ms) + ' ms . . .' )
			time.sleep( self.shutter.expose_time_ms / 1000.0 )

			# Generate a random image
			image = np.zeros( resolution )
			for i in range(resolution[0]):
				for j in range(resolution[1]):
					if i < resolution[0]/2:
						if j > resolution[1]/2:
							image[i,j] = (i+j)%256
						else:
							image[i,j] = (-i+j)%256
					else:
						if j > resolution[1]/2:
							image[i,j] = (i-j)%256
						else:
							image[i,j] = (-i-j)%256
				#image[i,:] = i%256
			
			return image;


	## @var context
	# The camera libusb1 context. For internal use only.
	## @var log
	# The camera logging context. For internal use only.
	## @var ccd
	# The camera _CCD object, interact with it to configure image's parameters.
	# @see _CCD
	## @var on_connect_fn
	# The function to call when the camera is plugged-in. For internal use only.
	# @see set_camera_on_connect_function.
	## @var on_disconnect_fn
	# The function to call when the camera is unplugged. For internal use only.
	# @see set_camera_on_connect_function.
