from nicegui import ui
import numpy as np
import plotly.graph_objs as go
import asyncio
import datetime

from config import Config1, Config2, Config3, Config4, Config5, Config6
from experiment_manager import ExperimentManager
from gen import GenInstrument

# ----------- DAQ Driver Selection -----------
def get_daq(config):
    if config.USE_DUMMY:
        from daq.dummy import DummyDAQ
        return DummyDAQ(
            config.SAMPLES_PER_CH,
            config.N_CHIRP,
            config.CHIRP_DURATION,
            config.SAMPLE_RATE,
        )
    elif config.USE_WINDOWS:
        from daq.mcculw_driver import MCCULWDAQ
        return MCCULWDAQ(
            config.SAMPLES_PER_CH,
            config.N_CHIRP,
            config.CHIRP_DURATION,
            config.SAMPLE_RATE,
        )
    else:
        from daq.real import RealDAQ
        return RealDAQ(
            config.SAMPLES_PER_CH,
            config.N_CHIRP,
            config.CHIRP_DURATION,
            config.SAMPLE_RATE,
        )


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


async def update_config(selected_config):
    """Update the configuration dynamically."""
    if selected_config == "Config1":
        return Config1
    elif selected_config == "Config2":
        return Config2
    elif selected_config == "Config3":
        return Config3
    elif selected_config == "Config4":
        return Config4
    elif selected_config == "Config5":
        return Config5
    elif selected_config == "Config6":
        return Config6


@ui.page("/")
async def main():
    print(f"[{datetime.datetime.now().isoformat()}] Page accessed or refreshed!")

    # Initialize configuration
    current_config = Config1

    # 1. Calculate axes and masks
    x, y_full, y_mask, y, x_limit, x_mask, x_plot = create_axes_and_masks(current_config)

    # 2. Create initial Z data for plot
    initial_Z = create_initial_Z(y, x_plot)

    # 3. Create main plot (always Heatmap)
    fig_plot = create_main_plot(x_plot, y, initial_Z)  # Pass False for ScatterGL

    # 4. Add grid lines and style plot
    add_grid_lines(fig_plot, x_limit, current_config)
    style_main_plot(fig_plot, x_limit, y, current_config)

    # 5. Create chirp plot
    fig_plot_chirp = create_chirp_plot(current_config)

    # # 6. Layout UI
    # async def on_config_change(event):
    #     """Handle configuration change dynamically."""
    #     nonlocal current_config
    #     current_config = await update_config(event.value)
        
    #     # Recreate axes and masks based on the updated configuration
    #     x, y_full, y_mask, y, x_limit, x_mask, x_plot = create_axes_and_masks(current_config)
        
    #     # Recreate main plot
    #     initial_Z = create_initial_Z(y, x_plot)
    #     fig_plot = create_main_plot(x_plot, y, initial_Z)
    #     add_grid_lines(fig_plot, x_limit, current_config)
    #     style_main_plot(fig_plot, x_limit, y, current_config)
    #     plot_widget.figure = fig_plot  # Update the figure property directly
        
    #     # Recreate chirp plot
    #     fig_plot_chirp = create_chirp_plot(current_config)
    #     plot_widget2.figure = fig_plot_chirp  # Update the chirp plot widget

    with ui.row():
        ui.label("Select Configuration:")
        config_dropdown = ui.select(
            # options=["Config1", "Config2", "Config3", "Config4", "Config5"],
            options=["Config1", "Config4", "Config5", "Config6"],
            value="Config1",
            # on_change=on_config_change,
        )

    with ui.row():
        plot_widget = ui.plotly(fig_plot)
        plot_widget2 = ui.plotly(fig_plot_chirp)

    # --- Initialize generator after figures ---
    gen = GenInstrument()
    chirp_t = current_config.CHIRP_DURATION
    BW = current_config.GEN_BW
    gen.init(chirp_t, BW)

    daq_ctx = {"daq": None, "data_task": None, "plot_task": None}
    running = {"flag": False}

    async def start_tasks():
        if running["flag"]:
            return
        running["flag"] = True

        selected_config = config_dropdown.value
        current_config = await update_config(selected_config)
        
        x, y_full, y_mask, y, x_limit, x_mask, x_plot = create_axes_and_masks(current_config)
        # Recreate main plot
        initial_Z = create_initial_Z(y, x_plot)
        fig_plot = create_main_plot(x_plot, y, initial_Z)
        add_grid_lines(fig_plot, x_limit, current_config)
        style_main_plot(fig_plot, x_limit, y, current_config)
        plot_widget.figure = fig_plot  # Update the figure property directly
        
        # Recreate chirp plot
        fig_plot_chirp = create_chirp_plot(current_config)
        plot_widget2.figure = fig_plot_chirp  # Update the chirp plot widget
    
        gen = GenInstrument()
        chirp_t = current_config.CHIRP_DURATION
        BW = current_config.GEN_BW
        gen.init(chirp_t, BW)

        gen.on()

        daq_ctx["daq"] = ExperimentManager(get_daq(current_config), gen, current_config)
        await daq_ctx["daq"].__aenter__()
        daq_ctx["daq"].stop_event.clear()

        daq_ctx["data_task"] = asyncio.create_task(daq_ctx["daq"].data_handling_loop())
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
        if not running["flag"]:
            return
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

