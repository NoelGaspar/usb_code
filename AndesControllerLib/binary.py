#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package binary
#
# Binary data formatting for USB transfers
#
# This module exposes the ByteCode class to generate Andes Controller USB bytecode.

import struct as struct;
import six as six;


## Generates bytecode ready for USB communication usage.
# Handles endianess and communication protocol internally.
class ByteCode:

	## Initializes a ByteCode.
	#
	# @param self An instance of ByteCode
	# @param endianess (str) A python's struct endianess format character. This is the endianess that will be used on USB communication.
	def __init__(self, endianess= '<'):
		# Byte order
		self.endianess                = endianess;    # <: little endian

		# Init word
		self._init                    = self.int_to_byte_list(0x029A);

		# Module select codes
		self._configurator_mod_index  = self.int_to_byte_list(0);
		self._acquisition_mod_index   = self.int_to_byte_list(1);
		self._pvm_mod_index           = self.int_to_byte_list(2);

		# Sub-module select codes
		self._configurator_powermanag_index    = 0
		self._configurator_spivideo_index      = 1
		self._configurator_spibiasclocks_index = 2
		self._acquisition_sequencer_index      = 0
		self._pvm_uartmicro_index              = 0

		# Instructions codes
		self._configurator_powermanag_readpowerenablereg_inst  = 0
		self._configurator_powermanag_enablepower_inst         = 1
		self._configurator_powermanag_resetdacs_inst           = 2
		self._configurator_spivideo_communicate_inst           = 0
		self._configurator_spibiasclocks_communicate_inst      = 0

		self._acquisition_sequencer_getimage_inst              = 0
		self._acquisition_sequencer_writeseqmem_inst           = 1
		self._acquisition_sequencer_enableseq_inst             = 2
		self._acquisition_sequencer_disableseq_inst            = 3
		self._acquisition_sequencer_writeexpotime_inst         = 4
		self._acquisition_sequencer_getpxlsch1_inst            = 5
		self._acquisition_sequencer_getpxlsch3_inst            = 6
		self._acquisition_sequencer_getdatach1_inst            = 7
		self._acquisition_sequencer_getdatach3_inst            = 8
		self._acquisition_sequencer_tstseqon_inst              = 9
		self._acquisition_sequencer_tstseqoff_inst             = 10

		self._pvm_uartmicro_senddata_inst                      = 0
		self._pvm_uartmicro_readmemory_inst                    = 1

		# General response codes
		self._default_error = 0xFFFFFFFF;
		self._timeout_error = 0xFEDCBA98;
		self._default_ok    = 0x55555555;
		self._expose_busy   = 0xEEEEBBBB;
		self._expose_done   = 0xEEEEDDDD;
		self._resp_disabled = 0;


	# --- Format functions -----------------------------------------------------

	## Transforms an int into a list of int's, each at most one byte length.
	#
	# @param self An instance of ByteCode.
	# @param number (int) The number to transform.
	# @param n_bytes (int) Number of bytes to output.
	# @param signed (bool) Assume unsigned numbers for formatting.
	#
	# @returns A list of ints containing the byte-by-byte representation.
	def int_to_byte_list(self, number, n_bytes = 4, signed=False):
		num_type = 'I';
		if(signed):
			num_type = 'i';

		if(n_bytes == 4):
			return tuple(six.byte2int(b) for b in struct.pack(self.endianess + num_type, number));

		elif(n_bytes == 8):
			number_h = (number & 0xFFFFFFFF00000000) >> 32;
			number_l =  number & 0x00000000FFFFFFFF;
			complete = struct.pack(self.endianess + num_type, number_h) + struct.pack(self.endianess + num_type, number_l);
			return tuple(six.byte2int(b) for b in complete);

		else:
			raise ValueError('Only 4 and 8 n_bytes supported');


	## Create header word of 32 bits, joining header submodule and header instruction.
	#
	# @param self An instance of ByteCode.
	# @param header_s (int) The code of header_submodule
	# @param header_i (int) The code of header_instruction
	#
	# @returns the joined header
	def _header_build(self, header_s, header_i):
		return ((header_s << 16) & 0xFFFF0000) + (header_i & 0x0000FFFF);


	## Transforms a group of ints into a str (byte in python 3)
	#
	# The ints must fit in a byte.
	#
	# @param self An instance of ByteCode.
	# @param *words (int) The ints to code.
	#
	# @returns The code (str/bytes) associated with the ints group.
	def _return_op(self, *words):
		result = tuple( [six.int2byte(byte) for word in words for byte in word] );
		return ''.join(result);


	## Boilerplate function for header-only instructons.
	#
	# @param self An instance of ByteCode.
	# @param module_code (int) The index byte list code of the module the instruction is directed to.
	# @param header_s (int) The code of the header submodule.
	# @param header_i (int) The code of the header instruction.
	#
	# @returns A list of codes ([int]).
	def _only_header_instruction(self, module_code, header_s, header_i):
		result =  [ \
								self._init,
								module_code,
								self.int_to_byte_list(1), 
								self.int_to_byte_list(self._header_build(header_s, header_i)) \
							];
		return self._return_op(*result);


	## Parses lines of bytecode into hexadecimal strings
	#
	# @param self An instance of ByteCode.
	# @param bytecode_lines ([str...]) The bytecode to transform.
	# @param word_separator (str) String to add between binary words.
	# @param line_separator (str) String to add between lines.
	# @param word_len (int) The length (in bytes) of a binary word.
	#
	# @returns The hexadecimal representation (str) of bytecode_lines
	def as_legacy_file(self, bytecode_lines, word_separator = ' ', line_separator = '\n', word_len = 4):
		flip = '>' != self.endianess;

		program_str = [];
		line_n = 1
		for line in bytecode_lines:
			words = [line[ii:(ii+word_len)] for ii in six.moves.range(0, len(line), word_len)];
			line_str = [];
			for word in words:
				word = [ord(b) for b in word];
				if(flip):
					word = reversed(word);
				line_str.append(''.join(['{0:02X}'.format(b) for b in word]));
			program_str.append('%03i:\t'%line_n + word_separator.join(line_str));
			line_n += 1
		
		return line_separator.join(program_str);


	# --- Configurator module instructions -------------------------------------
	# --- Power Management submodule instructions ------------------------------

	# Read Power Enable Reg ()
	# TODO

	## Generate the codes needed to turn on every power module
	#
	# @param self An instance of ByteCode.
	# @param regulator (str) name of the regulator to turn on/off
	# @param pwrOn (bool) True to turn on, False to turn off.
	#
	# @returns A list of codes ([int]).
	def configurator_power_on(self, pwrOn): #regulator, pwrOn):
		header_submodule = self._configurator_powermanag_index;  #0x0000;

		# headers = {
		# 	'clocks_digital' : self._configurator_powermanag_enableclocksdigital_inst, #0x0001,
		# 	'bias_digital'   : self._configurator_powermanag_enablebiasdigital_inst,   #0x0002,
		# 	'bias_analog'    : self._configurator_powermanag_enablebiasanalog_inst,    #0x0003,
		# 	'clocks_analog'  : self._configurator_powermanag_enableclocksanalog_inst,  #0x0004,
		# 	'video'          : self._configurator_powermanag_enablevideo_inst,         #0x0005,
		# }
		# if regulator in headers.keys():
		# 	header_instruction = headers[regulator];
		# else:
		# 	raise('Regulator is not in the header list')

		header_instruction = self._configurator_powermanag_enablepower_inst;
		pwrState           = 1 if pwrOn else 0;
		
		result =  [ \
					self._init,
					self._configurator_mod_index, 
					self.int_to_byte_list(2), 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(pwrState) \
					];
		return self._return_op(*result);


	## Generate the codes needed to reset all dacs devices
	#
	# @param self An instance of ByteCode.
	#
	# @returns A list of codes ([int]).
	def dacs_pwr_reset(self):
		#return self._only_header_instruction(self._configurator_mod_index, 0, 6);
		return self._only_header_instruction(self._configurator_mod_index, self._configurator_powermanag_index, self._configurator_powermanag_resetdacs_inst);


	# --- SPI Video submodule instructions -------------------------------------

	## Generate the codes needed to use the SPI Video Configurator
	#
	# @param self An instance of ByteCode.
	# @param address (int) Address of the dac
	# @param data (int) Data to write in the dac.
	#
	# @returns A list of codes ([int]).
	def configurator_spi_video(self, device, polarity, nbits, data):
		header_submodule    = self._configurator_spivideo_index;
		header_instruction  = self._configurator_spivideo_communicate_inst;
		result =  [ \
					self._init,
					self._configurator_mod_index,
					self.int_to_byte_list(3),
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list( ((device<<16)&0x00FF0000) + ((polarity<<8)&0x0000FF00) + (nbits&0x000000FF) ),
					self.int_to_byte_list(data) \
					];
		return self._return_op(*result);


	# --- SPI Bias Clocks submodule instructions -------------------------------

	## Generate the codes needed to use the SPI Bias and Clocks Configurator
	#
	# @param self An instance of ByteCode.
	# @param address (int) Address of the dac
	# @param data (int) Data to write in the dac.
	#
	# @returns A list of codes ([int]).
	def configurator_spi_bias_clocks(self, device, polarity, nbits, data):
		header_submodule    = self._configurator_spibiasclocks_index
		header_instruction  = self._configurator_spibiasclocks_communicate_inst
		result =  [ \
					self._init,
					self._configurator_mod_index, 
					self.int_to_byte_list(3), 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list( ((device<<16)&0x00FF0000) + ((polarity<<8)&0x0000FF00) + (nbits&0x000000FF) ),
					self.int_to_byte_list(data) \
					];
		return self._return_op(*result);


	# --- Acquisition module instructions --------------------------------------
	# --- Sequencer submodule instructions -------------------------------------

	## Generate the codes needed to execute a sequencer mode that captures an image and streams pixels.
	#
	# @param self An instance of ByteCode.
	# @param stop_cleaning_mode_dir (int) Address of the stop_cleaning mode.
	# @param get_image_mode_dir (int) Address of the get_image mode.
	# @param open_shutter (bool) To open the shutter or not.
	#
	# @returns A list of codes ([int]).
	def get_image(self, stop_cleaning_mode_dir, get_image_mode_dir, open_shutter=True):
		header_submodule   = self._acquisition_sequencer_index;          #0; 
		header_instruction = self._acquisition_sequencer_getimage_inst;  #0;
		shutter_state      = int(bool(open_shutter));

		result =  [ \
					self._init,
					self._acquisition_mod_index, 
					self.int_to_byte_list(4),    #2 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(stop_cleaning_mode_dir),
					self.int_to_byte_list(get_image_mode_dir),
					self.int_to_byte_list(shutter_state) \
					];
		return self._return_op(*result);


	## Generate the codes needed to write the sequencer memory
	#
	# @param self An instance of ByteCode.
	# @param address (int) Address of the sequencer memory
	# @param data (int) Data in the address (3 words long (3x32=96bits)).
	#
	# @returns A list of codes ([int]).
	def write_sequencer_memory(self, address, data):
		header_submodule    = self._acquisition_sequencer_index;			 #0;
		header_instruction  = self._acquisition_sequencer_writeseqmem_inst;	 #1;
		data1 = int( (data >> 64) & 0x0000000000000000FFFFFFFF );	# MSB
		data2 = int( (data >> 32) & 0x0000000000000000FFFFFFFF );
		data3 = int(  data        & 0x0000000000000000FFFFFFFF );	# LSB
		result =  [ \
					self._init,
					self._acquisition_mod_index,
					self.int_to_byte_list(5),
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(address),
					self.int_to_byte_list(data1),
					self.int_to_byte_list(data2),
					self.int_to_byte_list(data3) \
					];
		return self._return_op(*result);


	## Generate the codes needed to enable the sequencer
	#
	# @param self An instance of ByteCode.
	#
	# @returns A list of codes ([int]).
	def enable_sequencer(self):
		return self._only_header_instruction(self._acquisition_mod_index, self._acquisition_sequencer_index, self._acquisition_sequencer_enableseq_inst);


	## Generate the codes needed to disable the sequencer
	#
	# @param self An instance of ByteCode.
	#
	# @returns A list of codes ([int]).
	def disable_sequencer(self):
		return self._only_header_instruction(self._acquisition_mod_index, self._acquisition_sequencer_index, self._acquisition_sequencer_disableseq_inst);


	## Generate the codes needed set the exposition time.
	#
	# @param self An instance of ByteCode.
	# @param time (int) Miliseconds to expose.
	#
	# @returns A list of codes ([int]).
	def write_exposition_time(self, time):
		header_submodule    = self._acquisition_sequencer_index; #0;
		header_instruction  = self._acquisition_sequencer_writeexpotime_inst; #4;
		result =  [ \
					self._init,
					self._acquisition_mod_index, 
					self.int_to_byte_list(2),
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(time) \
					];
		return self._return_op(*result);


	# Generate the codes needed to execute a sequencer mode that streams pixels.
	#
	# @param self An instance of ByteCode.
	# @param channel_1or3 (bool) Channel to read (True:1, False:3).
	#
	# @returns A list of codes ([int]).
	def get_pixels_channel(self, channel_1or3=True):
		header_submodule   = self._acquisition_sequencer_index;  #0;
		header_instruction = self._acquisition_sequencer_getpxlsch1_inst if channel_1or3 else self._acquisition_sequencer_getpxlsch3_inst
		result =  [ \
					self._init,
					self._acquisition_mod_index, 
					self.int_to_byte_list(1), 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					];
		return self._return_op(*result);


	# Generate the codes needed to execute a sequencer mode that streams pixels.
	#
	# @param self An instance of ByteCode.
	# @param channel_1or3 (bool) Channel to read (True:1, False:3).
	# @param samples (int) number of samples to get.
	#
	# @returns A list of codes ([int]).
	def get_data_channel(self, channel_1or3=True, samples=0):
		header_submodule   = self._acquisition_sequencer_index;  #0;
		header_instruction = self._acquisition_sequencer_getdatach1_inst if channel_1or3 else self._acquisition_sequencer_getdatach3_inst
		result =  [ \
					self._init,
					self._acquisition_mod_index, 
					self.int_to_byte_list(2), 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(samples) \
					];
		return self._return_op(*result);


	## Generate the codes needed to test the sequencer clocks
	#
	# @param self An instance of ByteCode.
	# @param time Seq test time
	# @param states_high States[32:63]
	# @param states_low States[0:31]
	#
	# @returns A list of codes ([int]).
	def test_sequencer_on(self, time, states_high, states_low):
		header_submodule    = self._acquisition_sequencer_index;
		header_instruction  = self._acquisition_sequencer_tstseqon_inst;
		result =  [ \
					self._init,
					self._acquisition_mod_index, 
					self.int_to_byte_list(4), 
					self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
					self.int_to_byte_list(time),
					self.int_to_byte_list(states_high),
					self.int_to_byte_list(states_low) \
					];
		return self._return_op(*result);


	## Generate the codes needed to disable clock testing
	#
	# @param self An instance of ByteCode.
	#
	# @returns A list of codes ([int]).
	def test_sequencer_off(self):
		return self._only_header_instruction(self._acquisition_mod_index, self._acquisition_sequencer_index, self._acquisition_sequencer_tstseqoff_inst);


	# --- PVM module instructions ----------------------------------------------
	# --- UART uC submodule instructions ---------------------------------------

	# Send Data ()
	# TODO

	# Read Memory ()
	# TODO






# --- Main Test ----------------------------------------------------------------

if __name__ == '__main__':
	print 'Testing Binary.py'

	b = ByteCode()

	for i in dir(b):
		print i
