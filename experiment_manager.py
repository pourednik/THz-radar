import numpy as np
import asyncio
from config import (
    SAMPLES_PER_CH, N_CHIRP, SAMPLE_RATE, CHIRP_DURATION, RANGE_FFT_INTERP,
    VELOCITY_FFT_INTERP, DELAY, CHIRP_FFT_INTERP, BANDWIDTH, CHIRP_REAL_DURATION, C
)

class ExperimentManager:
    def __init__(self, daq, gen):
        self.daq = daq
        self.gen = gen  # Optional generator instrument
        self.data_shape = (int(SAMPLES_PER_CH / N_CHIRP / 2 + 1) * RANGE_FFT_INTERP, N_CHIRP*VELOCITY_FFT_INTERP)
        self.data = np.zeros(self.data_shape)
        self.data_chirp = np.zeros(int(SAMPLES_PER_CH / N_CHIRP))
        self.stop_event = asyncio.Event()
        self.rate = SAMPLE_RATE
        self.status = 0
        self._fft_initialized = False
        self.update_in_progress = False

    def _init_fft_windows(self, chirp_len, n_chirp):
        self.fft_size = chirp_len * RANGE_FFT_INTERP
        self.n_chirp = n_chirp * VELOCITY_FFT_INTERP
        self.freq_bins = np.fft.fftfreq(chirp_len, 1/SAMPLE_RATE)
        self.window_time = np.hamming(chirp_len)[:, np.newaxis]
        self.window_chirp = np.hamming(n_chirp)[np.newaxis, :]
        self._fft_initialized = True

    async def __aenter__(self):
        await asyncio.to_thread(self.daq.connect)
        self._init_fft_windows(int(CHIRP_DURATION * SAMPLE_RATE), N_CHIRP)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await asyncio.to_thread(self.cleanup)

    def cleanup(self):
        try:
            if self.status == 1:
                self.daq.scan_stop()
            self.daq.disconnect()
            self.daq.release()
            self.gen.off()
            self.gen.close()
        except Exception as e:
            print("Cleanup error:", e)

    async def get_data_loop(self):
        try:
            while not self.stop_event.is_set():
                self.rate = self.daq.a_in_scan()

                status = self.daq.get_scan_status()
                while status != 1:
                    status = self.daq.get_scan_status()
                    await asyncio.sleep(0.001)

                if self.gen is not None:
                    self.gen.connect()  # Ensure generator is connected
                    self.gen.fire()     # Fire after a_in_scan
                    self.gen.close()    # Close generator connection
                
                status = self.daq.get_scan_status()
                while status != 0 and not self.stop_event.is_set():
                    status = self.daq.get_scan_status()
                    await asyncio.sleep(0.001)
                self.status = status

                arr = self.daq.get_data_array()
                
                chirp_len = int(CHIRP_DURATION * self.rate)
                if (
                    not self._fft_initialized
                    or chirp_len * RANGE_FFT_INTERP != self.fft_size
                    or N_CHIRP * VELOCITY_FFT_INTERP != self.n_chirp
                ):
                    self._init_fft_windows(chirp_len, N_CHIRP)
                try:
                    arr = arr.reshape(N_CHIRP, chirp_len).T
                except Exception as e:
                    print(
                        f"Reshape failed: {e} arr.shape={arr.shape}, expected ({N_CHIRP}, {chirp_len})"
                    )
                    arr = np.zeros((chirp_len, N_CHIRP))

                voltages = arr

                Vp = np.fft.fft(voltages, axis=0)
                for i in range(voltages.shape[1]):
                    Vp[:, i] *= np.exp(-1j * self.freq_bins * 2 * np.pi * DELAY * i)
                voltages_corr = np.real(np.fft.ifft(Vp, axis=0))

                windowed = (
                    voltages_corr[:chirp_len, :] * self.window_time
                )
                V = np.fft.rfft(windowed, axis=0, n=self.fft_size)
                VV = np.fft.fft(V * self.window_chirp, axis=1, n=self.n_chirp)
                VV = np.fft.fftshift(VV, axes=1)
                data = np.abs(VV)
                data = data - np.min(data)
                data = data / np.max(data)
                # data[data < 2e-2] = 2e-2
                self.data = data
                temp = (
                    np.real(
                        np.fft.irfft(
                            np.fft.rfft(voltages_corr[:, 1]),
                            int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP),
                        )
                    )
                    # / voltages_corr[:, 1].size
                    # * 2**14
                )
                temp = temp - np.sum(temp) / temp.size
                temp = temp / np.max(np.abs(temp))
                # print(temp.size)
                # temp = temp / np.max(temp)
                self.data_chirp = temp
                await asyncio.sleep(0.08)
        except Exception as e:
            # if self.gen is not None:
            #     self.gen.off()
            raise

    async def update_plot_loop(
        self,
        fig_plot,
        plot_widget,
        y_mask,
        x_mask,
        x_plot,
        y,
        fig2_plot,
        plot2_widget,
    ):
        while not self.stop_event.is_set():
            # try:
            #     print(self.data[y_mask, :][:, x_mask])
            # except Exception as e:
            #     print(f"Error accessing data: {e}")
            #     await asyncio.sleep(0.05)
            #     continue
            if self.update_in_progress:
                await asyncio.sleep(0.05)
                continue
            self.update_in_progress = True
            try:
                z_data = self.data[y_mask, :][:, x_mask]
                fig_plot.data[0].z = z_data
                fig2_plot.data[0].y = self.data_chirp
                plot_widget.update()
                plot2_widget.update()
            finally:
                self.update_in_progress = False
            await asyncio.sleep(0.1)


