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
    self.endianess       = endianess;
    self._init           = self.int_to_byte_list(0x29A);
    self._pwr_mod_index  = self.int_to_byte_list(0);
    self._spi_mod_index  = self.int_to_byte_list(1);
    self._i2c1_mod_index = self.int_to_byte_list(2);
    self._i2c2_mod_index = self.int_to_byte_list(3);
    self._seq_mod_index  = self.int_to_byte_list(4);
    self._uart_mod_index = self.int_to_byte_list(5);
    self._default_error  = 0xFFFFFFFF;
    self._default_ok     = 0x55555555;
    self._default_hw_to  = 0xFEDCBA98;
    self._header_shift   = 24;

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

  ## Check an instruction header has been correclty pasted in an instruction.
  #
  # @param self An instance of ByteCode.
  # @param instr (int) The code to transform.
  # @param expected_value (int) The code of the header
  def _check_header(self, instr, expected_value):
    header = ''.join([six.int2byte(b) for b in instr[3]]);
    header = struct.unpack(self.endianess + 'I', header)[0];
    header_tmp = 0xFF << self._header_shift;
    header_tmp = header & header_tmp;
    header = header_tmp >> self._header_shift;
    if(header != expected_value):
      raise RuntimeError('Generated instruction ' + str(instr) + ', header ' + str(header) + ', does not match expected header ' + str(expected_value));

  ## Mask a code or value with a specified pattern
  #
  # Checks that the value doesn't change in the masking process.
  #
  # @param self An instance of ByteCode.
  # @param value The code or value to mask.
  # @param pattern (int) The pattern to apply on the code or value
  #
  # @returns The masked value (int)
  def _mask_int(self, value, pattern):
    if(value >= 0):
      value_short = value &  pattern;
    else:
      value_short = value | ~pattern;

    if(value_short != value):
      raise ValueError('The masked (mask:' + '{0:#X}'.format(value_short) + ') value ' + str(value_short) + ' does not equal the of ' + str(value) + '');
    return value_short & pattern;

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
  def _only_header_instruction(self, module, header):
    result =  [ \
                self._init,
                module, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(0, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to use SPI Protocol
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the dac
  # @param data (int) Data to write in the dac.
  #
  # @returns A list of codes ([int]).
  def spi_write(self, bus, device, polarity, nbits, data):
    header = 0x00;
    result =  [ \
                self._init,
                self._spi_mod_index, 
                self.int_to_byte_list(2), 
                self.int_to_byte_list(self._paste_byte((bus<<20)+(device<<16)+(polarity<<8)+nbits, header)),
                self.int_to_byte_list(data) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to write the sequencer memory
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the sequencer memory
  # @param data (int) Data in the address.
  #
  # @returns A list of codes ([int]).
  def seq_write_mem(self, address, data):
    header = 0;
    result =  [ \
                self._init,
                self._seq_mod_index, 
                self.int_to_byte_list(3), 
                self.int_to_byte_list(address),
                self.int_to_byte_list(data, n_bytes=8) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to turn on every power module
  #
  # @param self An instance of ByteCode.
  # @param regulator (str) name of the regulator to turn on/off
  # @param pwrOn (bool) True to turn on, False to turn off.
  #
  # @returns A list of codes ([int]).
  def regulator_power_on(self, regulator, pwrOn):
    headers = {
      'clocks_dacs' : 0x01,
      'bias_dacs'   : 0x02,
      'bias_hv'     : 0x03,
      'bias_lv'     : 0x04,
      'clocks'      : 0x05,
      'video'       : 0x06
    }

    header = 0x00;
    pwrState = 0x000000;

    if(pwrOn == True):
      pwrState = 0x010000;

    if(regulator in headers.keys()):
      header = headers[regulator];
    else:
      raise('Regulator is not in header list')

    result =  [ \
                self._init,
                self._pwr_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(pwrState, header))
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to reset all dacs devices
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def dacs_pwr_reset(self):
    return self._only_header_instruction(self._pwr_mod_index, 7);

  ## Generate the codes needed to enable the sequencer
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def seq_enable(self):
    return self._only_header_instruction(self._seq_mod_index, 2);

  ## Generate the codes needed to disable the sequencer
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def seq_disable(self):
    return self._only_header_instruction(self._seq_mod_index, 3);

  ## Generate the codes needed to execute a sequencer mode
  #
  # @param self An instance of ByteCode.
  # @param header (int) Header for the instruction.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def seq_execute(self, header, address):
    result =  [ \
                self._init,
                self._seq_mod_index,
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(address, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to execute a sequencer mode that streams pixels.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def seq_take_photo(self, address):
    header = 0x04;
    return self.seq_execute(header, address);

  ## Generate the codes needed to execute a sequencer mode that should respond a single word.
  #
  # @param self An instance of ByteCode.
  # @param address (int) Address of the mode.
  #
  # @returns A list of codes ([int]).
  def seq_move_to_mode(self, address):
    header = 0x18;
    return self.seq_execute(header, address);

  ## Generate the codes needed to test the USB 2 speed
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def seq_test_usb2(self):
    return self._only_header_instruction(self._seq_mod_index, 0x0D);

  ## Generate the codes needed to test the USB 3 speed
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def seq_test_usb3(self):
    return self._only_header_instruction(self._seq_mod_index, 0x0E);

  ## Generate the codes needed to test the sequencer clocks
  #
  # @param self An instance of ByteCode.
  # @param index (int) Index of the clock.
  # @param clk_div (int) the clock division denominator.
  #
  # @returns A list of codes ([int]).
  def seq_enable_test_clock(self, index, clk_div):
    header = 0x0F;
    index_short = self._mask_int(index, 0xFF);
    clk_div_short = self._mask_int(clk_div, 0xFFFF);

    result =  [ \
                self._init,
                self._seq_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte((clk_div_short << 8) & index_short), header) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to disable clock testing
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def seq_disable_test_clock(self):
    return self._only_header_instruction(self._seq_mod_index, 0x10);

  ## Generate the codes needed set the exposition time.
  #
  # @param self An instance of ByteCode.
  # @param time (int) Miliseconds to expose.
  #
  # @returns A list of codes ([int]).
  def seq_set_exposition_time(self, time):
    header = 0x16;
    time_short = self._mask_int(time, 0xFFFFFF);

    result =  [ \
                self._init,
                self._seq_mod_index, 
                self.int_to_byte_list(1),
                self.int_to_byte_list(self._paste_byte(time_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to expose the camera
  #
  # @param self An instance of ByteCode.
  # @param open_shutter (bool) Whenever to open the shutter or not.
  #
  # @returns A list of codes ([int]).
  def seq_expose(self, open_shutter = True):
    header = 0x17;
    value_short = int(bool(open_shutter));

    result =  [ \
                self._init,
                self._seq_mod_index, 
                self.int_to_byte_list(1),
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed to enable PID temperature control.
  #
  # @note You must also use pid_manual_mode_disable in order to enable the pid.
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def pid_enable(self):
    return self._only_header_instruction(self._pid_mod_index, 0x00);

  ## Generate the codes needed to enable PID temperature control.
  #
  # @note You must also use pid_manual_mode_enable in order to enable manual mode.
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def pid_disable(self):
    return self._only_header_instruction(self._pid_mod_index, 0x01);

  ## Generate the codes needed set the temperature control setpoint.
  #
  # @param self An instance of ByteCode.
  # @param value (int) The code of the setpoint.
  #
  # @returns A list of codes ([int]).
  def pid_set_setpoint(self, value):
    header = 0x02;
    value_short = self._mask_int(value, 0xFFFFFF);

    result =  [ \
                self._init,
                self._pid_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed set the k1 pid constant.
  #
  # @param self An instance of ByteCode.
  # @param value (int) The code of the constant.
  #
  # @returns A list of codes ([int])
  def pid_set_k1(self, value):
    header = 0x03;
    value_short = self._mask_int(value, 0xFFFFFF);

    result =  [ \
                self._init,
                self._pid_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed set the k2 pid constant.
  #
  # @param self An instance of ByteCode.
  # @param value (int) The code of the constant.
  #
  # @returns A list of codes ([int])
  def pid_set_k2(self, value):
    header = 0x04;
    value_short = self._mask_int(value, 0xFFFFFF);

    result =  [ \
                self._init,
                self._pid_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed set the k3 pid constant.
  #
  # @param self An instance of ByteCode.
  # @param value (int) The code of the constant.
  #
  # @returns A list of codes ([int])
  def pid_set_k3(self, value):
    header = 0x05;
    value_short = self._mask_int(value, 0xFFFFFF);

    result =  [ \
                self._init,
                self._pid_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## Generate the codes needed get the temperature control setpoint
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int])
  def pid_get_setpoint(self):
    return self._only_header_instruction(self._pid_mod_index, 0x06);

  ## Generate the codes needed get the k1 pid constant.
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int])
  def pid_get_k1(self):
    return self._only_header_instruction(self._pid_mod_index, 0x07);

  ## Generate the codes needed get the k2 pid constant.
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int])
  def pid_get_k2(self):
    return self._only_header_instruction(self._pid_mod_index, 0x08);

  ## Generate the codes needed get the k3 pid constant.
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int])
  def pid_get_k3(self):
    return self._only_header_instruction(self._pid_mod_index, 0x09);

  ## Generate the codes needed get the current CCD temperature
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int])
  def pid_get_temperature(self):
    return self._only_header_instruction(self._pid_mod_index, 0x0A);

  ## Generate the codes needed to enable manual temperature control.
  #
  # @note You must also use pid_disable in order to enable manual mode
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def pid_manual_mode_enable(self):
    return self._only_header_instruction(self._pid_mod_index, 0x0B);

  ## Generate the codes needed to disable manual temperature control.
  #
  # @note You must also use pid_disable in order to disable manual mode
  #
  # @param self An instance of ByteCode.
  #
  # @returns A list of codes ([int]).
  def pid_manual_mode_disable(self):
    return self._only_header_instruction(self._pid_mod_index, 0x0C);

  ## Generate the codes needed set the manipulated variable.
  #
  # @param self An instance of ByteCode.
  # @param value (int) The code of the manipulated variable.
  #
  # @returns A list of codes ([int])
  def pid_set_manipulated_variable(self, value):
    header = 0x0D;
    value_short = self._mask_int(value, 0xFFFFFF);

    result =  [ \
                self._init,
                self._pid_mod_index, 
                self.int_to_byte_list(1), 
                self.int_to_byte_list(self._paste_byte(value_short, header)) \
              ];
    self._check_header(result, header);
    return self._return_op(*result);

  ## @var endianess
  # (str) The endianness of the generated bytecode. Uses python struct's format.
  ## @var _init
  # (int) The init word form communication with the camera.
  ## @var _spi_mod_index
  # (int) The index of the dac module inside SciCam
  ## @var _i2c1_mod_index
  # (int) The index of i2c module for temp sensor 1 in SciCam
  ## @var _i2c2_mod_index
  # (int) The index of i2c module for temp sensor 2 in SciCam
  ## @var _seq_mod_index
  # (int) The index of the sequencer module inside SciCam
  ## @var _uart_mod_index
  # (int) The index of uart module inside SciCam to control Cryotel
  ## @var _header_shift
  # (int) Position (in bits) of the header of each instruction.
