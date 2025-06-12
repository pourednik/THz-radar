from .base import DAQBase

# If uldaq is not available on your dev machine, wrap imports in try/except
try:
    from uldaq import (
        get_daq_device_inventory,
        DaqDevice,
        ScanOption,
        AInScanFlag,
        ScanStatus,
        create_float_buffer,
        InterfaceType,
        AiInputMode,
    )
except ImportError:
    # In case you want to run tests without hardware
    get_daq_device_inventory = DaqDevice = ScanOption = AInScanFlag = ScanStatus = (
        create_float_buffer
    ) = InterfaceType = AiInputMode = None

import numpy as np


class RealDAQ(DAQBase):
    """A real DAQ device implementation."""

    def __init__(self, samples_per_channel, n_chirp, chirp_t, rate):
        super().__init__(samples_per_channel, n_chirp, chirp_t, rate)
        self.daq_device = None
        self.ai_device = None
        self.cdata = None
        self.range = None
        self.status = ScanStatus.IDLE if ScanStatus else 0

    def connect(self):
        interface_type = InterfaceType.ANY
        devices = get_daq_device_inventory(interface_type)
        if not devices:
            raise RuntimeError("Error: No DAQ devices found")
        self.daq_device = DaqDevice(devices[0])
        self.daq_device.connect(connection_code=0)
        self.ai_device = self.daq_device.get_ai_device()
        if self.ai_device is None:
            raise RuntimeError("DAQ device does not support analog input")
        ai_info = self.ai_device.get_info()
        ranges = ai_info.get_ranges(AiInputMode.SINGLE_ENDED)
        trigger_types = ai_info.get_trigger_types()
        self.ai_device.set_trigger(trigger_types[0], 0, 0, 0, 0)
        self.cdata = create_float_buffer(1, self.samples_per_channel)
        self.range = ranges[0]

    def disconnect(self):
        if self.daq_device and self.daq_device.is_connected():
            self.daq_device.disconnect()

    def a_in_scan(self):
        self.status = self.ai_device.a_in_scan(
            0,
            0,
            AiInputMode.SINGLE_ENDED,
            self.range,
            self.samples_per_channel,
            self.rate,
            ScanOption.EXTTRIGGER,  # External trigger synchronization
            AInScanFlag.DEFAULT,
            self.cdata,
        )
        return self.status

    def get_scan_status(self):
        status, _ = self.ai_device.get_scan_status()
        return status

    def scan_stop(self):
        if self.ai_device:
            self.ai_device.scan_stop()

    def release(self):
        if self.daq_device:
            self.daq_device.release()

    def get_data_array(self):
        return np.ctypeslib.as_array(
            self.cdata, shape=(self.samples_per_channel,)
        ).copy()
