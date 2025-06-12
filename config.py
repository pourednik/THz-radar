import numpy as np
import math  # Import math for rounding

class ConfigBase:
    USE_DUMMY = False
    USE_WINDOWS = False
    SAMPLE_RATE = 500000
    C = 3e8
    MULT_FACTOR = 18
    F0 = 15e9 * MULT_FACTOR
    PLOT_WIDTH = 900
    PLOT_HEIGHT = 900
    UPDATE_INTERVAL = 0.05  # seconds, for 20Hz

    # Default ranges for axes
    X_RANGE_MIN = -5
    X_RANGE_MAX = 5
    Y_RANGE_MIN = 1
    Y_RANGE_MAX = 3

    @classmethod
    def calculate_samples_per_ch(cls, chirp_duration, n_chirp):
        # Round chirp_duration to the nearest integer before calculation
        rounded_chirp_duration = round(chirp_duration * cls.SAMPLE_RATE)
        return int(n_chirp * rounded_chirp_duration)

    @classmethod
    def calculate_bandwidth(cls, gen_bw):
        return gen_bw * cls.MULT_FACTOR

class Config1(ConfigBase):
    N_CHIRP = 20
    CHIRP_DURATION = 0.61e-3
    SAMPLES_PER_CH = ConfigBase.calculate_samples_per_ch(CHIRP_DURATION, N_CHIRP)
    GEN_BW = 200e6
    BANDWIDTH = ConfigBase.calculate_bandwidth(GEN_BW)
    CHIRP_REAL_DURATION = 0.617016e-3
    RANGE_FFT_INTERP = 2
    VELOCITY_FFT_INTERP = 4
    CHIRP_FFT_INTERP = 128
    DELAY = CHIRP_DURATION - CHIRP_REAL_DURATION
    RESAMPLE = False

class Config2(ConfigBase):
    N_CHIRP = 20
    CHIRP_DURATION = 0.9e-3
    SAMPLES_PER_CH = ConfigBase.calculate_samples_per_ch(CHIRP_DURATION, N_CHIRP)
    GEN_BW = 600e6
    BANDWIDTH = ConfigBase.calculate_bandwidth(GEN_BW)
    CHIRP_REAL_DURATION = 0.9027243e-3
    RANGE_FFT_INTERP = 5
    VELOCITY_FFT_INTERP = 4
    CHIRP_FFT_INTERP = 8
    DELAY = CHIRP_DURATION - CHIRP_REAL_DURATION
    RESAMPLE = False

class Config3(ConfigBase):
    N_CHIRP = 20
    CHIRP_DURATION = 1.5e-3
    SAMPLES_PER_CH = ConfigBase.calculate_samples_per_ch(CHIRP_DURATION, N_CHIRP)
    GEN_BW = 1000e6
    BANDWIDTH = ConfigBase.calculate_bandwidth(GEN_BW)
    CHIRP_REAL_DURATION = 1.504538e-3
    RANGE_FFT_INTERP = 5
    VELOCITY_FFT_INTERP = 4
    CHIRP_FFT_INTERP = 8
    DELAY = CHIRP_DURATION - CHIRP_REAL_DURATION
    RESAMPLE = True
    t3 = np.load("./sampling_500ksps_15_1000MHz_1_5ms.npy")

class Config4(ConfigBase):
    N_CHIRP = 20
    CHIRP_DURATION = 0.2e-3
    SAMPLES_PER_CH = ConfigBase.calculate_samples_per_ch(CHIRP_DURATION, N_CHIRP)
    GEN_BW = 140e6
    BANDWIDTH = ConfigBase.calculate_bandwidth(GEN_BW)
    CHIRP_REAL_DURATION = 0.2007509e-3
    RANGE_FFT_INTERP = 2
    VELOCITY_FFT_INTERP = 4
    CHIRP_FFT_INTERP = 128
    DELAY = CHIRP_DURATION - CHIRP_REAL_DURATION
    RESAMPLE = False

# Default configuration
current_config = Config1
