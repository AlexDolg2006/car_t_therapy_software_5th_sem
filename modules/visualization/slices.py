import numpy as np
from matplotlib.figure import Figure
from .spatial import VARIABLES, TITLES

def _draw_slice(fig, df, day, axis, fixed_val):
    fig.clear()
    ax = fig.add_subplot(111)

    day_data = df[np.abs(df['time'] - day) < 0.01]
    if day_data.empty:
        ax.set_title("Нет данных")
        fig.canvas.draw_idle()
        return

    coord       = 'y' if axis == 'x' else 'x'
    fixed_coord = 'x' if axis == 'x' else 'y'

    available = np.sort(day_data[fixed_coord].unique())
    nearest = available[np.argmin(np.abs(available - fixed_val))]
    slice_data = day_data[day_data[fixed_coord] == nearest].sort_values(coord)

    line_styles = ['-', '--', '-.', ':', (0,(3,1,1,1)), (0,(5,2))]
    for var, ls, label in zip(VARIABLES, line_styles,
                              [TITLES[v] for v in VARIABLES]):
        ax.plot(slice_data[coord], slice_data[var],
                color='black', linewidth=1.5, linestyle=ls, label=label)

    ax.set_xlabel(coord); ax.set_ylabel('Концентрация')
    ax.set_title(f'Срез при {fixed_coord} = {nearest:.1f} — день {day:.1f}')
    ax.legend(fontsize=8)
    ax.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.5)
    fig.tight_layout()
    fig.canvas.draw_idle()

def draw_slice_x(fig: Figure, df, day: float, _var=None):
    y_mid = float(np.median(df['y'].unique()))
    _draw_slice(fig, df, day, 'x', y_mid)

def draw_slice_y(fig: Figure, df, day: float, _var=None):
    x_mid = float(np.median(df['x'].unique()))
    _draw_slice(fig, df, day, 'y', x_mid)