from .base import DAQBase

try:
    from mcculw import ul
    from mcculw.enums import InterfaceType, ScanOptions, Status
    from mcculw.device_info import DaqDeviceInfo
    from mcculw.ul import ULError
except ImportError:
    ul = InterfaceType = ScanOptions = Status = DaqDeviceInfo = ULError = None

import numpy as np
import ctypes
from ctypes import POINTER, c_double

class MCCULWDAQ(DAQBase):
    def __init__(self, samples_per_channel, n_chirp, chirp_t, rate):
        super().__init__(samples_per_channel, n_chirp, chirp_t, rate)
        self.board_num = 0
        self.range = None
        self.status = Status.IDLE if Status else 0
        self.memhandle = None
        self.ctypes_array = None

    def connect(self):
        if ul is None:
            raise RuntimeError("MCCULW library not available")
        try:
            ul.ignore_instacal()
            device_list = ul.get_daq_device_inventory(InterfaceType.ANY)
            if not device_list:
                raise RuntimeError("No MCC DAQ devices found")
            ul.create_daq_device(self.board_num, device_list[0])
            ai_info = DaqDeviceInfo(self.board_num).get_ai_info()
            ranges = ai_info.supported_ranges
            self.range = ranges[0]
            total_count = self.samples_per_channel
            self.memhandle = ul.scaled_win_buf_alloc(total_count)
            if self.memhandle == 0:
                raise RuntimeError("Failed to allocate memory buffer")
            self.ctypes_array = ctypes.cast(self.memhandle, POINTER(c_double))
        except ULError as e:
            raise RuntimeError(f"Error connecting to MCC DAQ: {e}")

    def disconnect(self):
        if ul is not None:
            try:
                ul.release_daq_device(self.board_num)
                if self.memhandle:
                    ul.win_buf_free(self.memhandle)
                    self.memhandle = None
                    self.ctypes_array = None
            except ULError:
                pass

    def a_in_scan(self):
        if ul is None:
            raise RuntimeError("MCCULW library not available")
        try:
            ul.set_trigger(self.board_num, 12, 0 ,0)
            rate = ul.a_in_scan(
                self.board_num,
                0,
                0,
                self.samples_per_channel,
                self.rate,
                self.range,
                self.memhandle,
                (ScanOptions.BACKGROUND | ScanOptions.EXTTRIGGER | ScanOptions.SCALEDATA)
            )
        except ULError as e:
            raise RuntimeError(f"Error starting scan: {e}")
        return rate

    def get_scan_status(self):
        if ul is None:
            return Status.IDLE
        try:
            status, _, _ = ul.get_status(self.board_num, 1)
            return status
        except ULError:
            return Status.IDLE

    def scan_stop(self):
        if ul is not None:
            try:
                ul.stop_background(self.board_num, 0)
            except ULError:
                pass

    def release(self):
        self.disconnect()

    def get_data_array(self):
        # Convert ctypes array to numpy array
        return np.ctypeslib.as_array(self.ctypes_array, shape=(self.samples_per_channel,)).copy()