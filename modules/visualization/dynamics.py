import numpy as np
import pandas as pd
from matplotlib.figure import Figure

def compute_dynamics(df):
    results = []
    for t, grp in df.groupby("time"):
        xs = np.sort(grp["x"].unique())
        ys = np.sort(grp["y"].unique())
        dx = np.diff(xs).mean() if len(xs) > 1 else 1.0
        dy = np.diff(ys).mean() if len(ys) > 1 else 1.0
        cell = dx * dy
        results.append({
            "day":         t,
            "tumor_volume": grp["T"].sum() * cell,
            "T_max":       grp["T"].max(),
            "mean_C":      grp["C"].mean(),
            "mean_I":      grp["I"].mean(),
            "mean_aT":     grp["a_t"].mean(),
        })
    return pd.DataFrame(results).sort_values("day")

def draw_total_dynamics(fig: Figure, df, _day=None, _var=None):
    fig.clear()
    ax = fig.add_subplot(111)
    res = compute_dynamics(df)
    ax.plot(res["day"], res["tumor_volume"], color="black", linewidth=1.8)
    ax.fill_between(res["day"], res["tumor_volume"],
                    facecolor="none", edgecolor="black",
                    hatch="///", linewidth=0.0)
    ax.set_xlabel("День")
    ax.set_ylabel("Объём опухоли (мм²)")
    ax.set_title("Объём опухоли")
    ax.grid(True, linestyle="--", linewidth=0.5, color="gray", alpha=0.7)
    ax.set_xlim(left=0); ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.canvas.draw_idle()

def draw_center_dynamics(fig: Figure, df, _day=None, var='T'):
    fig.clear()
    ax = fig.add_subplot(111)
    x_mid = df["x"].median()
    y_mid = df["y"].median()
    sub = df[(np.abs(df["x"] - x_mid) < 1.0) &
             (np.abs(df["y"] - y_mid) < 1.0)]
    if sub.empty: sub = df
    s = sub.groupby("time")[var].mean()
    ax.plot(s.index, s.values, color="crimson", linewidth=2)
    ax.set_xlabel("День"); ax.set_ylabel(var)
    ax.set_title(f"{var} в центре")
    ax.grid(True, linestyle="--", linewidth=0.5, color="gray", alpha=0.7)
    fig.tight_layout()
    fig.canvas.draw_idle()