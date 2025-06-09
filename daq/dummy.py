import numpy as np
import time
import matplotlib.pyplot as plt


class DummyDAQ:
    def __init__(self, SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE):
        self.samples_per_ch = SAMPLES_PER_CH
        self.n_chirp = N_CHIRP
        self.chirp_duration = CHIRP_DURATION
        self.sample_rate = SAMPLE_RATE

        # Simulation parameters
        self.c = 3e8
        self.f0 = 15e9 * 18
        self.bandwidth = 200e6 * 18
        self.current_range = 2.0  # meters, initial distance
        self.target_velocity = 0.4  # meters/second
        self.sign = 1
        self.before = time.time()

        self.start_time = time.time()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def release(self):
        pass

    def scan_stop(self):
        pass

    def a_in_scan(self):
        return self.sample_rate

    def get_scan_status(self):
        return 0, None

    def get_data_array(self):
        now = time.time()
        step = now - self.before
        self.before = now

        # Distance at current time
        self.current_range += self.sign * self.target_velocity * step
        if self.current_range >= 3:
            self.sign = -1
        if self.current_range <= 1:
            self.sign = 1

        # Beat frequency for this range
        f_b = 2 * self.bandwidth * self.current_range / (self.c * self.chirp_duration)

        # Prepare output array
        chirp_len = int(self.chirp_duration * self.sample_rate)
        arr = np.zeros((self.n_chirp, chirp_len), dtype=np.float32)

        # Phase change per chirp for the given velocity (Doppler)
        # phase_n = 2 * π * f_b * t + chirp_idx * doppler_phase
        # Doppler phase per chirp:
        wavelength = self.c / (self.f0)
        doppler_phase_per_chirp = (
            4
            * np.pi
            * self.sign
            * self.target_velocity
            * self.chirp_duration
            / wavelength
        )

        t = np.arange(chirp_len) / self.sample_rate

        for chirp_idx in range(self.n_chirp):
            # Each chirp gets a phase shift for Doppler
            phase = chirp_idx * doppler_phase_per_chirp
            arr[chirp_idx, :] = np.sin(2 * np.pi * f_b * t + phase)

        # plt.figure(figsize=(12, 6))
        # plt.imshow(
        #     arr, aspect="auto", cmap="viridis", extent=(0, chirp_len, 0, self.n_chirp)
        # )
        # plt.colorbar(label="Amplitude")
        # plt.xlabel("Sample within Chirp")
        # plt.ylabel("Chirp Index")
        # plt.title("DummyDAQ Output (arr) before flattening")
        # plt.show()

        arr = arr.flatten()
        return arr
