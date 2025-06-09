import numpy as np


class DAQBase:
    """Abstract DAQ interface for both real and dummy implementations."""

    def __init__(self, samples_per_channel, n_chirp, chirp_t, rate):
        self.samples_per_channel = samples_per_channel
        self.n_chirp = n_chirp
        self.chirp_t = chirp_t
        self.rate = rate
        self.data_shape = (int(samples_per_channel / n_chirp / 2 + 1), n_chirp)
        self.data = np.zeros(self.data_shape)

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def a_in_scan(self):
        """Start scan and return the actual rate."""
        raise NotImplementedError

    def get_scan_status(self):
        """Return (status, ...) where status=0 means IDLE, 1 means RUNNING."""
        raise NotImplementedError

    def scan_stop(self):
        raise NotImplementedError

    def release(self):
        raise NotImplementedError

    def get_data_array(self):
        """Return a numpy array with the latest scan data."""
        raise NotImplementedError
