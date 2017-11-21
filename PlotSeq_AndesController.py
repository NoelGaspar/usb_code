#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

import matplotlib.pyplot as plots
import AndesControllerLib.ccd as ccd
import AndesControllerLib.binary as binary


ccd = ccd.CCD_230_42();

ccd.n_cols = 5; #2048; #1072;
ccd.n_rows = 5; #2064; #1027;
ccd.n_times = 1;
ccd.x_bin = 1;
ccd.y_bin = 1;
# falling_time = 36;
# ccd.ccd_switch = falling_time;
# ccd.ccd_fall = falling_time;

plot_order = ['PC1D','PC2D','PC3D','PC4D','SC1L','SC2L','SCO','ORL','SWOL','TGD','DGD','PIXT','CRST'];


ccd.compile_configured_program();

program = ccd.get_configured_program();

# Simular una secuencia de fotos
plot = program.plot( \
  pin_labels = ccd.clock_pins,
  start_mode = 'init_sweep_out',
  max_cycles = 40000 ); #,
  #order = plot_order );

# Mostrar todos los modos.
plot = program.plot(pin_labels = ccd.clock_pins) #, order = ccd.clock_order);

for mode in program.modes:
	print mode.name, program.get_address(mode.name);

formatter = binary.ByteCode();
byte_code = ccd.get_configuration_bytecode(formatter)

file = formatter.as_legacy_file(byte_code, ' ');
with open('init_file.init', 'w') as f:
	f.write(file);

plots.show();
