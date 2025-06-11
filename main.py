from nicegui import ui
import numpy as np
import plotly.graph_objs as go
import asyncio
import os
import datetime

from daq.dummy import DummyDAQ
from daq.real import RealDAQ

# ----------- Parameters (all numbers here for easy change) ----------
USE_DUMMY = False
SAMPLES_PER_CH = 6100
SAMPLE_RATE = 500_000
N_CHIRP = 20
CHIRP_DURATION = 0.61e-3
C = 3e8
F0 = 15e9 * 18
BANDWIDTH = 200e6 * 18
CHIRP_REAL_DURATION = 0.617016e-3
PLOT_WIDTH = 700
PLOT_HEIGHT = 700
UPDATE_INTERVAL = 0.1  # seconds, for 20Hz
DELAY = -0.0116
# DELAY = -0

# --- Set desired axis ranges here ---
X_RANGE_MIN = -0.5  # example values, set as needed
X_RANGE_MAX = 0.5
Y_RANGE_MIN = 1
Y_RANGE_MAX = 3

# --- Use ScatterGL accelerated plotting? ---
USE_SCATTERGL = (
    False  # Set to False for classic (SVG) contour, True for Scattergl (WebGL)
)

# --- Interpolation factors for FFTs ---
RANGE_FFT_INTERP = 2  # multiply number of FFT points for V (range)
VELOCITY_FFT_INTERP = 4  # multiply number of FFT points for VV (angle)

CHIRP_FFT_INTERP = 128


def get_daq():
    if USE_DUMMY:
        return DummyDAQ(SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE)
    else:
        return RealDAQ(SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE)


class DAQManager:
    def __init__(self, daq):
        self.daq = daq
        self.data_shape = (
            int(SAMPLES_PER_CH / N_CHIRP / 2 + 1) * RANGE_FFT_INTERP,
            N_CHIRP * VELOCITY_FFT_INTERP,
        )
        self.data = np.zeros(self.data_shape)
        self.data_chirp = np.zeros(int(SAMPLES_PER_CH / N_CHIRP))
        self.stop_event = asyncio.Event()
        self.rate = SAMPLE_RATE
        self.status = 0
        self._fft_initialized = False
        self.update_in_progress = False

    def _init_fft_windows(self, chirp_len, n_chirp):
        # Interpolated sizes
        self.fft_size = chirp_len * RANGE_FFT_INTERP
        self.n_chirp = n_chirp * VELOCITY_FFT_INTERP
        # self.freq_bins = np.fft.fftfreq(self.fft_size, 1 / self.fft_size)
        self.freq_bins = np.fft.fftfreq(chirp_len, 1 / chirp_len)
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
        except Exception as e:
            print("Cleanup error:", e)

    async def get_data_loop(self):
        while not self.stop_event.is_set():
            self.rate = self.daq.a_in_scan()
            status, _ = self.daq.get_scan_status()
            while status != 0 and not self.stop_event.is_set():
                status, _ = self.daq.get_scan_status()
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
            # voltages_corr = voltages
            windowed = (
                voltages_corr[:chirp_len, :] * self.window_time
            )  # use original window size
            # Now V: interpolated along range (axis=0)
            V = np.fft.rfft(windowed, axis=0, n=self.fft_size)
            # Interpolate along chirp (axis=1)
            VV = np.fft.fft(V * self.window_chirp, axis=1, n=self.n_chirp)
            VV = np.fft.fftshift(VV, axes=1)
            # Only keep real part for plotting
            data = np.abs(VV)
            data = data - np.min(data)
            data = data / np.max(data)
            data[data < 1e-2] = 1e-2
            # data = np.log10(data)
            # Update self.data to the new size
            self.data = data
            temp = (
                np.real(
                    np.fft.irfft(
                        np.fft.rfft(voltages_corr[:, 1]),
                        int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP),
                    )
                )
                / voltages_corr[:, 0].size
                * 2**14
            )
            temp = temp / np.max(temp)
            self.data_chirp = temp
            await asyncio.sleep(0.01)

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
        mode="scattergl",
    ):
        while not self.stop_event.is_set():
            if self.update_in_progress:
                await asyncio.sleep(UPDATE_INTERVAL)
                continue
            self.update_in_progress = True
            try:
                z_data = self.data[y_mask, :][:, x_mask]  # shape (len(y), len(x_plot))
                if mode == "scattergl":
                    x_points = np.tile(x_plot, len(y))
                    y_points = np.repeat(y, len(x_plot))
                    z_points = z_data.flatten()
                    fig_plot.data[0].x = x_points
                    fig_plot.data[0].y = y_points
                    fig_plot.data[0].marker.color = z_points
                    fig_plot.data[0].marker.cmin = np.min(z_points)
                    fig_plot.data[0].marker.cmax = np.max(z_points)
                else:
                    fig_plot.data[0].z = z_data
                    fig2_plot.data[0].y = self.data_chirp
                plot_widget.update()
                plot2_widget.update()
            except Exception as e:
                print(f"h: {e}")

            finally:
                self.update_in_progress = False
            await asyncio.sleep(UPDATE_INTERVAL)


@ui.page("/")
async def main():
    print(f"[{datetime.datetime.now().isoformat()}] Page accessed or refreshed!")
    # --- Axes and Masks ---
    x = np.fft.fftshift(np.fft.fftfreq(N_CHIRP * VELOCITY_FFT_INTERP, CHIRP_DURATION))
    x = C / 2 * 1 / F0 * x
    y_full = np.fft.rfftfreq(
        int(SAMPLE_RATE * CHIRP_DURATION * RANGE_FFT_INTERP), 1 / SAMPLE_RATE
    )
    y_full = C / 2 * y_full / BANDWIDTH * CHIRP_REAL_DURATION

    y_mask = (y_full >= Y_RANGE_MIN) & (y_full <= Y_RANGE_MAX)
    y = y_full[y_mask]
    x_limit = min(abs(x[0]), abs(x[-1]), abs(X_RANGE_MIN), abs(X_RANGE_MAX))
    x_mask = (x >= -x_limit) & (x <= x_limit)
    x_plot = x[x_mask]

    initial_Z = np.random.normal(loc=0, scale=1, size=(len(y), len(x_plot)))

    if USE_SCATTERGL:
        x_points = np.tile(x_plot, len(y))
        y_points = np.repeat(y, len(x_plot))
        z_points = initial_Z.flatten()
        fig_plot = go.Figure(
            data=[
                go.Scattergl(
                    x=x_points,
                    y=y_points,
                    mode="markers",
                    marker=dict(
                        color=z_points,
                        colorscale="Viridis",
                        colorbar=dict(title="Intensity"),
                        size=4,
                        showscale=False,
                        cmin=np.min(z_points),
                        cmax=np.max(z_points),
                    ),
                )
            ]
        )
    else:
        fig_plot = go.Figure(
            data=[
                go.Contour(
                    z=initial_Z,
                    x=x_plot,
                    y=y,
                    colorscale="Viridis",
                    contours=dict(coloring="fill"),
                    showscale=False,
                    line_smoothing=0.85,
                    ncontours=20,
                )
            ]
        )

    fig_plot.update_layout(
        xaxis=dict(
            range=[-x_limit, x_limit],
            title=dict(text="Geschwindigkeit (m/s)", font=dict(size=30)),
            tickfont=dict(size=30),
            showgrid=True,
        ),
        yaxis=dict(
            range=[Y_RANGE_MIN, Y_RANGE_MAX],
            title=dict(text="Distanz (m)", font=dict(size=30)),
            tickfont=dict(size=30),
            tickmode="linear",
            tick0=1,  # Start tick at 10
            dtick=0.4,  # Tick step size
        ),
        width=PLOT_WIDTH,
        height=PLOT_HEIGHT,
        margin=dict(l=40, r=40, t=50, b=40),
    )
    # Example: Draw vertical grid lines
    for xv in np.arange(-0.4, 0.6, 0.1):
        fig_plot.add_shape(
            type="line",
            x0=xv,
            x1=xv,
            y0=1,
            y1=3,
            line=dict(color="grey", width=1),
            layer="above",  # ensures it's over the plot
        )

    # Example: Draw horizontal grid lines
    for yv in np.arange(1, 3, 0.2):
        fig_plot.add_shape(
            type="line",
            x0=-0.5,
            x1=0.5,
            y0=yv,
            y1=yv,
            line=dict(color="gray", width=1),
            layer="above",
        )
    fig_plot_chirp = go.Figure(
        data=[
            go.Scatter(
                # x=np.arange(int(SAMPLES_PER_CH / N_CHIRP)) / SAMPLE_RATE,
                # y=np.random.randn(int(SAMPLES_PER_CH / N_CHIRP)),
                # x=np.arange(int(2**14)) / SAMPLE_RATE,
                x=np.arange(int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP))
                / (SAMPLE_RATE * CHIRP_FFT_INTERP),
                y=np.random.randn(int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP)),
                mode="lines",
                name="lines",
            )
        ]
    )
    fig_plot_chirp.update_layout(
        width=700,
        height=700,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            # range=[-1.1, 1.1],
            title=dict(text="Zeit (s)", font=dict(size=30)),
            tickfont=dict(size=30),
            showgrid=True,
        ),
        yaxis=dict(
            range=[-1.1, 1.1],
            title=dict(text="Amplitude (V)", font=dict(size=30)),
            tickfont=dict(size=30),
            tickmode="linear",
            tick0=1,  # Start tick at 10
            dtick=0.4,  # Tick step size
        ),
    )
    fig_plot_chirp.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="lightgrey", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="lightgrey", zeroline=False),
        shapes=[
            dict(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                y0=0,
                x1=1,
                y1=1,
                line=dict(color="black", width=1),
                fillcolor="rgba(0,0,0,0)",
            )
        ],
    )

    with ui.row():
        plot_widget = ui.plotly(fig_plot)
        plot_widget2 = ui.plotly(fig_plot_chirp)

    # --- Robust start/stop task management ---
    daq_ctx = {"daq": None, "data_task": None, "plot_task": None}

    async def start_tasks():
        if daq_ctx["data_task"] is not None:
            return  # Already running
        daq_ctx["daq"] = DAQManager(get_daq())
        await daq_ctx["daq"].__aenter__()
        daq_ctx["daq"].stop_event.clear()
        daq_ctx["data_task"] = asyncio.create_task(daq_ctx["daq"].get_data_loop())
        daq_ctx["plot_task"] = asyncio.create_task(
            daq_ctx["daq"].update_plot_loop(
                fig_plot,
                plot_widget,
                y_mask,
                x_mask,
                x_plot,
                y,
                fig_plot_chirp,
                plot_widget2,
                mode="scattergl" if USE_SCATTERGL else "contour",
            )
        )

    async def stop_tasks():
        if daq_ctx["daq"] is not None:
            daq_ctx["daq"].stop_event.set()
            if daq_ctx["data_task"]:
                daq_ctx["data_task"].cancel()
            if daq_ctx["plot_task"]:
                daq_ctx["plot_task"].cancel()
            await daq_ctx["daq"].__aexit__(None, None, None)
            daq_ctx["daq"] = None
            daq_ctx["data_task"] = None
            daq_ctx["plot_task"] = None

    running = {"flag": False}

    async def toggle():
        running["flag"] = not running["flag"]
        toggle_button.text = "⏸ Stop" if running["flag"] else "▶ Start"
        if running["flag"]:
            await start_tasks()
        else:
            await stop_tasks()

    toggle_button = ui.button("▶ Start", on_click=toggle)

    ui.label(f"ScatterGL Mode: {'ON' if USE_SCATTERGL else 'OFF'}")
    ui.label(
        f"RANGE_FFT_INTERP: {RANGE_FFT_INTERP}, VELOCITY_FFT_INTERP: {VELOCITY_FFT_INTERP}"
    )


ui.run(favicon="📡", title="RADAR")
