import AndesControllerLib.cam as lib

cam = lib.Camera()
cam.ccd.bin_x = 1
cam.ccd.bin_y = 1
cam.shutter.expose_time_ms  = 500
cam.shutter.open            = True

import pdb
pdb.set_trace()

cam.configure()
image = cam.take_picture()
print image
