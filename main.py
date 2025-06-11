from nicegui import ui
import numpy as np
import plotly.graph_objs as go
import asyncio
import platform
import datetime
import json
import signal
import atexit

from config import (
    SAMPLES_PER_CH,
    N_CHIRP,
    SAMPLE_RATE,
    CHIRP_DURATION,
    RANGE_FFT_INTERP,
    VELOCITY_FFT_INTERP,
    DELAY,
    CHIRP_FFT_INTERP,
    BANDWIDTH,
    CHIRP_REAL_DURATION,
    C,
    USE_DUMMY,
    USE_WINDOWS,
)

from experiment_manager import ExperimentManager
from gen import GenInstrument

# ----------- DAQ Driver Selection -----------
if USE_DUMMY:
    from daq.dummy import DummyDAQ
elif USE_WINDOWS:
    from daq.mcculw_driver import MCCULWDAQ
else:
    from daq.real import RealDAQ

def get_daq():
    if USE_DUMMY:
        return DummyDAQ(SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE)
    elif USE_WINDOWS:
        return MCCULWDAQ(SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE)
    else:
        return RealDAQ(SAMPLES_PER_CH, N_CHIRP, CHIRP_DURATION, SAMPLE_RATE)


# --- Import helper modules ---
from plot_helpers import (
    create_axes_and_masks,
    create_initial_Z,
    create_main_plot,
    add_grid_lines,
    style_main_plot,
    create_chirp_plot,
)

# --- Main page handler (now mostly pseudo code) ---

@ui.page("/")
async def main():
    print(f"[{datetime.datetime.now().isoformat()}] Page accessed or refreshed!")

    # 1. Calculate axes and masks
    x, y_full, y_mask, y, x_limit, x_mask, x_plot = create_axes_and_masks()

    # 2. Create initial Z data for plot
    initial_Z = create_initial_Z(y, x_plot)

    # 3. Create main plot (always Heatmap)
    fig_plot = create_main_plot(x_plot, y, initial_Z)  # Pass False for ScatterGL

    # 4. Add grid lines and style plot
    add_grid_lines(fig_plot, x_limit)
    style_main_plot(fig_plot, x_limit, y)

    # 5. Create chirp plot
    fig_plot_chirp = create_chirp_plot()

    # 6. Layout UI
    with ui.row():
        plot_widget = ui.plotly(fig_plot)
        plot_widget2 = ui.plotly(fig_plot_chirp)

    # --- Initialize generator after figures ---
    gen = GenInstrument()
    chirp_t = 0.6e-3  # Set this appropriately
    chirp_t = 0.2e-3  # Set this appropriately
    BW = 140e6       # Set this appropriately

    gen.init(chirp_t, BW)

    daq_ctx = {"daq": None, "data_task": None, "plot_task": None}
    running = {"flag": False}

    async def start_tasks():
        if running["flag"]:
            return
        running["flag"] = True
        gen.on()  # Turn on generator before DAQ starts

        # Pass gen to ExperimentManager
        daq_ctx["daq"] = ExperimentManager(get_daq(), gen)
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
            )
        )

    async def stop_tasks():
        running["flag"] = False
        try:
            if daq_ctx["daq"]:
                daq_ctx["daq"].stop_event.set()
                if daq_ctx["data_task"]:
                    daq_ctx["data_task"].cancel()
                if daq_ctx["plot_task"]:
                    daq_ctx["plot_task"].cancel()
                await daq_ctx["daq"].__aexit__(None, None, None)
                daq_ctx["daq"] = None
                daq_ctx["data_task"] = None
                daq_ctx["plot_task"] = None
        finally:
            try:
                gen.off()
                gen.close()
            except Exception:
                pass

    async def toggle():
        if not running["flag"]:
            await start_tasks()
            toggle_button.text = "⏸ Stop"
        else:
            await stop_tasks()
            toggle_button.text = "▶ Start"
            try:
                gen.off()
                gen.close()
            except Exception:
                pass

    toggle_button = ui.button("▶ Start", on_click=toggle)


    # # 9. Show info labels
    # ui.label(
    #     f"RANGE_FFT_INTERP: {config.RANGE_FFT_INTERP}, VELOCITY_FFT_INTERP: {config.VELOCITY_FFT_INTERP}"
    # )

ui.run(title="RADAR", favicon="📡")