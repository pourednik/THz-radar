import numpy as np
import asyncio
import matplotlib.pyplot as plt
import time  # Import the time module


class ExperimentManager:
    def __init__(self, daq, gen, config):
        self.daq = daq
        self.gen = gen  # Optional generator instrument
        self.config = config
        self.data = None
        self.data_chirp = None
        self.stop_event = asyncio.Event()
        self.status = 0
        self._fft_initialized = False
        self.update_in_progress = False
        self.update_data_shape()

    def update_data_shape(self):
        """Update data_shape based on the given configuration."""
        self.data_shape = (
            int(self.config.SAMPLES_PER_CH / self.config.N_CHIRP / 2 * self.config.RANGE_FFT_INTERP + 1),
            self.config.N_CHIRP * self.config.VELOCITY_FFT_INTERP,
        )
        self.data = np.zeros(self.data_shape)
        self.data_chirp = np.zeros(int(self.config.SAMPLES_PER_CH / self.config.N_CHIRP))
        chirp_len = int(self.config.CHIRP_DURATION * self.config.SAMPLE_RATE)
        self._init_fft_windows(chirp_len, self.config.N_CHIRP)  # Reinitialize FFT windows

    def reinitialize_daq(self):
        """Reinitialize the DAQ object based on the updated configuration."""
        if self.config.USE_DUMMY:
            from daq.dummy import DummyDAQ
            self.daq = DummyDAQ(
                self.config.SAMPLES_PER_CH,
                self.config.N_CHIRP,
                self.config.CHIRP_DURATION,
                self.config.SAMPLE_RATE,
            )
        elif self.config.USE_WINDOWS:
            from daq.mcculw_driver import MCCULWDAQ
            self.daq = MCCULWDAQ(
                self.config.SAMPLES_PER_CH,
                self.config.N_CHIRP,
                self.config.CHIRP_DURATION,
                self.config.SAMPLE_RATE,
            )
        else:
            from daq.real import RealDAQ
            self.daq = RealDAQ(
                self.config.SAMPLES_PER_CH,
                self.config.N_CHIRP,
                self.config.CHIRP_DURATION,
                self.config.SAMPLE_RATE,
            )

    def _init_fft_windows(self, chirp_len, n_chirp):
        """Initialize FFT windows dynamically based on the given configuration."""
        self.fft_size = chirp_len * self.config.RANGE_FFT_INTERP
        self.n_chirp = n_chirp * self.config.VELOCITY_FFT_INTERP
        self.freq_bins = np.fft.fftfreq(chirp_len, 1 / self.config.SAMPLE_RATE)
        self.window_time = np.hamming(chirp_len)[:, np.newaxis]
        self.window_chirp = np.hamming(n_chirp)[np.newaxis, :]
        self._fft_initialized = True

    async def __aenter__(self):
        self.reinitialize_daq()  # Reinitialize DAQ with updated configuration
        await asyncio.to_thread(self.daq.connect)
        self.update_data_shape()  # Ensure data_shape is updated when entering
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

    async def collect_data(self):
        try:
            self.rate = self.daq.a_in_scan()

            
                
            status = self.daq.get_scan_status()
            while status != 1:
                status = self.daq.get_scan_status()
                await asyncio.sleep(0.001)
            
            # start_time = time.time()

            if self.gen is not None:
                self.gen.fire()
            
            # end_time = time.time()
            # print(f"Processing time: {end_time - start_time:.4f} seconds")


            status = self.daq.get_scan_status()
            while status != 0 and not self.stop_event.is_set():
                status = self.daq.get_scan_status()
                await asyncio.sleep(0.001)
            self.status = status

            return self.daq.get_data_array()
        except Exception as e:
            raise

    def process_data(self, arr, saved = 1):
        """Process data dynamically based on the given configuration."""
        chirp_len = int(self.config.CHIRP_DURATION * self.config.SAMPLE_RATE)
        if (
            not self._fft_initialized
            or chirp_len * self.config.RANGE_FFT_INTERP != self.fft_size
            or self.config.N_CHIRP * self.config.VELOCITY_FFT_INTERP != self.n_chirp
        ):
            self._init_fft_windows(chirp_len, self.config.N_CHIRP)
        try:
            arr = arr.reshape(self.config.N_CHIRP, chirp_len).T
        except Exception as e:
            print(
                f"Reshape failed: {e} arr.shape={arr.shape}, expected ({self.config.N_CHIRP}, {chirp_len})"
            )
            arr = np.zeros((chirp_len, self.config.N_CHIRP))

        voltages = arr

        Vp = np.fft.fft(voltages, axis=0)
        for i in range(voltages.shape[1]):
            Vp[:, i] *= np.exp(-1j * self.freq_bins * 2 * np.pi * self.config.DELAY * i)
        voltages_corr = np.real(np.fft.ifft(Vp, axis=0))
        if saved==0:
            np.save('ref.npy', voltages_corr[:,-1])

        if self.config.RESAMPLE:
            try:
                for i in range(self.config.N_CHIRP):
                    voltages_corr[:, i] = np.interp(
                        self.config.t3,
                        np.arange(voltages_corr[:, i].size) / self.config.SAMPLE_RATE,
                        voltages_corr[:, i],
                    )
            except Exception as e:
                print(f"Error accessing data: {e}")
                pass
        # fig, ax = plt.subplots()
        # ax.plot(voltages_corr)
        # plt.show()

        windowed = voltages_corr[:chirp_len, :] * self.window_time
        V = np.fft.rfft(windowed, axis=0, n=self.fft_size)
        VV = np.fft.fft(V * self.window_chirp, axis=1, n=self.n_chirp)
        VV = np.fft.fftshift(VV, axes=1)
        data = np.abs(VV)
        data = data - np.min(data)
        data = data / np.max(data)
        self.data = data

        # temp = (
        #     np.real(
        #         np.fft.irfft(
        #             np.fft.rfft(voltages_corr[:, 1]),
        #             int(self.config.SAMPLES_PER_CH / self.config.N_CHIRP * self.config.CHIRP_FFT_INTERP),
        #         )
        #     )
        # )
        temp = voltages_corr[:, 1]
        temp = temp - np.sum(temp) / temp.size
        temp = temp / np.max(np.abs(temp))
        # print(temp)
        self.data_chirp = temp

    async def send_data(self):
        # Placeholder for sending data logic
        await asyncio.sleep(0.01)

    async def data_handling_loop(self):
        saved = 0
        self.gen.connect()
        try:
            while not self.stop_event.is_set():
                # start_time = time.time()
                arr = await self.collect_data()
                # end_time = time.time()
                # print(f"Processing time: {end_time - start_time:.4f} seconds")
                self.process_data(arr, saved)
                saved = 1
                # await self.send_data()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.gen.close()
            raise
        finally:
            self.gen.close()
            print("Data handling loop exited.")

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
            #     await asyncio.sleep(0.1)
            #     continue
            if self.update_in_progress:
                await asyncio.sleep(0.05)
                continue
            self.update_in_progress = True
            try:
                z_data = self.data[y_mask, :][:, x_mask]
                # print(z_data)
                fig_plot.data[0].z = z_data
                fig2_plot.data[0].y = self.data_chirp
                plot_widget.update()
                plot2_widget.update()
            # except Exception as e:
            #     print(f"Error accessing data: {e}")
            #     await asyncio.sleep(0.1)
            #     continue
            finally:
                self.update_in_progress = False
            await asyncio.sleep(0.05)
