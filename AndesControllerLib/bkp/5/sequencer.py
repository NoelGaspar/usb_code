#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package sequencer
#
# Generation of Andes Controller sequencer programs.
#
# This module exposes the ProgramBuilder class to generate Andes Controller sequencer programs.

# Defined classes:
#   Program
#   ProgramBuilder
#   Mode
#   State
#   Labels

import log as log;
import six as six;


## An already compiled Andes Controller sequencer program.
# @note For read-only use. To build programs use ProgramBuilder
class Program:

	## Initializes a compiled program.
	# @note Do not call direclty, use ProgramBuilder instead.
	#
	# @param self An instance of Program
	# @param codes ([int...]) Binary value of the memory to be written at each index.
	# @param mode_addresses ({str:int...}) Cache of the program's modes location.
	# @param modes ([sequencer.Mode]) Source modes of the program compiled in codes.
	# @param log (log._Log) The logging context
	def __init__(self, codes, mode_addresses, modes, log=log.get_default_context()):
		self.codes = codes;
		self.address_map = mode_addresses;
		self.modes = modes;
		self.log = log;

	## Get the location in memory of a mode
	#
	# @param self An instance of Program
	# @param mode (str) Name of the mode.
	#
	# @returns The address (int) of the mode.
	def get_address(self, mode):
		return self.address_map[mode];

	## Retruns a string of the program contents.
	#
	# If labels is provided, state pin names are included.
	#
	# @param self An instance of Program
	# @param labels ({str:int}) Name of the sequencer pins.
	#
	# @returns A human-readable string representation of the program.
	def as_str(self, labels = None):
		result = [];
		for c in self.codes:
			if((c >> 63) == 1):
				result.append(Mode.format_code(c, self.address_map));
			else:
				result.append(State.format_code(c, labels));
		return '\n'.join(result);

	## Gets all the defined mode names in the program.
	#
	# @returns A list of all the mode names (str) in the program.
	def mode_names(self):
		return [m.name for m in self.modes];

	## Gets the mode with the specified name.
	#
	# @param self An instance of Program
	# @param name (str) The name of the mode
	#
	# @returns A mode with the specified name.
	def get_mode(self, name):
		for mode in self.modes:
			if(name == mode.name):
				return mode;
		raise ValueError('Mode with name '' + str(name) + '' not found in program.');

	## Alias for self.as_str(None)
	#
	# @see as_str
	#
	# @param self An instance of Program
	#
	# @returns A human-readable string representation of the program.
	def __str__(self):
		return self.as_str();


	## Plots the program modes.
	#
	# If a start mode is specified, the plot will simulate a program run.
	#
	# @note: Requires matplotlib to be installed.
	#
	# @param self An instance of Program
	# @param pin_labels ({str:int...}/sequencer.Labels) A mapping between pin names and addresses.
	# @param start_mode (str) The mode in which to start the simulation.
	# @param max_cycles (int) Maximum length of the simulation.
	#
	# @returns A matplotlib handler.
	def plot(self, pin_labels = None, start_mode = None, max_cycles = 100000):
		import matplotlib.pyplot as plots;
		import matplotlib.patches as patches;
		import matplotlib.lines as lines;
		
		# Determine which modes to plot
		plot_modes = self.modes;
		if(start_mode is not None):
			tot_time = 0;
			nested_count = 0;

			plot_modes = [];
			next_mode = self.get_mode(start_mode);

			while(tot_time < max_cycles):
				current_mode = next_mode;
				next_mode = self.get_mode(current_mode.next_mode_name);
				
				mode_time = 0;
				mode_multiplier = current_mode.n_loops;

				for state in current_mode.states:
					mode_time += state.hold_time;

				if(current_mode.n_loops <= 0):
					plot_modes.append(current_mode);
					break;
				else:
					if(current_mode.is_nested()):
						if(nested_count < current_mode.nested_loops):
							nested_count += 1;
							mode_multiplier = 1;
							next_mode = self.get_mode(current_mode.parent_mode_name);
						else:
							mode_multiplier = 0;
							nested_count = 0;

				plot_modes.extend([current_mode]*mode_multiplier);
				tot_time += mode_time * mode_multiplier;

		# Plot modes
		fig = plots.figure();
		axes = fig.add_subplot(111, aspect='equal');

		current_time = 0;
		parity = False;

		plot_values = {};

		for mode in plot_modes:
			current_duration = 0;
			to_plot = mode._expand_states(pin_labels);
			for k in to_plot.keys():
				current_duration = max(current_duration, len(to_plot[k]));
				if(k not in plot_values):
					plot_values[k] = (len(plot_values), [], []);

			if(parity):
				pos_y = 0;
				size_y = len(plot_values.keys());
				pos_x = current_time;
				size_x = current_duration;
				bg = patches.Rectangle((pos_x, pos_y), size_x, size_y, alpha=0.1, facecolor='#000000', edgecolor=None, fill=True);
				axes.add_patch(bg);
			parity = not parity;

			axes.text(current_time + current_duration/2, len(plot_values.keys()) + 1, mode.name,
				horizontalalignment='center',
				verticalalignment='top');

			for k in to_plot.keys():
				axes.text(-0.1 + current_time, plot_values[k][0] + 0.5, k, horizontalalignment='right', verticalalignment='center');

				values = [v*0.9 + plot_values[k][0] for v in to_plot[k]];
				plot_values[k][1].extend(six.moves.range(current_time, current_time + current_duration));
				plot_values[k][2].extend(values);

			current_time += current_duration;

		self.log.info('Optimizing plots... ', 2);
		for pin in plot_values.keys():
			x_values = plot_values[pin][1];
			y_values = plot_values[pin][2];
			
			if(len(y_values) > 1):
				preserve = [0] + [ii+1 for ii in range(len(y_values) - 2) if y_values[ii] != y_values[ii+1] or y_values[ii+1] != y_values[ii+2]] + [len(y_values) -1];
				x_values = [x_values[ii] for ii in preserve];
				y_values = [y_values[ii] for ii in preserve];
				plots.step(x_values, y_values);
		self.log.info('Done.', 2);

		axes.axis('auto');

		plots.tick_params(
			axis='y',
			which='both',
			bottom='off',
			top='off',
			labelbottom='off',
			labeltop='off');

		return fig;

	## @var codes
	#  ([int...]) Binary value of the memory to be written at each index.
	## @var address_map
	#  ({str:int...}) Cache of the program's modes location.
	## @var modes
	# ([sequencer.Mode]) Source modes of the program compiled in codes.      
	## @var log
	# (log._Log) The logging context



## A class to build Andes Controller secuencer programs.    
class ProgramBuilder:

	## Maximum number of lines the program can have (the memory is 1024x96 bits)
	_max_n_lines = 2**10 - 1;

	## Initializes a ProgramBuilder
	#
	# @param self An instance of ProgramBuilder
	# @param log The logging context.
	def __init__(self, log = log.get_default_context()):
		self.modes = [];
		self.log = log;

	## Adds a mode to the current program
	#
	# Will raise error if another mode with equal name has been registered.
	#
	# @param self An instance of ProgramBuilder
	# @param mode (sequencer.Mode) The mode to add.
	def add_mode(self, mode):
		# Check repeated modes
		name = mode.name;
		if(name in self.mode_names()):
			raise ValueError('There is already a mode named ' + str(name));

		# Add mode
		self.modes.append(mode);

	## Gets all the mode names in the program so far.
	#
	# @param self An instance of ProgramBuilder
	#
	# @returns A list of all the mode names (str) in the program.
	def mode_names(self):
		return [m.name for m in self.modes];

	## Get a mode with a specifid name.
	#
	# @param self An instance of ProgramBuilder
	# @param name (str) The name of the mode.
	#
	# @returns The mode (sequencer.Mode) with the specified name.
	def get_mode(self, name):
		for m in self.modes:
			if m.name == name:
				return m;
		raise ValueError('There is no mode named: ' + str(name));

	## Creates an Andes Controller sequencer program.
	#
	# @param self An instance of ProgramBuilder
	# @param log (log._Log) The log context to give to the new Program.
	#
	# @returns A compiled program (sequencer.Program).
	def build(self, log=None):
		if(log is None):
			log = self.log;

		# Create an address cache, storing the memory index in which each mode will be written
		address_cache = {};
		current_address = 0;
		for mode in self.modes:
			address_cache[mode.name] = current_address;
			current_address += len(mode.states) + 1;

		# Consistency checks
		error = False;
		for mode in self.modes:
			try:
				self.get_mode(mode.next_mode_name);
			except:
				error = True;
				self.log.error('Next mode ' + str(mode.next_mode_name) + ' for mode ' + str(mode.name) + ' does not exist.');

			if(mode.is_nested()):
				try:
					parent = self.get_mode(mode.parent_mode_name);
					if(parent.is_nested()):
						error = True;
						self.log.error('Double nested modes detected: ' + str(mode.name) + ' in ' + str(parent.name) + ' in ' + str(parent.parent_mode_name) + '.');
				except:
					error = True;
					self.log.error('Parent mode '' + str(mode.parent_mode_name) + '' for mode ' + str(mode.name) + ' does not exist.');

		if(error):
			raise ValueError('Compilation stopped because of consistency errors. Check log.');

		codes = [];
		for mode in self.modes:
			codes.append( mode.get_code(address_cache) );
			for state in mode.states:
				codes.append( state.get_code() );

		# Check maximum memory length
		if len(codes) > self._max_n_lines:
			raise ValueError('Compilation stopped because of maximum memory lines restriction (' + str(len(codes)) + '/' + str(self._max_n_lines) + ')')

		return Program(codes, address_cache, self.modes, log);

	## @var modes
	#  ([sequencer.Mode...]): List of registered modes.
	## @var log
	#  (log._Log): The logging context.



## A sequencer mode.
#
class Mode:
	## Default value of a mode address
	_invalid_mode = 2**10 -1;
	## Maximum value n_loops can have
	_max_n_loops = 2**16 - 1;
	## Maximum value nested_loops can have
	_max_n_loops_nested = 2**16 - 1;
	## Maximum number of states the mode can have
	_max_n_states = 2**10 - 1;

	## Initializes a Mode.
	#
	# @param self An instance of Mode
	# @param name (str) The name of the mode.
	# @param n_loops (int) The number of times this mode runs before jumping to the next mode (0 = infinite).
	# @param next_mode_name (str) The name of the mode to jump after this mode finishes.
	# @param parent_mode_name (str) The name of the parent mode of this mode (if this mode is nested).
	# @param nested_loops (int) The number of times to jump to the parent mode before jumping to the next mode.
	def __init__(self, name, n_loops, next_mode_name = None, parent_mode_name = None, nested_loops = None):
		self.name = name;

		if(n_loops > self._max_n_loops):
			raise ValueError('n_loops (' + str(n_loops) + ') is out of range [0...' + str(self._max_n_loops) + '].');      
		self.n_loops = n_loops;

		self.next_mode_name = next_mode_name;

		if(parent_mode_name):
			self.parent_mode_name = parent_mode_name;
			if(not nested_loops):
				raise ValueError('Must give a value to nested_loops if parent_mode_name is specified.');
			if(nested_loops > self._max_n_loops_nested):
				raise ValueError('nested_loops (' + str(nested_loops) + ') is out of range [0...' + str(self._max_n_loops_nested) + '].');
			self.nested_loops = nested_loops;

		self.states = [];

	## Gets the time evolution of the modes states.
	#
	# Useful for plotting. If pin_labels is provided, names instead of addresses will be keys of the pin states.
	#
	# @param self An instance of Mode
	# @param pin_labels ({str:int...}/sequencer.Labels) A mapping between pin names and addresses.
	#
	# @returns A dict {str:[int...]} containing the time evolution of each pin.
	def _expand_states(self, pin_labels = None):
		pin_dir = pin_labels;
		if(pin_dir is None):
			pin_dir = {};
			for ii in range(32):
				pin_dir[str(ii)] = ii;

		result = {};
		for k in pin_dir.keys():
			result[k] = [];

		for state in self.states:
			for k in pin_dir.keys():
				pin_value = state.get_value_of_address(pin_dir[k]);
				result[k].extend([pin_value]*state.hold_time);

		return result;

	## Appends a state to the end of the mode
	#
	# @param self An instance of Mode
	# @param state (sequencer.state) The state to add.
	def add_state(self, state):
		if(len(self.states) >= self._max_n_states):
			raise ValueError('Number of states per mode limit (' + str(self._max_n_states) + ') reached.');
		self.states.append(state);

	## Appends many states to the end of the mode
	#
	# @param self An instance of Mode
	# @param states (iter of sequencer.state) An iterable containing states.
	def add_states(self, states):
		for state in states:
			self.add_state(state);

	## Get if this node has a parent.
	#
	# @returns True if it has a parent, False otherwise.
	def is_nested(self):
		return hasattr(self, 'parent_mode_name');
		
	## Get the binary data associated with this mode.
	#
	# @param self An instance of Mode
	# @param address_cache ({str:int...}) The cache of the mode's addresses.
	#
	# @returns The binary code (int) representing this mode.
	#	range			|95..88	|    87..72			|      71..56		|     55..40		|      39..32		|     31..16	|    15..0		 |
	#	bit length		|  8	|      16			|        16			|     	16			|        8			|       16		|      16		 |  96
	#	name python		|  0	|   len(states)		|     n_loops		|   nested_loops	|     is_nested		|  next_address	| parent_address | TOTAL
	#	name verilog	|  0	| CURRENT_NSTATES	|  CURRENT_NLOOPS	|  CURRENT_NNESTED	| CURRENT_IF_NESTED	|    NEXT_ADDR	|  PARENT_ADDR	 |
	def get_code(self, address_cache):
		is_nested = 0;
		nested_loops = 0;

		if(self.is_nested()):
			is_nested = 1;
			nested_loops = self.nested_loops;

		#mode_address = address_cache[self.name];
		
		next_address = self._invalid_mode;
		if(self.next_mode_name):
			next_address = address_cache[self.next_mode_name];
		
		parent_address = self._invalid_mode;
		if(self.is_nested()):
			parent_address = address_cache[self.parent_mode_name];

		code = 0;									# 96 bits total (3 x 32 bit words)
		code = code | parent_address;				# 16 bits
		code = code | (next_address << 16);			# 16 bits
		code = code | (is_nested << 32);			#  8 bits
		code = code | (nested_loops << 40);			# 16 bits
		code = code | (self.n_loops << 56);			# 16 bits
		code = code | (len(self.states) << 72);		# 16 bits
		code = code | (0x80 << 88);					#  8 bits

		print '\nMode', self.name, ':\n', self.format_code(code, address_cache)
		return code;

	@classmethod
	## Create a human-redable representation of a mode's code
	#
	# If addresses is provided, modes names will be shown to parent and next modes.
	# 
	# @note This is a class method.
	#
	# @param cls An instance of Mode class
	# @param code (int) The code to represent
	# @param addresses ({str:int...}) The cache of the mode's addresses.
	def format_code(cls, code, addresses = None):

		parent_address =  code        & 0xFFFF;
		next_address   = (code >> 16) & 0xFFFF;
		is_nested      = (code >> 32) & 0xFF;
		nested_loops   = (code >> 40) & 0xFFFF;
		n_loops        = (code >> 56) & 0xFFFF;
		n_states       = (code >> 72) & 0xFFFF;

		def conform_str(string, length):
			return ' '*max(0, (length - len(string))) + string;

		min_str_len = 3;
		if(addresses):
			min_str_len_label = min_str_len;
			for k in addresses.keys():
				min_str_len_label = max(min_str_len_label, len(k));

			next_label   = '<unknown>';
			parent_label = '<unknown>';

			for k in addresses.keys():
				if(addresses[k] == parent_address):
					parent_label = k;
				if(addresses[k] == next_address):
					next_label = k;
				
				data = ['n_states:' + str(n_states), 'n_loops:' + str(n_loops), 'nested_loops:' + str(nested_loops), 'is_nested:' + str(is_nested), 'next_label:' + str(next_label), 'parent_label:' + str(parent_label)];
				#data = [1, n_states, n_loops, is_nested, next_label, parent_label, nested_loops];
				data_str = [conform_str(str(s), min_str_len) for s in data];
				data_str[4] = conform_str(data_str[4], min_str_len_label);
				data_str[5] = conform_str(data_str[5], min_str_len_label);

		else:
			data = ['n_states:' + str(n_states), 'n_loops:' + str(n_loops), 'nested_loops:' + str(nested_loops), 'is_nested:' + str(is_nested), 'next_address:' + str(next_address), 'parent_address:' + str(parent_address)];
			#data = [1, n_states, n_loops, is_nested, next_address, parent_address, nested_loops];
			data_str = [conform_str(str(s), min_str_len) for s in data];

		return ' | '.join(data_str);

	## @var name (str)
	#  The name (str) of the mode.
	## @var n_loops
	#  (int) The number of times this mode runs before jumping to the next mode (0 = infinite).
	## @var next_mode_name
	#  (str) The name of the mode to jump after this mode finishes.
	## @var parent_mode_name
	#  (str) The name of the parent mode of this mode (if this mode is nested).
	## @var nested_loops
	#  (int) The number of times to jump to the parent mode before jumping to the next mode.
	## @var states
	#  ([sequencer.State...]) The states of this mode.



## A sequencer state.
# Contains information of the pin output values and how much time to hold them.
class State:
	# Maximum value for hold_time.
	_max_hold_time = 2**24 - 1;		# In 10 ns increments
	# Maximum value for states length
	_max_states_length = 64

	## Initializes a State.
	#
	# @param self An instance of State
	# @param data (int) The value of each pin (in binary) of this mode.
	# @param hold_time (int) The number of cycles this state holds the data.
	def __init__(self, data, hold_time):
		self.data = data;

		if(hold_time < 0 or hold_time > self._max_hold_time):
			raise ValueError('hold_time (' + str(hold_time) + ') is out of range [0...' + str(self._max_hold_time) + '].');
		self.hold_time = hold_time;

	## Get the value of a pin of the state.
	#
	# @param self An instance of State
	# @param address (int) The address of the pin.
	#
	# @returns The value of the pin (int). Either 1 or 0.
	def get_value_of_address(self, address):
		return (self.data >> address) & 0x01;

	@classmethod
	## Creates a state from a list of each bit value.
	#
	# @note This is a class method.
	#
	# @param cls An instance of Mode class
	# @param data_bits ([str/int/bool...]) The value of each pin (in binary) of this mode.
	# @param hold_time (int) The number of cycles this state holds the data.
	#
	# @returns A State
	def from_bits(cls, data_bits, hold_time):
		bits = [int(bool(bit)) for bit in data_bits];	# Creates a list of 1's and 0's
		if(len(bits) > cls._max_states_length):
			raise ValueError('Too many bits (' + str(len(bits)) + ') for a sequencer state (max is ' + str(cls._max_states_length) + ').');
		if(len(bits) < cls._max_states_length):
			log.warning('There are less bits than the expected in a state (' + str(len(bits) ) + '/' + str(cls._max_states_length) + '), will fill MSBs with 0s.');

		# Generates the binary word
		data = 0;
		for ii in range(len(bits)):
			data = data | (bits[ii] << ii);
		return State(data, hold_time);

	@classmethod
	## Creates a state from a dictionary of each bit value.
	#
	# @note This is a class method.
	#
	# @param cls An instance of Mode class
	# @param labels ({str:int...}) The address of each pin name.
	# @param named_bits ({str:int/str...}) The value of each pin name.
	# @param hold_time (int): The number of cycles this state holds the data.
	#
	# @returns A State
	def from_labels(cls, labels, named_bits, hold_time):
		bits = [0] * cls._max_states_length;
		for k in named_bits.keys():
			bits[labels[k]] = named_bits[k];

		return cls.from_bits(bits, hold_time);

	@classmethod
	## Creates multiple states from a dictionary.
	#
	# The dictionary `named_bits` has to contains names of each pin name associated.
	# with a tuple containing the values of multiple states. The length of each tuple must
	# match `len(hold_times)`.
	#
	# @note This is a class method.
	#
	# @param cls An instance of Mode class
	# @param labels ({str:int...}) The address of each pin name.
	# @param named_bits ({str:iter(int/str)...}): The values of each pin name.
	# @param hold_times (tuple(int)): The number of cycles this state holds the data for each state.
	#
	# @returns A tuple containing States
	def from_labels_array(cls, labels, named_bits, hold_times):
		length = len(hold_times);
		for k in named_bits.keys():
			if(len(named_bits[k]) != length):
				raise ValueError('Length of label ' + str(k) + ' (' + str(len(named_bits[k])) + ') does not match length of hold_times (' + str(length) + ').');
	 
		result = [];
		for ii in range(length):
			result.append(cls.from_labels(labels, {k:named_bits[k][ii] for k in named_bits.keys()}, hold_times[ii]));
		return tuple(result);

	@classmethod
	## Create a human-redable representation of a state's code
	#
	# If labels is provided, pin names will be shown instead of addresses.
	#
	# @note This is a class method.
	#
	# @param cls An instance of Mode class
	# @param code (int) The code to represent
	# @param labels ({str:int...}) The name of each pin.
	#
	# @returns A human-readable representation (str) of a state's code
	def format_code(cls, code, labels = None):
		#data = (code & 0x7FFFFFFF80000000) >> 31;
		#time = (code & 0x7FFFFF80) >> 7;
		data = (code & 0x7FFFFFFF80000000) >> 31;
		time = (code & 0xFFFFFF);
		data_array = [''] * 32;
		for ii in range(32):
			data_array[ii] = (data >> ii) & 1;
			if(labels is None):
				data_array[ii] = str(data_array[ii]);
			else:
				label = None;
				for k in labels.keys():
					if(labels[k] == ii):
						label = str(k);
						break;
				if(label != None):
					data_array[ii] = str(label) + ':' + str(data_array[ii]) + '\n';
				else:
					data_array[ii] = None;
		if(labels):
			data_array = ['---- hold for: ' + str(time) + ' ----- \n'] + [d for d in data_array if d];
		else:
			data_array = data_array + [', hold for: ' + str(time)];
		return ' '.join(data_array);

	## Returns the code associated with this state
	#
	# @param self An instance of Mode
	#
	# @returns The code (int) associated with this state
	# Code
	#	range		  	|	95..88	|		87..24		  |		 23..0		   |
	#	bit length  	|	  8		|	  	  64		  |		  24		   |	 96
	#	name python 	|	  0		|	data (pin states) |	 hold_time (10ns)  |	TOTAL
	#	name verilog	|	  0		|		  SEQ		  |	CURRENT_HOLD_TIME  |
	def get_code(self):
		code = (self.data << 24) | (self.hold_time);
		print self.format_code(code)
		return code


	## @var data
	#  (int) The value of each pin (in binary) of this mode.
	## @var hold_time
	#  (int) The number of cycles this state holds the data.



## Labels of the pins of the sequencer.
# This class is basically a dict with a method to reverse it and
# repeated address-checking.
class Labels:

	## Initialize a sequencer labels
	#
	# @param self An instance of Labels
	# @param labels ({str:int...}): The address of each pin name.
	def __init__(self, labels):
		seen_values = [];
		repeated_keys = [];
		for k in labels.keys():
			v = labels[k];
			if(v in seen_values):
				repeated_keys.append(k);
			else:
				seen_values.append(v);

		if(len(repeated_keys) > 0):
			repeated_strs = [str(k) + ':' + str(labels[k]) for k in repeated_keys];
			raise ValueError('There are repeated indexes for labels: ' + ','.join(repeated_strs));

		self.labels = labels;

	## Gets the address associated with a name
	#
	# @param self An instance of Labels
	# @param label (str) The name of the pin
	#
	# @returns The address (int) associated with the name
	def __getitem__(self, label):
		return self.labels[label];

	## Gets the name associated with an address
	#
	# @param self An instance of Labels
	# @param address (int) The address of the pin
	#
	# @returns The label (str) associated with the address
	def label_of(self, address):
		for k in self.labels.keys():
			if(address == self.labels[k]):
				return k;
		raise ValueError('There is no label for address ' + str(address));

	## @var labels
	#  ({str:int...}): The address of each pin name.




if __name__ == '__main__':

	print '\n*** Testing sequencer.State ***\n'
	x = State.from_bits([1,1,1,1,0,0,0,0], 22)
	print x.format_code( x.get_code() )
