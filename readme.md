[//]: # (This is a markdown document. Use a markdown viewer for easier reading.)

![ASI logo](./docgen/asi_banner.png)

Andes Controller python usb interface
============

AndesControllerLib is a python package for controlling and obtaining images from an Andes Controller powered camera.

Requirements
------------
The package has the following requirements.

* Linux operating system
* Python 2.7
* Numpy
* Libsusb1 for python

Installation
------------
Install **python** and **numpy** using your distribution package manager (apt-get for ubuntu, pacman for arch, yum for centos, etc..). Example (ubuntu 16.04):

~~~
>> sudo apt-get install python2.7 python-numpy
~~~

Install **libsusb1 for python**. You can install it from the [github repository](https://github.com/vpelletier/python-libusb1), we the recommend installing it via pip. Example (ubuntu 16.04):

~~~
>> sudo apt-get install python-pip
>> pip install libusb1
~~~

Now to install **AndesControllerLib** navigate to the root directory of the installation package (where this readme is located) and run setup.py, depending on your python configuration you may or may not require super user privileges:

~~~
>> sudo python setup.py install
~~~

Permissions
------------

Depending on your system configuration you may need to call python (or python scripts) with super user privileges in order to communicate with an usb device.

The solution to this issue is either always call python with super user privileges or configure your operating system to let any user use the camera. See [udev](https://wiki.debian.org/udev) and [writing udev rules](http://reactivated.net/writing_udev_rules.html#example-printer) for debian-based systems. The camera vendor id is 0x04B4 and product id is 0x00F1.

Basic usage
------------

 1. Connect the camera to the computer.
 2. Open a console and run python.
    ~~~
    >> python
    ~~~
 3. Import AndesControllerLib.cam and instance a camera handle.
    ~~~
    >>> import AndesControllerLib.cam as lib
    >>> cam = lib.Camera()
    ~~~
 4. Specify the required camera parameters.
    ~~~
    >>> cam.ccd.bin_x = 1
    >>> cam.ccd.bin_y = 1
    >>> cam.shutter.expose_time_ms  = 500
    >>> cam.shutter.open            = True
    ~~~
 5. Apply the parameters and take the photo.
    ~~~
    >>> cam.configure()
    >>> image = cam.take_picture()
    ~~~

Examples
------------

The file [Example.py](Example.py) configures the camera once and takes pictures in a loop until a keystroke is detected. Check the file for useful comments.

Also a graphical user interface is provided in [AndesControllerUSB.py](AndesControllerUSB/AndesControllerUSB.py) which shows the camera operating in a threaded enviroment and provides a way of performing quick tests on the camera.

This GUI has extra requirements. It needs matplotlib and wxPython in order to run. Both can be installed using your package manager. Example (ubuntu 16.04):

~~~
>> sudo apt-get install python-matplotlib wxgtk3.0
~~~

The GUI is generated using wxglade. The project file Interface.wxg is provided if you want to modifiy it. The wxglade output has to be saved to AndesControllerUsb_Interface.py.

Documentation
------------
Doxygen-generated documentation can be found in [/doc/AndesControllerLib](/doc/AndesControllerLib/html/index.html) if you need to regenerate it or output a different type of documentation the doxyfile can be found on /docgen

Un-installation
------------
Like any setup.py package, you have to uninstall it by manually deleting the files. A semi-automatic option is to re-install the package with the --record option to list all the files and then use that list to unistall the libary.

 1. Create a list of all the package files (may require super-user permissions).
    ~~~
    >> sudo python setup.py install --record files.txt
    ~~~
 2. Uninstall the package (may require super-user permissions).
    ~~~
    >> cat files.txt | sudo xargs rm -rf
    ~~~
 3. Remove the list.
    ~~~
    >> rm files.txt
    ~~~
