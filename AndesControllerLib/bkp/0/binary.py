#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package binary
#
# Binary data formatting for USB transfers
#
# This module exposes the ByteCode class to generate SciCam usb bytecode.

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
    self.endianess                = endianess;
    self._init                    = self.int_to_byte_list(0x29A);
    self._configurator_mod_index  = self.int_to_byte_list(0);
    self._acquisition_mod_index   = self.int_to_byte_list(1);
    self._temperature_mod_index   = self.int_to_byte_list(2);
    self._default_error           = 0xFFFFFFFF;
    self._default_ok              = 0x55555555;
    self._default_hw_to           = 0xFEDCBA98; # Default Hardware Time Out Error

  ## Transforms a int into a list of int's, each at most one byte length.
  #
  # @param self An instance of ByteCode.
  # @param number (int) The number to transform.
  # @param n_bytes (int) Number of bytes to output.
  # @param signed (bool) Assume signed numbers for formatting.
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

  ## Parses lines of bytecode into hexadecimal strings
  #
  # @param self An instance of ByteCode.
  # @param bytecode_lines ([str...]) The bytecode to transform.
  # @param word_separator (str) String to add between binary words.
  # @param line_separator (str) String to add between lines.
  # @param word_len (int) The length (in bytes) of a binary word.
  #
  # @returns The hexadecimal representation (str) of bytecode_lines
  def as_legacy_file(self, bytecode_lines, word_separator = ' ', line_separator = '\n',word_len = 4):
    flip = '>' != self.endianess;

    program_str = [];
    for line in bytecode_lines:
      words = [line[ii:(ii+word_len)] for ii in six.moves.range(0, len(line), word_len)];
      line_str = [];
      for word in words:
        word = [ord(b) for b in word];
        if(flip):
          word = reversed(word);
        line_str.append(''.join(['{0:02X}'.format(b) for b in word]));
      program_str.append(word_separator.join(line_str));
    
    return line_separator.join(program_str);

  ## Pastes a byte with an offset (in bytes) in a code
  #
  # @param self An instance of ByteCode.
  # @param data (int) The code or value to paste the byte over.
  # @param byte (int) The value of the byte to paste
  # @param position (int) The position (in bytes) of where to paste the byte.
  #
  # @returns The modified code.
  def _paste_byte(self, data, byte, position = 3):    
    result = data & ~(0xFF << (position*8));
    if(result != data):
      raise ValueError('Pasting byte ' + str(byte) + ' in data ' + str(data) + ' at offset ' + position + ' changes its value.');
    if(byte > 255 or byte < 0):
      raise ValueError('Byte ' + str(byte) + ' does not fit in 8 bits.');

    return result | (byte << (position*8));

  ## Create header word of 32 bits, joining header submodule and header instruction
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
    result = tuple([six.int2byte(byte) for word in words for byte in word]);
    return ''.join(result);

  ## Boilerplate function for header-only instructons.
  #
  # @param self An instance of ByteCode.
  # @param module (int) The index of the module the instruction is directed to.
  # @param header (int) The code of the header.
  #
  # @returns A list of codes ([int]).
  def _only_header_instruction(self, module, header_s, header_i):
    result =  [ \
                self._init,
                module, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._header_build(header_s, header_i)) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to use the SPI Video Configurator
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the dac
  # @param data (int) Data to write in the dac.
  #
  # @returns A list of codes ([int]).
  def configurator_spi_video(self, device, polarity, nbits, data):
    header_submodule    = 1;
    header_instruction  = 0;
    result =  [ \
                self._init,
                self._configurator_mod_index, 
                self.int_to_byte_list(3), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(((device<<16)&0x00FF0000)+((polarity<<8)&0x0000FF00)+(nbits&0x000000FF)),
                self.int_to_byte_list(data) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to use the SPI Bias and Clocks Configurator
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the dac
  # @param data (int) Data to write in the dac.
  #
  # @returns A list of codes ([int]).
  def configurator_spi_bias_clocks(self, device, polarity, nbits, data):
    header_submodule    = 2;
    header_instruction  = 0;
    result =  [ \
                self._init,
                self._configurator_mod_index, 
                self.int_to_byte_list(3), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(((device<<16)&0x00FF0000)+((polarity<<8)&0x0000FF00)+(nbits&0x000000FF)),
                self.int_to_byte_list(data) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to use the SPI Heater
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the dac
  # @param data (int) Data to write in the dac.
  #
  # @returns A list of codes ([int]).
  def temperature_spi_heater(self, device, polarity, nbits, data):
    header_submodule    = 0;
    header_instruction  = 0;
    result =  [ \
                self._init,
                self._temperature_mod_index, 
                self.int_to_byte_list(3), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(((device<<16)&0x00FF0000)+((polarity<<8)&0x0000FF00)+(nbits&0x000000FF)),
                self.int_to_byte_list(data) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to turn on every power module
  #
  # @param self An instance of ByteCode.
  # @param regulator (str) name of the regulator to turn on/off
  # @param pwrOn (bool) True to turn on, False to turn off.
  #
  # @returns A list of codes ([int]).
  def configurator_power_on(self, regulator, pwrOn):
    headers = {
      'clocks_digital' : 0x0001,
      'bias_digital'   : 0x0002,
      'bias_analog'    : 0x0003,
      'clocks_analog'  : 0x0004,
      'video'          : 0x0005
    }

    header_submodule = 0x0000;
    pwrState = 0;

    if(pwrOn == True):
      pwrState = 1;

    if(regulator in headers.keys()):
      header_instruction = headers[regulator];
    else:
      raise('Regulator is not in header list')

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
    return self._only_header_instruction(self._configurator_mod_index, 0, 6);

  ## Generate the codes needed to execute a sequencer mode that streams pixels.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def get_image(self, address):
    header_submodule    = 0;
    header_instruction  = 0;
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(address) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to execute a sequencer mode that should respond a single word.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def stop_ccd_cleaning(self, address):
    header_submodule    = 0;
    header_instruction  = 1;
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(address) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to write the sequencer memory
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the sequencer memory
  # @param data (int) Data in the address.
  #
  # @returns A list of codes ([int]).
  def write_sequencer_memory(self, address, data):
    header_submodule    = 0;
    header_instruction  = 2;    #XXX ver ACQUISITION_CONSTANTS.v, WRITE_SEQUENCER_MEMORY = 1
    data1 = int((data >> 64) & 0x0000000000000000FFFFFFFF);
    data2 = int((data >> 32) & 0x0000000000000000FFFFFFFF);
    data3 = int( data        & 0x0000000000000000FFFFFFFF);
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
    return self._only_header_instruction(self._acquisition_mod_index, 0, 3);

  ## Generate the codes needed to disable the sequencer
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def disable_sequencer(self):
    return self._only_header_instruction(self._acquisition_mod_index, 0, 4);

  ## Generate the codes needed set the exposition time.
  #
  # @param self An instance of ByteCode.
  # @param time (int) Miliseconds to expose.
  #
  # @returns A list of codes ([int]).
  def write_exposition_time(self, time):
    header_submodule    = 0;
    header_instruction  = 5;
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2),
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(time) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to expose the camera
  #
  # @param self An instance of ByteCode.
  # @param open_shutter (bool) Whenever to open the shutter or not.
  #
  # @returns A list of codes ([int]).
  def expose(self, open_shutter = True):
    shutter_state       = int(bool(open_shutter));
    header_submodule    = 0;
    header_instruction  = 6;
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2),
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(shutter_state) \
              ];
    return self._return_op(*result);

  # Generate the codes needed to execute a sequencer mode that streams pixels.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def get_data_channel(self, samples, channel):
    header_submodule   = 0;
    header_instruction = 0;
    if(channel > 0 and channel <= 4):
      header_instruction  = 12 + channel;
    else:
      raise('Wrong channel number')
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(samples) \
              ];
    return self._return_op(*result);

  # Generate the codes needed to execute a sequencer mode that streams pixels.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def get_pixels_channel(self, address, channel):
    header_submodule   = 0;
    header_instruction = 0;
    if(channel > 0 and channel <= 4):
      header_instruction  = 8 + channel;
    else:
      raise('Wrong channel number')
    result =  [ \
                self._init,
                self._acquisition_mod_index, 
                self.int_to_byte_list(2), 
                self.int_to_byte_list(self._header_build(header_submodule, header_instruction)),
                self.int_to_byte_list(address) \
              ];
    return self._return_op(*result);

  ## Generate the codes needed to test the sequencer clocks
  #
  # @param self An instance of ByteCode.
  # @param index (int) Index of the clock.
  # @param clk_div (int) the clock division denominator.
  #
  # @returns A list of codes ([int]).
  def test_sequencer_on(self, time, states_high, states_low):
    header_submodule    = 0;
    header_instruction  = 17;
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
    return self._only_header_instruction(self._acquisition_mod_index, 0, 18);