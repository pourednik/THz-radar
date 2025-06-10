from nicegui import ui
import numpy as np
import plotly.graph_objs as go
import asyncio
import platform
import datetime
import json

import config

from daq_manager import DAQManager

# ----------- DAQ Driver Selection -----------
if config.USE_DUMMY:
    from daq.dummy import DummyDAQ
elif config.USE_WINDOWS:
    from daq.mcculw_driver import MCCULWDAQ
else:
    from daq.real import RealDAQ

def get_daq():
    if config.USE_DUMMY:
        return DummyDAQ(config.SAMPLES_PER_CH, config.N_CHIRP, config.CHIRP_DURATION, config.SAMPLE_RATE)
    elif config.USE_WINDOWS:
        return MCCULWDAQ(config.SAMPLES_PER_CH, config.N_CHIRP, config.CHIRP_DURATION, config.SAMPLE_RATE)
    else:
        return RealDAQ(config.SAMPLES_PER_CH, config.N_CHIRP, config.CHIRP_DURATION, config.SAMPLE_RATE)


# --- Import helper modules ---
from plot_helpers import (
    create_axes_and_masks,
    create_initial_Z,
    create_main_plot,
    add_grid_lines,
    style_main_plot,
    create_chirp_plot,
)
from task_helpers import setup_tasks

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

    # 7. Setup DAQ and plotting tasks
    daq_ctx = {"daq": None, "data_task": None, "plot_task": None}
    start_tasks, stop_tasks = setup_tasks(
        daq_ctx, fig_plot, plot_widget, y_mask, x_mask, x_plot, y, fig_plot_chirp, plot_widget2
    )

    # 8. Start/stop button logic
    running = {"flag": False}
    async def toggle():
        running["flag"] = not running["flag"]
        toggle_button.text = "⏸ Stop" if running["flag"] else "▶ Start"
        if running["flag"]:
            await start_tasks()
        else:
            await stop_tasks()
    toggle_button = ui.button("▶ Start", on_click=toggle)

    # # 9. Show info labels
    # ui.label(
    #     f"RANGE_FFT_INTERP: {config.RANGE_FFT_INTERP}, VELOCITY_FFT_INTERP: {config.VELOCITY_FFT_INTERP}"
    # )

ui.run(title="RADAR", favicon="📡")