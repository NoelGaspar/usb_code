#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## This example configures the camera once and takes images a key is pressed.
# Stores a plot of the last taken image in ./plot_example.png

from __future__ import print_function;

import AndesControllerLib.cam as camLib
import matplotlib.image as images

# All this imports are only to be able to detect a keystroke.
import select;
import sys;
import tty;
import termios;


cam = camLib.Camera();

### Set CCD configuration ###
cam.ccd.bin_x = 1;					# Binning in the x and y direction
cam.ccd.bin_y = 1;
#cam.ccd.extra_int_time = 1;		# Extra integration time, for better image quality (and slower readouts)
cam.shutter.expose_time_ms = 500;	# Exposition time
cam.shutter.open = True;			# Open state of the shutter during exposition.

### Extra function for key detection ###
def hasKey():
	return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

old_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno());


# Enable debug mode
import pdb
pdb.set_trace()


try:
### Apply configuration ###
	print('Configuring...');
	cam.configure();
	print('Configuration complete.');

### Take pictures in a loop ###
	total_pictures = 0;
	exit = False;
	while(not exit):
		print('\rPictures taken ' + str(total_pictures) + ', press any key to stop... (after finishing this image)', end = '');
		sys.stdout.flush();

		image = cam.take_picture();
		images.imsave('./plot_example_' + str(total_pictures) + '.png', image, cmap='gray');

		total_pictures += 1;
		exit = hasKey();

except:
	print('Problem occurred during execution.')

finally:
	termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings);

print('\nProgram completed.');
