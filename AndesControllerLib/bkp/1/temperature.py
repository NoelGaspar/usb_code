#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package temperature
#
# Generation of Andes Controller configuration for temperature control.

import GuideCamLib.binary as binary;

## A class for storing and converting temperature control configuration values
#
class TemperatureControl:

  ## Initializes a TemperatureControl
  #
  # @param self An instance of TemperatureControl
  # @param manual (bool) Whenever manual mode is enabled.
  # @param manipulated_var (float) The voltage applied to control the peltier strength. (For manual mode)
  # @param setpoint (float) The target temperature. (For PID mode)
  # @param k_vect ((float,)*3) The k_p, k_i and k_d constants of the PID.
  def __init__(self, manual = True, manipulated_var = 0, setpoint = 0, k_vect = (0,0,0)):
    self.manual = manual;
    self.setpoint = setpoint;
    self.manipulated_var = manipulated_var;
    self.set_k(k_vect);

  ## Sets the k_p, k_i and k_d constants
  #
  # @param self An instance of TemperatureControl
  # @param k_vect ((float,)*3) The k_p, k_i and k_d constants of the PID.
  def set_k(self, k_vect):
    if(len(k_vect) != 3):
      raise ValueError("len(k_vect) is expected to be 3.");
    self.k = k_vect;

  ## Sets the k_p constant
  #
  # @param self An instance of TemperatureControl
  # @param k_p (float) The k_p value.
  def set_k_p(self, k_p):
    self.k = (k_p,) + (self.k[1],) + (self.k[2],);

  ## Sets the k_i constant
  #
  # @param self An instance of TemperatureControl
  # @param k_i (float) The k_i value.
  def set_k_i(self, k_i):
    self.k = (self.k[0],) + (k_i,) + (self.k[2],);

  ## Sets the k_d constant
  #
  # @param self An instance of TemperatureControl
  # @param k_d (float) The k_d value.
  def set_k_d(self, k_d):
    self.k = (self.k[0],) + (self.k[1],) + (k_d,);

  ## Computes the code tho program for the current k
  #
  # It also transforms from k_pid to k_123 a digital implemetation of the PID controller.
  #
  # @param self An instance of TemperatureControl
  #
  # @returns The code (int) representing the k_123
  def _k_pid_to_k_123_code(self):
    k = self.k;
    values = (k[0]+k[1]+k[2], -(k[0]+2*k[2]), k[2],);
    return tuple([int(v) for v in values]);

  ## Computes the code tho program for the current setpoint
  #
  # @param self An instance of TemperatureControl
  #
  # @returns The code (int) representing the setpoint
  def _setpoint_to_code(self):
    max_temperature = ( 25 + 273.15 ) * 10;
    min_temperature = ( -25 + 273.15 ) * 10;
    current_setpoint = ( self.setpoint + 273.15 ) * 10;
    return int(min(max(current_setpoint, min_temperature), max_temperature));

  ## Computes the code the program for the current manipulated_var
  #
  # @param self An instance of TemperatureControl
  #
  # @returns The code (int) representing the manipulated_var
  def manipulated_var_to_code(self):
    max_mv = ( ( ( 2.7  - 0.49548 ) / 2.7098 / 5.0 ) / 4.096 + 1 ) * 4096;
    min_mv = ( ( ( 0 - 0.49548 ) / 2.7098 / 5.0 ) / 4.096 + 1 ) * 4096;
    current_mv = ( ( ( self.manipulated_var - 0.49548 ) / 2.7098 / 5.0 ) / 4.096 + 1 ) * 4096;
    return int( min( max( current_mv, min_mv ), max_mv ) );

  ## From the temperature code calculates it's decimal celcius value
  #
  # @param self An instance of TemperatureControl
  # @param code (int) Temperature code (readed from camera)
  #
  # @returns The temperature in celcius degrees (float)
  def temperature_code_to_celcius(self, code):
    return (code/10.0) - 273.15;

  ## Generates the bytecode to program the current temperature control configuration.
  #
  # @param self An instance of TemperatureControl
  # @param formatter (binary.ByteCode) A ByteCode formatter to pass codes (int) to bytes (str)
  #
  # @returns ByteCode lines ([str...]) to program the camera.
  def get_configuration_bytecode(self, formatter = binary.ByteCode()):
    bytecode_lines = [];

    if(self.manual):
      manipulated = self.manipulated_var_to_code();

      bytecode_lines.append(formatter.pid_set_manipulated_variable(manipulated));
      bytecode_lines.append(formatter.pid_disable());
      bytecode_lines.append(formatter.pid_manual_mode_enable());

    else:
      k = self._k_pid_to_k_123_code();
      setpoint = self._setpoint_to_code();

      bytecode_lines.append(formatter.pid_set_k1(k[0]));
      bytecode_lines.append(formatter.pid_set_k2(k[1]));
      bytecode_lines.append(formatter.pid_set_k3(k[2]));
      bytecode_lines.append(formatter.pid_set_setpoint(setpoint));
      bytecode_lines.append(formatter.pid_manual_mode_disable());
      bytecode_lines.append(formatter.pid_enable());

    return bytecode_lines;

  ## Generates the bytecode to get the current CCD temperature.
  #
  # @param self An instance of TemperatureControl
  # @param formatter (binary.ByteCode) A ByteCode formatter to pass codes (int) to bytes (str)
  #
  # @returns ByteCode lines ([str...]) to send to the camera.
  def get_temperature_bytecode(self, formatter = binary.ByteCode()):
    return [formatter.pid_get_temperature()];

  ## @var manual
  #  (bool) Whenever manual mode is enabled.
  ## @var manipulated_var
  #  (float) The voltage applied to control the peltier strength. (For manual mode)
  ## @var setpoint
  #  (float) The target temperature. (For PID mode)
  ## @var k
  #  ((float,)*3) The k_p, k_i and k_d constants of the PID.
