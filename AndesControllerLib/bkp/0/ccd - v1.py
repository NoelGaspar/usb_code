#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package ccd
#
# Generation of SciCam's programs for specific CCD's.
#
# This module contains the _CCD class with specifies an overridable interface for
# CCD program generation.

import six as six;
import sequencer as sequencer;
from math import ceil, floor;

from collections import namedtuple as namedtuple;

## Defines a CCD minimal function definitions.
# @note This is an abstract class it MUST be overriden in order to work.
#
# A _CCD derived class is expected to have an init method with a **kwarg parameter.
# Then in the init method the kwarg dict is filled with the missing attributes of the kwarg
# using the add_default method. Finally the class is expected to call _CCD.__init__.
# All the keys in kwargs will transform into attributes.
#
# This way every CCD can have very different parameters, but it will be ensured that they
# are filled with at least a default value.
class _CCD:
  ## Initializes a _CDD
  #
  # @param self An instance of _CCD
  # @param kwargs A dict containing the attributes of the object.
  def __init__(self, **kwargs):
    self._metadata = [];

    for k in kwargs:
      if(hasattr(self, str(k))):
        raise ValueError('CCD already has attribute ' + str(k) + '!');
      setattr(self, str(k), kwargs[k]);
      self._metadata.append(str(k));

    self._init_sanity_check();

  ## Checks that the CCD parameters are valid for programming.
  #
  # If an attribute is not valid, a ValueError shall be raised.
  #
  # @param self An instance of _CCD
  def _init_sanity_check(self):
    raise NotImplementedError('Override _CCDs _init_sanity_check!');

  ## Creates a sequencer.Program based on the current CCD attributes
  #
  # @param self An instance of _CCD
  #  
  # @returns A sequencer.Program for SciCam sequencer programming.
  def _create_sequencer_program(self):
    raise NotImplementedError('Override _CCDs _create_sequencer_program!');

  ## Creates the codes needed for each bias dac
  #
  # @param self An instance of _CCD
  #  
  # @returns A list of codes ([int...]), each index of the list corresponds to the dac address.
  def _create_word_codes(self):
    raise NotImplementedError('Override _CCDs _create_word_codes!');

  ## Creates the codes needed for a complete CCD configuration (bias + program)
  #
  # @param self An instance of _CCD
  # @param bytecode_formatter A binary.ByteCodes to format writing instructions.
  #  
  # @returns A list of bytecode ([str...])
  def get_configuration_bytecode(self, bytecode_formatter):
    if(not hasattr(self, 'configured_program')):
      raise ValueError('Call compile_configured_program before obtaining a program.');
    self._init_sanity_check();

    formatter = bytecode_formatter;
    word_config_codes = self._create_word_codes();

    bytecode_lines = [];

    bytecode_lines.append(formatter.regulator_power_on('bias_hv',False));
    bytecode_lines.append(formatter.regulator_power_on('bias_lv',False));
    bytecode_lines.append(formatter.regulator_power_on('clocks',False));
    bytecode_lines.append(formatter.regulator_power_on('video',False));
    bytecode_lines.append(formatter.regulator_power_on('clocks_dacs',True));
    bytecode_lines.append(formatter.regulator_power_on('bias_dacs',True));
    bytecode_lines.append(formatter.dacs_pwr_reset());

    for word in word_config_codes['BiasClocksConfig']:
      bytecode_lines.append(formatter.spi_write(word.bus, word.dev, word.pol, word.nbits, word.code));

    for word in word_config_codes['BiasClocksVoltage']:
      bytecode_lines.append(formatter.spi_write(word.bus, word.dev, word.pol, word.nbits, (word.address<<16) + word.voltage));

    for ii in range(len(self.configured_program.codes)):
      seq_line = self.configured_program.codes[ii];
      bytecode_lines.append(formatter.seq_write_mem(ii, seq_line));

    bytecode_lines.append(formatter.seq_enable());

    bytecode_lines.append(formatter.regulator_power_on('video',True));

    for word in word_config_codes['VideoAdcConfig']:
      bytecode_lines.append(formatter.spi_write(word.bus, word.dev, word.pol, word.nbits, word.code));

    for word in word_config_codes['VideoConfig']:
      bytecode_lines.append(formatter.spi_write(word.bus, word.dev, word.pol, word.nbits, word.code));

    for word in word_config_codes['VideoVoltage']:
      bytecode_lines.append(formatter.spi_write(word.bus, word.dev, word.pol, word.nbits, (word.address<<16) + word.voltage));

    bytecode_lines.append(formatter.regulator_power_on('bias_hv',True));
    bytecode_lines.append(formatter.regulator_power_on('bias_lv',True));
    bytecode_lines.append(formatter.regulator_power_on('clocks',True));

    return bytecode_lines;

  ## Gets the resulting image resolution given the ccd parameters.
  #
  # @param self An instance of _CCD
  #  
  # @returns A tuple(x, y) containing the image dimensions.
  def get_image_resolution(self):
    raise NotImplementedError('Override _CCDs get_image_resolution!');

  ## Gets the name of the sequencer mode in which to start taking a photo.
  #
  # @param self An instance of _CCD
  #  
  # @returns The mode name (str)
  def get_take_photo_mode_name(self):
    raise NotImplementedError('Override _CCDs get_take_photo_mode_name!');

  ## Compiles the sequencer porgram for the current ccd attributes.
  #
  # @param self An instance of _CCD
  def compile_configured_program(self):
    self.configured_program = self._create_sequencer_program();

  ## Gets the last sequencer program compiled
  #
  # @param self An instance of _CCD
  #  
  # @returns The last compiled program (sequencer.Program).
  def get_configured_program(self):
    if(not hasattr(self, 'configured_program')):
      raise ValueError('Call compile_configured_program before obtaining a program.');
    return self.configured_program;

  ## Gets all the attributes set on the init method
  #
  # @param self An instance of _CCD
  #  
  # @returns A list of all the attributes names ([str...])
  def get_metadata(self):
    return list(self._metadata);

  ## Adds an attribute (key) to kwargs if not already present
  #
  # @param self An instance of _CCD
  # @param kwargs (dict) Dict containing attributes names as keys with their attributes values as values.
  # @param key (str) Name of the attribute
  # @param argument Value of the attribute if not already present
  def add_default(self, kwargs, key, argument):
    if(key not in kwargs):
      kwargs[key]= argument;

  ## @var _metadata
  # A list of all the ccd attribute names ([str...])
  ## @var configured_program
  # The last built program (sequencer.Program)

## This is a specialization of _CCD for the ccd CCD_47_10 from ...
# @see _CCD
class CCD_47_10(_CCD):

  ## Default value for clocks
  # clocks_vect order name bus device polarity nbits add_bot add_top volt_bot volt_top seq_num
  _default_clock_params = {
    'CLK1A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot': 0, 'add_top': 1, 'volt_bot':0, 'volt_top':0,  'clockId': 0},
    'CLK2A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot': 3, 'add_top': 2, 'volt_bot':0, 'volt_top':0,  'clockId': 1},
    'CLK3A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot': 4, 'add_top': 5, 'volt_bot':0, 'volt_top':0,  'clockId': 2},
    'CLK4A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot': 7, 'add_top': 6, 'volt_bot':0, 'volt_top':0,  'clockId': 3},
    'CLK5A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot': 8, 'add_top': 9, 'volt_bot':0, 'volt_top':0,  'clockId': 4},
    'CLK6A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot':11, 'add_top':10, 'volt_bot':0, 'volt_top':0,  'clockId': 5},
    'CLK7A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot':12, 'add_top':13, 'volt_bot':0, 'volt_top':0,  'clockId': 6},
    'CLK8A':{'bus':0, 'dev':0, 'pol':0, 'nbits':24, 'add_bot':15, 'add_top':14, 'volt_bot':0, 'volt_top':0,  'clockId': 7},

    'CLK1B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot': 0, 'add_top': 1, 'volt_bot':0, 'volt_top':0,  'clockId': 8},
    'CLK2B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot': 3, 'add_top': 2, 'volt_bot':0, 'volt_top':0,  'clockId': 9},
    'CLK3B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot': 4, 'add_top': 5, 'volt_bot':0, 'volt_top':0,  'clockId':10},
    'CLK4B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot': 7, 'add_top': 6, 'volt_bot':0, 'volt_top':0,  'clockId':11},
    'CLK5B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot': 8, 'add_top': 9, 'volt_bot':0, 'volt_top':0,  'clockId':12},
    'CLK6B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot':11, 'add_top':10, 'volt_bot':0, 'volt_top':0,  'clockId':13},
    'CLK7B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot':12, 'add_top':13, 'volt_bot':0, 'volt_top':0,  'clockId':14},
    'CLK8B':{'bus':0, 'dev':1, 'pol':0, 'nbits':24, 'add_bot':15, 'add_top':14, 'volt_bot':0, 'volt_top':0,  'clockId':15},

    'CLK1C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot': 0, 'add_top': 1, 'volt_bot':0, 'volt_top':0,  'clockId':16},
    'CLK2C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot': 3, 'add_top': 2, 'volt_bot':0, 'volt_top':0,  'clockId':17},
    'CLK3C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot': 4, 'add_top': 5, 'volt_bot':0, 'volt_top':0,  'clockId':18},
    'CLK4C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot': 7, 'add_top': 6, 'volt_bot':0, 'volt_top':0,  'clockId':19},
    'CLK5C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot': 8, 'add_top': 9, 'volt_bot':0, 'volt_top':0,  'clockId':20},
    'CLK6C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot':11, 'add_top':10, 'volt_bot':0, 'volt_top':0,  'clockId':21},
    'CLK7C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot':12, 'add_top':13, 'volt_bot':0, 'volt_top':0,  'clockId':22},
    'CLK8C':{'bus':0, 'dev':2, 'pol':0, 'nbits':24, 'add_bot':15, 'add_top':14, 'volt_bot':0, 'volt_top':0,  'clockId':23},

    'CLKI1':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':24},
    'CLKI2':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':25},
    'CLKI3':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':26},
    'CLKI4':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':27},
    'CLKI5':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':28},
    'CLKI6':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':29},
    'CLKI7':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':30},
    'CLKI8':{'bus':0, 'dev':0, 'pol':0, 'nbits':0,  'add_bot': 0, 'add_top': 0, 'volt_bot':0, 'volt_top':0,  'clockId':31},    
  }

  ## Default value for bias
  # bias_vect order name bus device polarity nbits address voltage
  _default_bias_params = {
    'BHV1A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 0, 'voltage':0, 'biasId': 33, 'voltType': 'high'},
    'BHV2A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 1, 'voltage':0, 'biasId': 34, 'voltType': 'high'},
    'BHV3A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 2, 'voltage':0, 'biasId': 35, 'voltType': 'high'},
    'BHV4A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 3, 'voltage':0, 'biasId': 36, 'voltType': 'high'},
    'BHV5A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 4, 'voltage':0, 'biasId': 37, 'voltType': 'high'},
    'BHV6A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 5, 'voltage':0, 'biasId': 38, 'voltType': 'high'},
    'BHV7A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 6, 'voltage':0, 'biasId': 39, 'voltType': 'high'},
    'BHV8A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 7, 'voltage':0, 'biasId': 40, 'voltType': 'high'},
    'BLV1A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 8, 'voltage':0, 'biasId': 41, 'voltType': 'low' },
    'BLV2A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address': 9, 'voltage':0, 'biasId': 42, 'voltType': 'low' },
    'BLV3A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':10, 'voltage':0, 'biasId': 43, 'voltType': 'low' },
    'BLV4A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':11, 'voltage':0, 'biasId': 44, 'voltType': 'low' },
    'BLV5A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':12, 'voltage':0, 'biasId': 45, 'voltType': 'low' },
    'BLV6A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':13, 'voltage':0, 'biasId': 46, 'voltType': 'low' },
    'BLV7A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':14, 'voltage':0, 'biasId': 47, 'voltType': 'low' },
    'BLV8A':{'bus':0, 'dev':3, 'pol':0, 'nbits':24, 'address':15, 'voltage':0, 'biasId': 48, 'voltType': 'low' },

#    'BHV1B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 0, 'voltage':0, 'biasId':49, 'voltType': 'high'},
#    'BHV2B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 1, 'voltage':0, 'biasId':50, 'voltType': 'high'},
#    'BHV3B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 2, 'voltage':0, 'biasId':51, 'voltType': 'high'},
#    'BHV4B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 3, 'voltage':0, 'biasId':52, 'voltType': 'high'},
#    'BHV5B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 4, 'voltage':0, 'biasId':53, 'voltType': 'high'},
#    'BHV6B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 5, 'voltage':0, 'biasId':54, 'voltType': 'high'},
#    'BHV7B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 6, 'voltage':0, 'biasId':55, 'voltType': 'high'},
#    'BHV8B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 7, 'voltage':0, 'biasId':56, 'voltType': 'high'},
#    'BLV1B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 8, 'voltage':0, 'biasId':57, 'voltType': 'low' },
#    'BLV2B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address': 9, 'voltage':0, 'biasId':58, 'voltType': 'low' },
#    'BLV3B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':10, 'voltage':0, 'biasId':59, 'voltType': 'low' },
#    'BLV4B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':11, 'voltage':0, 'biasId':60, 'voltType': 'low' },
#    'BLV5B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':12, 'voltage':0, 'biasId':61, 'voltType': 'low' },
#    'BLV6B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':13, 'voltage':0, 'biasId':62, 'voltType': 'low' },
#    'BLV7B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':14, 'voltage':0, 'biasId':63, 'voltType': 'low' },
#    'BLV8B':{'bus':0, 'dev':5, 'pol':0, 'nbits':24, 'address':15, 'voltage':0, 'biasId':64, 'voltType': 'low' },
  }

  ## Default value for bias
  # bias_vect order name bus device polarity nbits address voltage
  _default_video_params = {
    'OFFCH1':{'bus':1, 'dev':2, 'pol':0, 'nbits':24, 'address': 0, 'voltage':0, 'videoId': 0},
    'OFFCH2':{'bus':1, 'dev':2, 'pol':0, 'nbits':24, 'address': 1, 'voltage':0, 'videoId': 1},
    'OFFCH3':{'bus':1, 'dev':3, 'pol':0, 'nbits':24, 'address': 0, 'voltage':0, 'videoId': 2},
    'OFFCH4':{'bus':1, 'dev':3, 'pol':0, 'nbits':24, 'address': 1, 'voltage':0, 'videoId': 3},
  }

  ## Default value for bias
  # bias_vect order name bus device polarity nbits address voltage
  _default_video_ADC_params = {
    'ADCCH1':{'bus':1, 'dev':0, 'pol':1, 'nbits':16},
    'ADCCH2':{'bus':1, 'dev':1, 'pol':1, 'nbits':16},
  }

  ## Default value for clock_pins, mount names
  _default_clock_pins = {
  # 4 Outputs
    'PC1D' : _default_clock_params['CLK7C']['clockId'],  # SEQ22  # A4 B4 Parallel Clock Down
    'PC2D' : _default_clock_params['CLK4C']['clockId'],  # SEQ19  # A1 B1 Parallel Clock Down
    'PC3D' : _default_clock_params['CLK5C']['clockId'],  # SEQ20  # A2 B2 Parallel Clock Down
    'PC4D' : _default_clock_params['CLK3C']['clockId'],  # SEQ18  # A3 B3 Parallel Clock Down
    'PC1U' : _default_clock_params['CLK2A']['clockId'],  # SEQ01  # C1 D1 Parallel Clock Up
    'PC2U' : _default_clock_params['CLK4A']['clockId'],  # SEQ03  # C2 D2 Parallel Clock Up
    'PC3U' : _default_clock_params['CLK6A']['clockId'],  # SEQ05  # C3 D3 Parallel Clock Up
    'PC4U' : _default_clock_params['CLK5A']['clockId'],  # SEQ04  # C4 D4 Parallel Clock Up
    'SC1L' : _default_clock_params['CLK8A']['clockId'],  # SEQ07  # E2 H2 Serial Clock Left
    'SC2L' : _default_clock_params['CLK1B']['clockId'],  # SEQ08  # E1 H1 Serial Clock Left
    'SC1R' : _default_clock_params['CLK6B']['clockId'],  # SEQ13  # F2 G2 Serial Clock Right
    'SC2R' : _default_clock_params['CLK5B']['clockId'],  # SEQ12  # F1 G1 Serial Clock Right
    'SCO'  : _default_clock_params['CLK3B']['clockId'],  # SEQ10  # E F G H Serial Clock Output
    'TGD'  : _default_clock_params['CLK6C']['clockId'],  # SEQ21  # A B Transfer Gate, Must be equal to PC1. Down
    'TGU'  : _default_clock_params['CLK1A']['clockId'],  # SEQ00  # C D Transfer Gate, Must be equal to PC1. Up
    'ORL'  : _default_clock_params['CLK8C']['clockId'],  # SEQ23  # E H Reset Left
    'ORR'  : _default_clock_params['CLK3A']['clockId'],  # SEQ02  # F G Reset Right
    'SWOL' : _default_clock_params['CLK7A']['clockId'],  # SEQ06  # E H Summing Well Left
    'SWOR' : _default_clock_params['CLK7B']['clockId'],  # SEQ14  # F G Summing Well Right
    'DGD'  : _default_clock_params['CLK2B']['clockId'],  # SEQ09  # A B Dump Gate Down
    'DGU'  : _default_clock_params['CLK4B']['clockId'],  # SEQ11  # C D Dump Gate Up
    'PIXT' : _default_clock_params['CLKI7']['clockId'],  # SEQ30  # Pixel Time
    'CRST' : _default_clock_params['CLKI6']['clockId'],  # SEQ29  # DC Level Reset, Video Capacitor
  };

  ## Set default clock voltages
  _default_clock_voltages = {
    'PC1D' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC2D' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC3D' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC4D' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC1U' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC2U' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC3U' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'PC4U' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SC1L' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SC2L' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SC1R' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SC2R' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SCO'  : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'TGD'  : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'TGU'  : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'ORL'  : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'ORR'  : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SWOL' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'SWOR' : {'volt_top':  +2.0, 'volt_bot': -9.0},
    'DGD'  : {'volt_top':  +3.0, 'volt_bot': -9.0},
    'DGU'  : {'volt_top':  +3.0, 'volt_bot': -9.0},
  }

  ## Default value for bias_pins, mount names
  _default_bias_pins = {
    'RDE'  : _default_bias_params['BLV8A']['biasId'],         #
    'ODE'  : _default_bias_params['BHV7A']['biasId'],         #
    'OGE'  : _default_bias_params['BLV7A']['biasId'],         #
    'DDA'  : _default_bias_params['BHV6A']['biasId'],         #
    'OGF'  : _default_bias_params['BLV6A']['biasId'],         #
    'ODF'  : _default_bias_params['BHV5A']['biasId'],         #
    'RDF'  : _default_bias_params['BLV5A']['biasId'],         #
    'RDG'  : _default_bias_params['BLV4A']['biasId'],         #
    'ODG'  : _default_bias_params['BHV4A']['biasId'],         #
    'OGG'  : _default_bias_params['BLV3A']['biasId'],         #
    'DDD'  : _default_bias_params['BHV3A']['biasId'],         #
    'OGH'  : _default_bias_params['BLV2A']['biasId'],         #
    'ODH'  : _default_bias_params['BHV2A']['biasId'],         #
    'RDH'  : _default_bias_params['BLV1A']['biasId'],         #
  };

  ## Set default bias voltages
  _default_bias_voltages = {
    'RDE'  : {'voltage':  +9.0},
    'ODE'  : {'voltage': +21.0},
    'OGE'  : {'voltage':  -6.0},
    'DDA'  : {'voltage': +21.0},
    'OGF'  : {'voltage':  -6.0},
    'ODF'  : {'voltage': +21.0},
    'RDF'  : {'voltage':  +9.0},
    'RDG'  : {'voltage':  +9.0},
    'ODG'  : {'voltage': +21.0},
    'OGG'  : {'voltage':  -6.0},
    'DDD'  : {'voltage': +21.0},
    'OGH'  : {'voltage':  -6.0},
    'ODH'  : {'voltage': +21.0},
    'RDH'  : {'voltage':  +9.0},
  }

  ## Set default video offset ids
  _default_video_pins = {
    'CH1'  : _default_video_params['OFFCH1']['videoId'],         #
    'CH2'  : _default_video_params['OFFCH2']['videoId'],         #
    'CH3'  : _default_video_params['OFFCH3']['videoId'],         #
    'CH4'  : _default_video_params['OFFCH4']['videoId'],         #
  }

  ## Set default video offset
  _default_video_voltages = {
    'CH1'  : {'voltage':  +0.237535},
    'CH2'  : {'voltage':  +0.237535},
    'CH3'  : {'voltage':  +0.237535},
    'CH4'  : {'voltage':  +0.237535},
  }

  ## Default value for n_cols
  _default_n_cols = 1072;
  ## Default value for n_rows
  _default_n_rows = 1027;

  ## Default value for n_times
  _default_n_times         = 1;
  ## Default value for video_fall_time
  _default_video_fall_time = 2;

  ## Default value for y_bin
  _default_y_bin	= 1;
  ## Default value for x_bin
  _default_x_bin	= 1;

  ## Default value for extra_int_time
  _default_extra_int_time = 0;

  ## Initializes a CDD_47_10. See _CCD
  #
  # @param self An instance of CDD_47_10
  # @param kwargs A dict containing the attributes of the object.
  #
  # @see _CCD
  def __init__(self, **kwargs):
    self.add_default(kwargs, 'clocks',          self._default_clock_params);
    self.add_default(kwargs, 'biases',          self._default_bias_params);
    self.add_default(kwargs, 'video_offset',    self._default_video_params);
    self.add_default(kwargs, 'video_ADC',       self._default_video_ADC_params);
    self.add_default(kwargs, 'clock_pins',      self._default_clock_pins);
    self.add_default(kwargs, 'clock_voltages',  self._default_clock_voltages);
    self.add_default(kwargs, 'bias_pins',       self._default_bias_pins);
    self.add_default(kwargs, 'bias_voltages',   self._default_bias_voltages);
    self.add_default(kwargs, 'video_pins',      self._default_video_pins);
    self.add_default(kwargs, 'video_voltages',  self._default_video_voltages);

    self.add_default(kwargs, 'n_cols',          self._default_n_cols);
    self.add_default(kwargs, 'n_rows',          self._default_n_rows);

    self.add_default(kwargs, 'video_fall_time', self._default_video_fall_time);
    self.add_default(kwargs, 'n_times',         self._default_n_times);

    self.add_default(kwargs, 'y_bin',           self._default_y_bin);
    self.add_default(kwargs, 'x_bin',           self._default_x_bin);

    self.add_default(kwargs, 'extra_int_time',  self._default_extra_int_time);

    _CCD.__init__(self, **kwargs);
    
    # Neeeded for doxygen member detection.
    if False:
      self.clocks           = None;
      self.biases           = None;
      self.video_offset     = None;
      self.video_ADC        = None;
      self.clock_pins       = None;
      self.clock_voltages   = None;
      self.bias_pins        = None;
      self.bias_voltages    = None;
      self.video_pins       = None;
      self.video_voltages   = None;

      self.n_cols           = None;
      self.n_rows           = None;

      self.video_fall_time  = None;
      self.n_times          = None;

      self.y_bin            = None;
      self.x_bin            = None;

      self.extra_int_time   = None;

  def _init_sanity_check(self):
    pass
  #   if(set(self.clocks_top_address) != set(self.clocks_top_voltages)):
  #     message = 'There are diferent keys in clocks_top_address and clocks_top_voltages. ';
  #     message += 'Unique in clocks_top_address: ' + str(set(self.clocks_top_address) - set(self.clocks_top_voltages)) + '. ';
  #     message += 'Unique in clocks_top_voltages: ' + str(set(self.clocks_top_voltages) - set(self.clocks_top_address));
  #     raise ValueError(message);

  #   if(set(self.clocks_bottom_address) != set(self.clocks_bottom_voltages)):
  #     message = 'There are diferent keys in clocks_bottom_address and clocks_bottom_voltages. ';
  #     message += 'Unique in clocks_bottom_address: ' + str(set(self.clocks_bottom_address) - set(self.clocks_bottom_voltages)) + '. ';
  #     message += 'Unique in clocks_bottom_voltages: ' + str(set(self.clocks_bottom_voltages) - set(self.clocks_bottom_address));
  #     raise ValueError(message);

  #   if(set(self.low_voltage_bias_address) != set(self.low_voltage_bias_voltages)):
  #     message = 'There are diferent keys in low_voltage_bias_address and low_voltage_bias_voltages. ';
  #     message += 'Unique in low_voltage_bias_address: ' + str(set(self.low_voltage_bias_address) - set(self.low_voltage_bias_voltages)) + '. ';
  #     message += 'Unique in low_voltage_bias_voltages: ' + str(set(self.low_voltage_bias_voltages) - set(self.low_voltage_bias_address));
  #     raise ValueError(message);

  #   if(set(self.high_voltage_bias_address) != set(self.high_voltage_bias_voltages)):
  #     message = 'There are diferent keys in high_voltage_bias_address and high_voltage_bias_voltages. ';
  #     message += 'Unique in high_voltage_bias_address: ' + str(set(self.high_voltage_bias_voltages) - set(self.high_voltage_bias_voltages)) + '. ';
  #     message += 'Unique in high_voltage_bias_voltages: ' + str(set(self.high_voltage_bias_voltages) - set(self.high_voltage_bias_address));
  #     raise ValueError(message);

    # Check other ranges

  ## Overload for CDD_47_10.
  #
  # @param self An instance of CDD_47_10
  #
  # @see _CCD
  def get_image_resolution(self):
    return \
    ( \
      int(ceil(float(self.n_cols)/float(self.x_bin))),
      int(ceil(float(self.n_rows)/float(self.y_bin))) \
    );

  ## Overload for CDD_47_10.
  #
  # @param self An instance of CDD_47_10
  #
  # @see _CCD
  def get_take_photo_mode_name(self):
    return 'init_sweep_out';

  ## Returns the name of the sequencer mode to jump for stopping CCD cleaning.
  #
  # @param self An instance of CDD_47_10
  def get_stop_cleaning_mode_name(self):
    return 'cleaning_end';

  def _dac_video_volt_to_code(self, voltage):
    return int(floor((voltage + 5) / 10 * 2**16 ))

  def _dac_bias_volt_to_code(self, voltage, voltType):
    voltCode = 0;
    if(voltType == 'high'):
      voltCode = int( ( ( ( voltage/6.0 ) / 5.0 ) * (2**14) ) + 0b1100000000000000 );
    elif(voltType == 'low'):
      voltCode = int( ( ( ( voltage/6.0 + 2.5 ) / 5.0 ) * (2**14) ) + 0b1100000000000000 );
    else:
      raise('Wrong voltage Type in bias dacs')
    return voltCode

  def _dac_clocks_volt_to_code(self, voltage): 
    return int( ( ( ( voltage/6.0 + 2.5 ) / 5.0 ) * (2**14) ) + 0b1100000000000000 );

  def _set_dac_initial_voltages(self, voltages):
    for key in voltages:
      if(key in self.clock_pins.keys()):
        checkId = self.clock_pins[key]
        for clock in self.clocks:
          if(checkId == self.clocks[clock]['clockId']):
            self.clocks[clock]['volt_top'] = voltages[key]['volt_top']
            self.clocks[clock]['volt_bot'] = voltages[key]['volt_bot']
      elif(key in self.bias_pins.keys()):
        checkId = self.bias_pins[key]
        for bias in self.biases:
          if(checkId == self.biases[bias]['biasId']):
            self.biases[bias]['voltage'] = voltages[key]['voltage']
      elif(key in self.video_pins.keys()):
        checkId = self.video_pins[key]
        for video in self.video_offset:
          if(checkId == self.video_offset[video]['videoId']):
            self.video_offset[video]['voltage'] = voltages[key]['voltage']
      else:
        raise ValueError('No existe el label ' + str(key));

  def _create_word_codes(self):
    self._set_dac_initial_voltages(self.bias_voltages)
    self._set_dac_initial_voltages(self.clock_voltages)
    self._set_dac_initial_voltages(self.video_voltages)

    BiasClocksVoltageCode = [];
    BiasClocksConfigCode  = [];
    VideoVoltageCode      = [];
    VideoConfigCode       = [];
    VideoAdcConfigCode    = [];
    BiasClocksVoltageWord = namedtuple('BiasClocksVoltageWord', 'bus dev pol nbits address voltage');
    BiasClocksConfigWord  = namedtuple('BiasClocksConfigWord', 'bus dev pol nbits code');
    VideoVoltageWord      = namedtuple('VideoVoltageWord', 'bus dev pol nbits address voltage');
    VideoConfigWord       = namedtuple('VideoConfigWord', 'bus dev pol nbits code');
    VideoAdcConfigWord    = namedtuple('VideoAdcConfigWord', 'bus dev pol nbits code');
    Devices = [];

    # Set dac Bias
    for k in self.biases.keys():
      bus   = self.biases[k]['bus'];
      dev   = self.biases[k]['dev'];
      pol   = self.biases[k]['pol'];
      nbits = self.biases[k]['nbits'];
      addr  = self.biases[k]['address'];
      vType = self.biases[k]['voltType'];
      volt  = self._dac_bias_volt_to_code(self.biases[k]['voltage'],vType);
      BiasClocksVoltageCode.append(BiasClocksVoltageWord(bus, dev, pol, nbits, addr, volt));
      tup = [bus, dev];
      if(tup not in Devices):
        Devices.append(tup);
        BiasClocksConfigCode.append(BiasClocksConfigWord(bus, dev, pol, nbits, 0x000C1D00));

    # Set dac Clocks
    for k in self.clocks.keys():
      bus   = self.clocks[k]['bus'];
      dev   = self.clocks[k]['dev'];
      pol   = self.clocks[k]['pol'];
      nbits = self.clocks[k]['nbits'];
      addr  = self.clocks[k]['add_bot'];
      volt  = self._dac_clocks_volt_to_code(self.clocks[k]['volt_bot']);
      BiasClocksVoltageCode.append(BiasClocksVoltageWord(bus, dev, pol, nbits, addr, volt));
      tup = [bus, dev];
      if(tup not in Devices):
        Devices.append(tup);
        BiasClocksConfigCode.append(BiasClocksConfigWord(bus, dev, pol, nbits, 0x000C1D00));

    for k in self.clocks.keys():
      bus   = self.clocks[k]['bus'];
      dev   = self.clocks[k]['dev'];
      pol   = self.clocks[k]['pol'];
      nbits = self.clocks[k]['nbits'];
      addr  = self.clocks[k]['add_top'];
      volt  = self._dac_clocks_volt_to_code(self.clocks[k]['volt_top']);
      BiasClocksVoltageCode.append(BiasClocksVoltageWord(bus, dev, pol, nbits, addr, volt));

    for k in self.video_offset.keys():
      bus   = self.video_offset[k]['bus'];
      dev   = self.video_offset[k]['dev'];
      pol   = self.video_offset[k]['pol'];
      nbits = self.video_offset[k]['nbits'];
      addr  = self.video_offset[k]['address'];
      volt  = self._dac_video_volt_to_code(self.video_offset[k]['voltage']);
      VideoVoltageCode.append(VideoVoltageWord(bus, dev, pol, nbits, addr, volt));
      VideoConfigCode.append(VideoConfigWord(bus, dev, pol, nbits, 0x00200000));
      VideoConfigCode.append(VideoConfigWord(bus, dev, pol, nbits, 0x00300000));
      VideoConfigCode.append(VideoConfigWord(bus, dev, pol, nbits, 0x00380001));

    for k in self.video_ADC.keys():
      bus   = self.video_ADC[k]['bus'];
      dev   = self.video_ADC[k]['dev'];
      pol   = self.video_ADC[k]['pol'];
      nbits = self.video_ADC[k]['nbits'];
      VideoAdcConfigCode.append(VideoAdcConfigWord(bus, dev, pol, nbits, 0x00000080));
      VideoAdcConfigCode.append(VideoAdcConfigWord(bus, dev, pol, nbits, 0x00000180));
      VideoAdcConfigCode.append(VideoAdcConfigWord(bus, dev, pol, nbits, 0x00000245));
      VideoAdcConfigCode.append(VideoAdcConfigWord(bus, dev, pol, nbits, 0x00000355));
      VideoAdcConfigCode.append(VideoAdcConfigWord(bus, dev, pol, nbits, 0x00000455));

    return {'BiasClocksVoltage':BiasClocksVoltageCode, 'BiasClocksConfig':BiasClocksConfigCode, 'VideoVoltage':VideoVoltageCode, \
            'VideoConfig':VideoConfigCode, 'VideoAdcConfig':VideoAdcConfigCode };

  def _create_sequencer_program(self):

    labels = sequencer.Labels(self.clock_pins);

    # Constants
    n_times           = self.n_times;
    video_fall_time   = self.video_fall_time;
    n_rows            = self.n_rows;
    n_cols            = self.n_cols;
    y_bin             = self.y_bin;
    x_bin             = self.x_bin;
    extra_int_time    = self.extra_int_time;

    # CLEANING REPEAT
    all_modes = [];

    cleaning_repeat_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,1,1,1,0,),
        'PC2D' : (0,0,0,0,1,1,1,),
        'PC3D' : (1,1,0,0,0,0,0,),
        'PC4D' : (0,1,1,1,1,0,0,),
        'PC1U' : (0,0,0,1,1,1,0,),
        'PC2U' : (0,0,0,0,1,1,1,),
        'PC3U' : (1,1,0,0,0,0,0,),
        'PC4U' : (0,1,1,1,1,0,0,),
        'SC1L' : (1,1,1,1,1,1,1,),
        'SC2L' : (1,1,1,1,1,1,1,),
        'SC1R' : (1,1,1,1,1,1,1,),
        'SC2R' : (1,1,1,1,1,1,1,),
        'SCO'  : (0,0,0,0,0,0,0,),
        'TGD'  : (0,0,0,1,1,1,0,), # 4 Outputs > equal to PC1
        'TGU'  : (0,0,0,1,1,1,0,), # 4 Outputs > equal to PC1
        'ORL'  : (1,1,1,1,1,1,1,),
        'ORR'  : (1,1,1,1,1,1,1,),
        'SWOL' : (0,0,0,0,0,0,0,),
        'SWOR' : (0,0,0,0,0,0,0,),
        'DGD'  : (1,1,1,1,1,1,1,),
        'DGU'  : (1,1,1,1,1,1,1,),
        'PIXT' : (0,0,0,0,0,0,0,),
        'CRST' : (1,1,1,1,1,1,1,),
      },
      (1500, 1500, 1500, 1500, 1500, 1500, 1500,)\
    );

    cleaning_repeat_mode = sequencer.Mode(name='cleaning_repeat', n_loops=0, next_mode_name='cleaning_end');
    cleaning_repeat_mode.add_states(cleaning_repeat_states);
    all_modes.append(cleaning_repeat_mode);

    # CLEANING END

    cleaning_end_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,),
        'PC2D' : (0,0,0,0,),
        'PC3D' : (0,0,0,0,),
        'PC4D' : (0,0,0,0,),
        'PC1U' : (0,0,0,0,),
        'PC2U' : (0,0,0,0,),
        'PC3U' : (0,0,0,0,),
        'PC4U' : (0,0,0,0,),
        'SC1L' : (1,0,0,1,),
        'SC2L' : (1,0,0,1,),
        'SC1R' : (1,0,0,1,),
        'SC2R' : (1,0,0,1,),
        'SCO'  : (0,0,0,0,),
        'TGD'  : (0,0,0,0,),
        'TGU'  : (0,0,0,0,),
        'ORL'  : (1,1,1,1,),
        'ORR'  : (1,1,1,1,),
        'SWOL' : (0,0,0,0,),
        'SWOR' : (0,0,0,0,),
        'DGD'  : (1,1,0,0,),
        'DGU'  : (1,1,0,0,),
        'PIXT' : (0,0,0,0,),
        'CRST' : (1,1,1,1,),
      },
      (1500, 2000, 2000, 1500,)\
    );

    cleaning_end_mode = sequencer.Mode(name='cleaning_end', n_loops=1, next_mode_name='exposing');
    cleaning_end_mode.add_states(cleaning_end_states);
    all_modes.append(cleaning_end_mode);

    # EXPOSING

    exposing_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,),
        'PC2D' : (0,),
        'PC3D' : (0,),
        'PC4D' : (0,),
        'PC1U' : (0,),
        'PC2U' : (0,),
        'PC3U' : (0,),
        'PC4U' : (0,),
        'SC1L' : (1,),
        'SC2L' : (1,),
        'SC1R' : (1,),
        'SC2R' : (1,),
        'SCO'  : (0,),
        'TGD'  : (0,),
        'TGU'  : (0,),
        'ORL'  : (1,),
        'ORR'  : (1,),
        'SWOL' : (0,),
        'SWOR' : (0,),
        'DGD'  : (0,),
        'DGU'  : (0,),
        # 'PIXT' : (0,),
        'PIXT' : (1,),
        'CRST' : (1,),
      },
      (2,)\
    );

    exposing_mode = sequencer.Mode(name='exposing', n_loops=0, next_mode_name='init_sweep_out');
    exposing_mode.add_states(exposing_states);
    all_modes.append(exposing_mode);

    # INIT SWEEP OUT

    init_sweep_out_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,0,0,0,),
        'PC2D' : (0,0,0,0,0,0,0,),
        'PC3D' : (0,0,0,0,0,0,0,),
        'PC4D' : (0,0,0,0,0,0,0,),
        'PC1U' : (0,0,0,0,0,0,0,),
        'PC2U' : (0,0,0,0,0,0,0,),
        'PC3U' : (0,0,0,0,0,0,0,),
        'PC4U' : (0,0,0,0,0,0,0,),
        'SC1L' : (0,0,0,0,1,1,1,),
        'SC2L' : (1,1,1,0,0,0,1,),
        'SC1R' : (0,0,0,0,1,1,1,),
        'SC2R' : (1,1,1,0,0,0,1,),
        'SCO'  : (0,0,1,1,1,0,0,),
        'TGD'  : (0,0,0,0,0,0,0,),
        'TGU'  : (0,0,0,0,0,0,0,),
        'ORL'  : (1,0,0,0,0,0,0,),
        'ORR'  : (1,0,0,0,0,0,0,),
        'SWOL' : (0,0,1,1,1,0,0,),
        'SWOR' : (0,0,1,1,1,0,0,),
        'DGD'  : (0,0,0,0,0,0,0,),
        'DGU'  : (0,0,0,0,0,0,0,),
        # 'PIXT' : (0,0,0,0,0,0,0,),
        'PIXT' : (1,1,1,1,1,1,1,),
        'CRST' : (0,0,0,0,0,0,0,),
      },
      (16, 10, 4, 32, 4, 32, 4,)\
    );

    init_sweep_out_mode = sequencer.Mode(name='init_sweep_out', n_loops=1, next_mode_name='sweep_out');
    init_sweep_out_mode.add_states(init_sweep_out_states);
    all_modes.append(init_sweep_out_mode);

    # SWEEP OUT 

    sweep_out_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,0,0,0,0,),
        'PC2D' : (0,0,0,0,0,0,0,0,),
        'PC3D' : (0,0,0,0,0,0,0,0,),
        'PC4D' : (0,0,0,0,0,0,0,0,),
        'PC1U' : (0,0,0,0,0,0,0,0,),
        'PC2U' : (0,0,0,0,0,0,0,0,),
        'PC3U' : (0,0,0,0,0,0,0,0,),
        'PC4U' : (0,0,0,0,0,0,0,0,),
        'SC1L' : (0,0,0,0,0,1,1,1,),
        'SC2L' : (1,1,1,1,0,0,0,1,),
        'SC1R' : (0,0,0,0,0,1,1,1,),
        'SC2R' : (1,1,1,1,0,0,0,1,),
        'SCO'  : (0,0,0,1,1,1,0,0,),
        'TGD'  : (0,0,0,0,0,0,0,0,),
        'TGU'  : (0,0,0,0,0,0,0,0,),
        'ORL'  : (0,1,0,0,0,0,0,0,),
        'ORR'  : (0,1,0,0,0,0,0,0,),
        'SWOL' : (0,0,0,1,1,1,0,0,),
        'SWOR' : (0,0,0,1,1,1,0,0,),
        'DGD'  : (0,0,0,0,0,0,0,0,),
        'DGU'  : (0,0,0,0,0,0,0,0,),
        # 'PIXT' : (0,0,0,0,0,0,0,0,),
        'PIXT' : (1,1,1,1,1,1,1,1,),
        'CRST' : (0,0,0,0,0,0,0,0,),
      },
      (10, 6, 10, 4, 32, 4, 32, 4,)\
    );

    sweep_out_mode = sequencer.Mode(name='sweep_out', n_loops=n_cols-1, next_mode_name='end_sweep_out');
    sweep_out_mode.add_states(sweep_out_states);
    all_modes.append(sweep_out_mode);

    # END SWEEP OUT 2

    end_sweep_out_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,),
        'PC2D' : (0,0,),
        'PC3D' : (0,0,),
        'PC4D' : (0,0,),
        'PC1U' : (0,0,),
        'PC2U' : (0,0,),
        'PC3U' : (0,0,),
        'PC4U' : (0,0,),
        'SC1L' : (1,1,),
        'SC2L' : (1,1,),
        'SC1R' : (1,1,),
        'SC2R' : (1,1,),
        'SCO'  : (0,0,),
        'TGD'  : (0,0,),
        'TGU'  : (0,0,),
        'ORL'  : (0,1,),
        'ORR'  : (0,1,),
        'SWOL' : (0,0,),
        'SWOR' : (0,0,),
        'DGD'  : (0,0,),
        'DGU'  : (0,0,),
        # 'PIXT' : (0,0,),
        'PIXT' : (1,1,),
        'CRST' : (0,1,),
      },
      (10, 1500,)\
    );

    end_sweep_out_mode = sequencer.Mode(name='end_sweep_out', n_loops=1, next_mode_name='parallel');
    end_sweep_out_mode.add_states(end_sweep_out_states);
    all_modes.append(end_sweep_out_mode);

    # PARALLEL

    parallel_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,1,1,1,0,0,),
        'PC2D' : (0,0,0,0,1,1,1,0,),
        'PC3D' : (1,1,0,0,0,0,0,0,),
        'PC4D' : (0,1,1,1,1,0,0,0,),
        'PC1U' : (0,0,0,1,1,1,0,0,),
        'PC2U' : (0,0,0,0,1,1,1,0,),
        'PC3U' : (1,1,0,0,0,0,0,0,),
        'PC4U' : (0,1,1,1,1,0,0,0,),
        'SC1L' : (1,1,1,1,1,1,1,1,),
        'SC2L' : (1,1,1,1,1,1,1,1,),
        'SC1R' : (1,1,1,1,1,1,1,1,),
        'SC2R' : (1,1,1,1,1,1,1,1,),
        'SCO'  : (0,0,0,0,0,0,0,0,),
        'TGD'  : (0,0,0,1,1,1,0,0,),
        'TGU'  : (0,0,0,1,1,1,0,0,),
        'ORL'  : (1,1,1,1,1,1,1,1,),
        'ORR'  : (1,1,1,1,1,1,1,1,),
        'SWOL' : (0,0,0,0,0,0,0,0,),
        'SWOR' : (0,0,0,0,0,0,0,0,),
        'DGD'  : (1,1,1,1,1,1,1,1,),
        'DGU'  : (1,1,1,1,1,1,1,1,),
        # 'PIXT' : (0,0,0,0,0,0,0,0,),
        'PIXT' : (1,1,1,1,1,1,1,1,),
        'CRST' : (1,1,1,1,1,1,1,1,),
      },
      (1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500,)\
    );

    parallel_mode = sequencer.Mode(name='parallel', n_loops=y_bin, next_mode_name='init_binning');
    parallel_mode.add_states(parallel_states);
    all_modes.append(parallel_mode);

    # INIT BINNING

    init_binning_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,),
        'PC2D' : (0,0,0,0,),
        'PC3D' : (0,0,0,0,),
        'PC4D' : (0,0,0,0,),
        'PC1U' : (0,0,0,0,),
        'PC2U' : (0,0,0,0,),
        'PC3U' : (0,0,0,0,),
        'PC4U' : (0,0,0,0,),
        'SC1L' : (0,0,0,0,),
        'SC2L' : (1,1,1,0,),
        'SC1R' : (0,0,0,0,),
        'SC2R' : (1,1,1,0,),
        'SCO'  : (0,0,1,1,),
        'TGD'  : (0,0,0,0,),
        'TGU'  : (0,0,0,0,),
        'ORL'  : (1,0,0,0,),
        'ORR'  : (1,0,0,0,),
        'SWOL' : (0,0,1,1,),
        'SWOR' : (0,0,1,1,),
        'DGD'  : (0,0,0,0,),
        'DGU'  : (0,0,0,0,),
        # 'PIXT' : (0,0,0,0,),
        'PIXT' : (1,1,1,1,),
        'CRST' : (1,0,0,0,),
      },
      (16, 10, 4, 12 + video_fall_time,)\
    );

    init_binning_mode = sequencer.Mode(name='init_binning', n_loops=1, next_mode_name='binning');
    init_binning_mode.add_states(init_binning_states);
    all_modes.append(init_binning_mode);

    # BINNING REPEAT

    binning_repeat_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,0,0,0,0,0,),
        'PC2D' : (0,0,0,0,0,0,0,0,0,),
        'PC3D' : (0,0,0,0,0,0,0,0,0,),
        'PC4D' : (0,0,0,0,0,0,0,0,0,),
        'PC1U' : (0,0,0,0,0,0,0,0,0,),
        'PC2U' : (0,0,0,0,0,0,0,0,0,),
        'PC3U' : (0,0,0,0,0,0,0,0,0,),
        'PC4U' : (0,0,0,0,0,0,0,0,0,),
        'SC1L' : (0,1,1,1,0,0,0,0,0,),
        'SC2L' : (0,0,0,1,1,1,1,1,0,),
        'SC1R' : (0,1,1,1,0,0,0,0,0,),
        'SC2R' : (0,0,0,1,1,1,1,1,0,),
        'SCO'  : (1,1,0,0,0,0,0,1,1,),
        'TGD'  : (0,0,0,0,0,0,0,0,0,),
        'TGU'  : (0,0,0,0,0,0,0,0,0,),
        'ORL'  : (0,0,0,0,0,1,0,0,0,),
        'ORR'  : (0,0,0,0,0,1,0,0,0,),
        'SWOL' : (1,1,1,1,1,1,1,1,1,),
        'SWOR' : (1,1,1,1,1,1,1,1,1,),
        'DGD'  : (0,0,0,0,0,0,0,0,0,),
        'DGU'  : (0,0,0,0,0,0,0,0,0,),
        'PIXT' : (1,1,1,1,1,1,1,1,1,),
        'CRST' : (0,0,0,0,0,0,0,0,0,),
      },
      (20 - video_fall_time, 4, 32, 4, 10, 6, 10, 4, 12 + video_fall_time,)\
    );

    # BINNING SAMPLE

    binning_sample_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,0,0,0,0,0,),
        'PC2D' : (0,0,0,0,0,0,0,0,0,),
        'PC3D' : (0,0,0,0,0,0,0,0,0,),
        'PC4D' : (0,0,0,0,0,0,0,0,0,),
        'PC1U' : (0,0,0,0,0,0,0,0,0,),
        'PC2U' : (0,0,0,0,0,0,0,0,0,),
        'PC3U' : (0,0,0,0,0,0,0,0,0,),
        'PC4U' : (0,0,0,0,0,0,0,0,0,),
        'SC1L' : (0,1,1,1,0,0,0,0,0,),
        'SC2L' : (0,0,0,1,1,1,1,1,0,),
        'SC1R' : (0,1,1,1,0,0,0,0,0,),
        'SC2R' : (0,0,0,1,1,1,1,1,0,),
        'SCO'  : (1,1,0,0,0,0,0,1,1,),
        'TGD'  : (0,0,0,0,0,0,0,0,0,),
        'TGU'  : (0,0,0,0,0,0,0,0,0,),
        'ORL'  : (0,0,0,0,0,1,0,0,0,),
        'ORR'  : (0,0,0,0,0,1,0,0,0,),
        'SWOL' : (1,1,0,0,0,0,0,1,1,),
        'SWOR' : (1,1,0,0,0,0,0,1,1,),
        'DGD'  : (0,0,0,0,0,0,0,0,0,),
        'DGU'  : (0,0,0,0,0,0,0,0,0,),
        # 'PIXT' : (1,1,1,1,1,1,1,0,0,),
        'PIXT' : (1,1,1,1,1,1,1,1,1,),
        'CRST' : (0,0,0,0,0,1,0,0,0,),
      },
      (20 - video_fall_time, 4, 32, 4, 10, 6, 10, 4, 12 + video_fall_time,)\
    );

    binning_mode = sequencer.Mode(name='binning', n_loops=int(ceil(float(n_cols)/float(x_bin)))-1, next_mode_name='end_binning');
    if(x_bin > 1):
    	for bins in range(x_bin-1):
    		binning_mode.add_states(binning_repeat_states);
    binning_mode.add_states(binning_sample_states);
    all_modes.append(binning_mode);

    # BINNING END

    end_binning_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,0,0,0,0,0,0,),
        'PC2D' : (0,0,0,0,0,0,0,),
        'PC3D' : (0,0,0,0,0,0,0,),
        'PC4D' : (0,0,0,0,0,0,0,),
        'PC1U' : (0,0,0,0,0,0,0,),
        'PC2U' : (0,0,0,0,0,0,0,),
        'PC3U' : (0,0,0,0,0,0,0,),
        'PC4U' : (0,0,0,0,0,0,0,),
        'SC1L' : (0,1,1,1,1,1,1,),
        'SC2L' : (0,0,0,1,1,1,1,),
        'SC1R' : (0,1,1,1,1,1,1,),
        'SC2R' : (0,0,0,1,1,1,1,),
        'SCO'  : (1,1,0,0,0,0,0,),
        'TGD'  : (0,0,0,0,0,0,0,),
        'TGU'  : (0,0,0,0,0,0,0,),
        'ORL'  : (0,0,0,0,0,1,1,),
        'ORR'  : (0,0,0,0,0,1,1,),
        'SWOL' : (1,1,0,0,0,0,0,),
        'SWOR' : (1,1,0,0,0,0,0,),
        'DGD'  : (0,0,0,0,0,0,0,),
        'DGU'  : (0,0,0,0,0,0,0,),
        # 'PIXT' : (1,1,1,1,1,1,0,),
        # 'PIXT' : (1,1,1,1,1,1,1,),
        'CRST' : (0,0,0,0,0,1,1,),
      },
      (20 - video_fall_time, 4, 32, 4, 10, 16, 1500,)\
    );

    end_binning_mode = sequencer.Mode(name='end_binning', n_loops=1, next_mode_name='cleaning_init', parent_mode_name = 'parallel', nested_loops = int(ceil(float(n_rows)/float(y_bin))));
    if(x_bin > 1):
    	for bins in range(x_bin-1):
    		end_binning_mode.add_states(binning_repeat_states);
    end_binning_mode.add_states(end_binning_states);
    all_modes.append(end_binning_mode);

    # CLEANING INIT

    cleaning_init_states = sequencer.State.from_labels_array \
    ( \
      labels,
      { \
        'PC1D' : (0,),
        'PC2D' : (0,),
        'PC3D' : (0,),
        'PC4D' : (0,),
        'PC1U' : (0,),
        'PC2U' : (0,),
        'PC3U' : (0,),
        'PC4U' : (0,),
        'SC1L' : (1,),
        'SC2L' : (1,),
        'SC1R' : (1,),
        'SC2R' : (1,),
        'SCO'  : (0,),
        'TGD'  : (0,),
        'TGU'  : (0,),
        'ORL'  : (1,),
        'ORR'  : (1,),
        'SWOL' : (0,),
        'SWOR' : (0,),
        'DGD'  : (1,),
        'DGU'  : (1,),
        'PIXT' : (0,),
        'CRST' : (1,),
      },
      (1500,)\
    );

    cleaning_init_mode = sequencer.Mode(name='cleaning_init', n_loops=1, next_mode_name='cleaning_repeat');
    cleaning_init_mode.add_states(cleaning_init_states);
    all_modes.append(cleaning_init_mode);

    # PROGRAM

    compiler = sequencer.ProgramBuilder();
    for mode in all_modes:
      compiler.add_mode(mode);
    program = compiler.build();

    return program

  ## @var clocks_top_address
  # A dict mapping names to the addresses of the top clocks
  ## @var clocks_bottom_address
  # A dict mapping names to the addresses of the bottom clocks
  ## @var low_voltage_bias_address
  # A dict mapping names to the addresses of the low biases
  ## @var high_voltage_bias_address
  # A dict mapping names to the addresses of the high biases

  ## @var clocks_top_voltages
  # A dict mapping names to the voltages of the top clocks
  ## @var clocks_bottom_voltages
  # A dict mapping names to the voltages of the bottom clocks
  ## @var low_voltage_bias_voltages
  # A dict mapping names to the voltages of the low biases
  ## @var high_voltage_bias_voltages
  # A dict mapping names to the voltages of the high biases

  ## @var sequencer_pins
  # A dict mapping names to the address of the pins of the sequencer output.

  ## @var n_cols
  # The number of columns (int) the ccd has
  ## @var n_rows
  # The number of columns (int) the ccd has

  ## @var n_times
  # The number of extra cycles delay (int >= 1) to add to the ccd charge processing in all the clock sequence.
  ## @var sampling_time
  # The number of extra cycles delay (int >= 1) to add to the ccd charge processing in just in the sampling sequence.
  ## @var ccd_fall
  # The number of cycles delay (int >= 6) to leave in the switch-to-pixel voltage levels.

  ## @var y_bin
  # The binning (int >= 1) to apply in the y direction.
  ## @var x_bin
  # The binning (int >= 1) to apply in the x direction.

  ## @var extra_int_time
  # The extra integration cycles (int >= 0), leading to a longer integration time at the sampling stage, giving better noise results but lower frame rate.
