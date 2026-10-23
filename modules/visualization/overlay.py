import numpy as np
from matplotlib.figure import Figure
from .spatial import build_grid

def draw_overlay(fig: Figure, df, day: float, _var=None):
    fig.clear()
    ax = fig.add_subplot(111)

    day_data = df[np.abs(df['time'] - day) < 0.01]
    if day_data.empty:
        ax.set_title("Нет данных")
        fig.canvas.draw_idle()
        return

    X, Y, ZC = build_grid(day_data, 'C')
    _, _, ZT = build_grid(day_data, 'T')

    im1 = ax.contourf(X, Y, ZC, levels=40, cmap='Blues', alpha=0.6)
    im2 = ax.contourf(X, Y, ZT, levels=40, cmap='Reds',  alpha=0.6)

    fig.colorbar(im1, ax=ax, label='CAR-T', pad=0.10)
    fig.colorbar(im2, ax=ax, label='Опухоль', pad=0.02)

    ax.set_xlabel('x'); ax.set_ylabel('y')
    ax.set_title(f'CAR-T и опухоль — день {day:.1f}')
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.5)
    fig.tight_layout()
    fig.canvas.draw_idle()