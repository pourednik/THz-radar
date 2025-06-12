import numpy as np
import plotly.graph_objs as go

from config import current_config


def create_axes_and_masks(config):
    """Dynamically create axes and masks based on the given configuration."""
    x = np.fft.fftshift(np.fft.fftfreq(config.N_CHIRP * config.VELOCITY_FFT_INTERP, config.CHIRP_DURATION))
    x *= config.C / (2 * config.F0)
    y_full = np.fft.rfftfreq(
        int(config.SAMPLE_RATE * config.CHIRP_DURATION * config.RANGE_FFT_INTERP), 1 / config.SAMPLE_RATE
    )
    y_full *= config.C / (2 * config.BANDWIDTH) * config.CHIRP_REAL_DURATION

    y_mask = (y_full >= config.Y_RANGE_MIN) & (y_full <= config.Y_RANGE_MAX)
    x_limit = min(abs(x[0]), abs(x[-1]), abs(config.X_RANGE_MIN), abs(config.X_RANGE_MAX))
    x_mask = (x >= -x_limit) & (x <= x_limit)
    return x, y_full, y_mask, y_full[y_mask], x_limit, x_mask, x[x_mask]


def create_initial_Z(y, x_plot):
    """Create initial Z data for the plot dynamically."""
    return np.random.normal(loc=0, scale=1, size=(len(y), len(x_plot)))


def create_main_plot(x_plot, y, initial_Z):
    """Create the main plot dynamically."""
    return go.Figure(
        data=[
            go.Heatmap(
                z=initial_Z,
                x=x_plot,
                y=y,
                colorscale="Viridis",
                showscale=False,
            )
        ]
    )


def add_grid_lines(fig_plot, x_limit, config):
    """Add grid lines dynamically based on the given configuration."""
    for xv in np.arange(-0.4, 0.6, 0.1):
        fig_plot.add_shape(type="line", x0=xv, x1=xv, y0=config.Y_RANGE_MIN, y1=config.Y_RANGE_MAX, line=dict(color="grey", width=1), layer="above")
    for yv in np.arange(config.Y_RANGE_MIN, config.Y_RANGE_MAX, 0.2):
        fig_plot.add_shape(type="line", x0=-x_limit, x1=x_limit, y0=yv, y1=yv, line=dict(color="gray", width=1), layer="above")


def style_main_plot(fig_plot, x_limit, y, config):
    """Style the main plot dynamically."""
    fig_plot.update_layout(
        hovermode=False,
        xaxis=dict(range=[-x_limit, x_limit], title=dict(text="Geschwindigkeit (m/s)", font=dict(size=30)), tickfont=dict(size=30), showgrid=True),
        yaxis=dict(range=[config.Y_RANGE_MIN, config.Y_RANGE_MAX], title=dict(text="Distanz (m)", font=dict(size=30)), tickfont=dict(size=30), tickmode="linear", tick0=1, dtick=0.4),
        width=config.PLOT_WIDTH,
        height=config.PLOT_HEIGHT,
        margin=dict(l=40, r=40, t=50, b=40),
    )


def create_chirp_plot(config):
    """Create the chirp plot dynamically based on the given configuration."""
    x = np.arange(int(config.SAMPLES_PER_CH / config.N_CHIRP * config.CHIRP_FFT_INTERP)) / (config.SAMPLE_RATE * config.CHIRP_FFT_INTERP)
    y = np.random.randn(len(x))
    fig_plot_chirp = go.Figure(data=[go.Scatter(x=x, y=y, mode="lines", name="lines")])
    fig_plot_chirp.update_layout(
        hovermode=False,
        width=config.PLOT_WIDTH,
        height=config.PLOT_HEIGHT,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
            range=[0, config.CHIRP_DURATION],  # Dynamically set x-axis range based on chirp duration
            title=dict(text="Zeit (s)", font=dict(size=30)),
            tickfont=dict(size=30),
            showgrid=True,
        ),
        yaxis=dict(
            range=[-1.1, 1.1],
            title=dict(text="Amplitude (V)", font=dict(size=30)),
            tickfont=dict(size=30),
            tickmode="linear",
            tick0=1,
            dtick=0.4,
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis_showgrid=True,
        xaxis_gridcolor="lightgrey",
        xaxis_zeroline=False,
        yaxis_showgrid=True,
        yaxis_gridcolor="lightgrey",
        yaxis_zeroline=False,
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
    return fig_plot_chirp
