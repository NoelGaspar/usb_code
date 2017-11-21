#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#

## @package usb
#
# Module to interact with libusb1 in a simplified manner.
#
# This module only works with bulk transfers. It makes all calls blocking
# (even asynchronous transfers).

import usb1 as usb
import six as six

## For libusb1 status human-readable printing. For internal use only.
transfer_status_dict = \
{ \
  usb.TRANSFER_COMPLETED : 'TRANSFER_COMPLETED',
  usb.TRANSFER_ERROR     : 'TRANSFER_ERROR',
  usb.TRANSFER_TIMED_OUT : 'TRANSFER_TIMED_OUT',
  usb.TRANSFER_CANCELLED : 'TRANSFER_CANCELLED',
  usb.TRANSFER_STALL     : 'TRANSFER_STALL',
  usb.TRANSFER_NO_DEVICE : 'TRANSFER_NO_DEVICE',
  usb.TRANSFER_OVERFLOW  : 'TRANSFER_OVERFLOW' \
};

## Callback to send succesive transfer calls
# Use with _TransferCollector as a async_process
class _AsyncWriter:

  ## Initializes a _AsyncWriter.
  #
  # @param self An instance of _AsyncWriter
  # @param original_data (str or bytes) The data to transfer, will be chuncked
  # @param buffer_size (int) The size of bytes to transfer per bulk transfer 
  def __init__(self, original_data, buffer_size):
    self.pending_transfers = [];
    # Slice data in buffer_size
    for ii in six.moves.range(0, len(original_data), buffer_size):
      data = original_data[ii:(ii+buffer_size)];
      self.pending_transfers.append(''.join(data));
    # Reverse order for LIFO access (using pop())
    self.pending_transfers = reversed(pending_transfers);

  ## Gets next bytes to transfer or None if empty
  #
  # @param self An instance of _AsyncWriter
  def _next_bytes(self):
    if(len(self.pending_transfers) == 0):
      return None;
    else:
      return self.pending_transfers.pop();

  ## Prepares a transfer and (re)sumbits it.
  #
  # @param self An instance of _AsyncWriter
  # @param transfer (libusb1.Transfer) The transfer object to prepare.
  def prepare_next_transfer(self, transfer):
    data = self._next_bytes();
    if(data):
      transfer.setBuffer(data);
      transfer.submit();

  ## Get the results of the transfer
  #
  # @param self An instance of _AsyncWriter
  #
  # @returns None (since is a write operation)
  def get_result(self):
    return None;

  ## Process the transfer every time it has a status update
  #
  # @param self An instance of _AsyncWriter
  # @param transfer (libusb1.Transfer) The transfer object to process.
  def __call__(self, transfer):
    if(transfer.getStatus() != usb.TRANSFER_COMPLETED):
      return;
    else:
      self.prepare_next_transfer(transfer);
  
  ## @var pending_transfers
  # A LIFO list of the data still to be transfered ([str...])

## Callback to accumulate succesive transfer calls
# Use with _TransferCollector as a async_process
class _AsyncReader:

  ## Initializes a _AsyncReader.
  #
  # @param self An instance of _AsyncReader
  def __init__(self):
    self.transfers = [];

  ## Prepares a transfer and (re)sumbits it.
  #
  # @param self An instance of _AsyncReader
  # @param transfer (libusb1.Transfer) The transfer object to prepare.
  def prepare_next_transfer(self, transfer):
    transfer.submit();

  ## Get the results of the transfer
  #
  # @param self An instance of _AsyncReader
  #
  # @returns The recieved data (str or bytes)
  def get_result(self):
    result = [byte for data in self.transfers for byte in data];
    return ''.join(result);

  ## Process the transfer every time it has a status update
  #
  # @param self An instance of _AsyncReader
  # @param transfer (libusb1.Transfer) The transfer object to process.
  def __call__(self, transfer):
    if(transfer.getStatus() != usb.TRANSFER_COMPLETED):
      return;
    else:
      self.transfers.append(transfer.getBuffer()[:transfer.getActualLength()]);
      transfer.submit();

  ## @var transfers
  # A FIFO list of the data recieved ([str...])

## A collector of asyncronous transfer of data.
# Stops collection after port.timeout time of recieving/sending the last transfer.
#
# It uses a asynchronous processor which has to comply with the following interface:
# A prepare_next_transfer method, which recieves a transfer and submits them if necesary.
# A __call__ method, which recieves a transfer on each transfer state change and proceses it.
#
# @see _AsyncReader
# @see _AsyncWriter
class _TransferCollector:

  ## Initializes a _TransferCollector.
  #
  # @param self An instance of _TransferCollector
  # @param transfer_size (int) The size of each transaction
  # @param pararell_transfers (int) The size of each transaction
  # @param port (usb.Port) The port from where the transactions will be done.
  # @param async_process An asynchronous processor as described on this class.
  def __init__(self, transfer_size, pararell_transfers, port, async_process):
    self.processor = async_process;
    self.port = port;
    transfers = [];

    # Queue transfers
    for ii in range(pararell_transfers):
      transfer = port.device.dev.getTransfer();
      transfer.setBulk(
        port.address,
        transfer_size,
        callback=self.processor,
        timeout=port.timeout );
      async_process.prepare_next_transfer(transfer);
      transfers.append(transfer);
    self.transfers = transfers;

  ## Activate data collection / send
  #
  # @param self An instance of _TransferCollector
  #
  # @returns The result of the transaction. Depending on self.processor
  # @see _AsyncReader
  # @see _AsyncWriter
  def __call__(self):
    # Collect tranfers with _AsyncReader while there are active transfers.
    while any(x.isSubmitted() for x in self.transfers):
      try:
        self.port.device.context.handleEvents();
      except usb.USBErrorInterrupted:
        pass;
    return self.processor.get_result();

  ## @var processor
  # An asynchronous processor as described on this class.
  ## @var port
  # The port (usb.Port) in which the transactions are taking place.
  ## @var transfers
  # ([libusb1.Transfer]) The quequed transfers of this collector.

## Port class for creating syncronous / asyncronous transfers
# Intance this class from a usb.Device
class Port:

  ## Initializes a Port.
  #
  # @param self An instance of Port
  # @param device (usb.Device) The device this port belongs.
  # @param address (int) Port address.
  # @param timeout (float) Timeout (in seconds) for transactions done with this port. (None = Infinite)
  def __init__(self, device, address, timeout = None):
    self.device = device;
    self.address = address;

    self.timeout = timeout;
    if(timeout is None):
      self.timeout = 0;

  ## Perform a synchronous read
  #
  # @param self An instance of Port
  # @param length (int) Number of bytes to read.
  #
  # @returns The read data (str or bytes)
  def read_sync(self, length):
    data = self.device.dev.bulkRead(self.address, length, timeout=self.timeout);
    return data;

  ## Perform a synchronous write
  #
  # @param self An instance of Port
  # @param data (str or bytes) Data to send
  #
  # @returns Operation succesfull (True) or not (False)
  def write_sync(self, data):
    return self.device.dev.bulkWrite(self.address, data, timeout=self.timeout);

  ## Perform a asynchronous read
  #
  # @param self An instance of Port
  # @param length (int) Size of each transfer
  # @param pararell_transfers (int) Number of pararel transfers.
  #
  # @returns The read data (str or bytes)
  def read_async(self, length, pararell_transfers = 32):
    return _TransferCollector(length, pararell_transfers, self, _AsyncReader());

  ## @var device
  #  (usb.Device) The device this port belongs.
  ## @var address
  #  (int) Port address.
  ## @var timeout
  #  (float) Timeout (in seconds) for transactions done with this port.


## Device class for creating ports
# It must be used in a context manager fashion. See <a href='https://www.python.org/dev/peps/pep-0343/'>Context managers</a>. 
class Device:

  ## Initializes a Device.
  #
  # @param self An instance of Device
  # @param vid (int) The USB vendor ID of the device.
  # @param pid (int) The USB product ID of the device.
  # @param context (libusb1.Context) The libusb1 context of the device. If None a new context wll be created.
  # @param interface (int) Interface of the device to open.
  def __init__(self, vid, pid, context = None, interface = 0):

    if(not context):
      self.backend = usb.USBContext();
      context = self.backend.__enter__();

    self.context = context;
    self.interface = interface;

    self.dev = context.openByVendorIDAndProductID(vid, pid, skip_on_error = False);    
    if self.dev is None:
      raise RuntimeError('Device not found');

    self.interface_handle = self.dev.claimInterface(self.interface);

  ## Context manager __enter__ method
  #
  # It adquires the interface of the device.
  #
  # @param self An instance of Device
  def __enter__(self):
    self.interface_handle.__enter__();
    return self;

  ## Context manager __exit__ method
  #
  # It releases the interface of the device. And the context if it was created on this object. 
  #
  # @param self An instance of Device
  # @param exception_type The type of the raised exception. None if no error happened.
  # @param exception_value The object of the raised exception. None if no error happened.
  # @param traceback The stack information of the raised exception. None if no error happened.
  def __exit__(self, exception_type, exception_value, traceback):
    self.interface_handle.__exit__(exception_type, exception_value, traceback);
    if(hasattr(self, 'backend')):
      self.backend.__exit__(exception_type, exception_value, traceback);

  ## Opens a port for sending / recieving data.
  #
  # @param self An instance of Device.
  # @param address (int) Port address.
  # @param timeout (float) Timeout (in seconds) for transactions done with this port.
  #
  # @returns A port (Port) for sending/recieving data
  def open_port(self, address, timeout = None):
    return Port(self, address, timeout);

  ## @var backend
  #  (libusb1.Context) Same as context. This attribute exists only if the USB context was created by the Device Itself
  ## @var context
  #  (libusb1.Context) The libusb1 context the device is using.
  ## @var interface
  #  (int) The number of the USB interface being used by this device
  ## @var dev
  #  (libusb1.Device) The libusb1 device object this device is simplifying
  ## @var interface_handle
  #  (libusb1.Interface) The libusb1 interface object this device is using on __enter__ and __exit__
