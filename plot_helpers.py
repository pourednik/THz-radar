import numpy as np
import plotly.graph_objs as go

from config import (
    N_CHIRP, VELOCITY_FFT_INTERP, CHIRP_DURATION, C, F0, SAMPLE_RATE,
    RANGE_FFT_INTERP, BANDWIDTH, CHIRP_REAL_DURATION, Y_RANGE_MIN, Y_RANGE_MAX,
    X_RANGE_MIN, X_RANGE_MAX, PLOT_WIDTH, PLOT_HEIGHT, SAMPLES_PER_CH, CHIRP_FFT_INTERP
)

def create_axes_and_masks():
    # ...existing code from main.py...
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
    return x, y_full, y_mask, y, x_limit, x_mask, x_plot

def create_initial_Z(y, x_plot):
    # ...existing code from main.py...
    return np.random.normal(loc=0, scale=1, size=(len(y), len(x_plot)))

def create_main_plot(x_plot, y, initial_Z):
    fig_plot = go.Figure(
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
    return fig_plot

def add_grid_lines(fig_plot, x_limit):
    # ...existing code from main.py...
    for xv in np.arange(-0.4, 0.6, 0.1):
        fig_plot.add_shape(
            type="line",
            x0=xv,
            x1=xv,
            y0=1,
            y1=3,
            line=dict(color="grey", width=1),
            layer="above",
        )
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

def style_main_plot(fig_plot, x_limit, y):
    # ...existing code from main.py...
    fig_plot.update_layout(
        hovermode=False,
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
            tick0=1,
            dtick=0.4,
        ),
        width=PLOT_WIDTH,
        height=PLOT_HEIGHT,
        margin=dict(l=40, r=40, t=50, b=40),
    )

def create_chirp_plot():
    # ...existing code from main.py...
    fig_plot_chirp = go.Figure(
        data=[
            go.Scatter(
                x=np.arange(int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP))
                / (SAMPLE_RATE * CHIRP_FFT_INTERP),
                y=np.random.randn(int(SAMPLES_PER_CH / N_CHIRP * CHIRP_FFT_INTERP)),
                mode="lines",
                name="lines",
            )
        ]
    )
    fig_plot_chirp.update_layout(
        hovermode=False,
        width=900,
        height=900,
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(
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
