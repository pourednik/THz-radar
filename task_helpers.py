import asyncio

def setup_tasks(daq_ctx, fig_plot, plot_widget, y_mask, x_mask, x_plot, y, fig_plot_chirp, plot_widget2):
    async def start_tasks():
        from daq_manager import DAQManager
        from main import get_daq
        if daq_ctx["data_task"] is not None:
            return
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
    return start_tasks, stop_tasks
