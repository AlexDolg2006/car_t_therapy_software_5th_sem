import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from PySide6.QtWidgets import QWidget, QVBoxLayout


class OptimizationChart(QWidget):
    """График «Модель vs эксперимент» для вкладки обучения."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas)

        self.ax = self.fig.add_subplot(111)
        self._init_plot()

    def _init_plot(self):
        self.ax.clear()
        self.ax.set_xlabel("t, сут")
        self.ax.set_ylabel("V, мм³")
        self.ax.grid(True, linestyle=":", alpha=0.6)
        self.ax.set_title("Модель vs эксперимент")
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def draw(self, exp_df=None, traj_df=None):
        """exp_df, traj_df — pandas.DataFrame с колонками day, volume."""
        self.ax.clear()
        self.ax.set_xlabel("t, сут")
        self.ax.set_ylabel("V, мм³")
        self.ax.grid(True, linestyle=":", alpha=0.6)

        has_data = False

        # ── Точки эксперимента ──────────────────────────────
        if exp_df is not None and not exp_df.empty:
            self.ax.scatter(exp_df["day"], exp_df["volume"],
                            color="red", edgecolor="black", s=60,
                            label="Эксперимент", zorder=3)
            has_data = True

        # ── Кривая модели ───────────────────────────────────
        if traj_df is not None and not traj_df.empty:
            self.ax.plot(traj_df["day"], traj_df["volume"],
                         color="black", linewidth=2.0,
                         label="Модель", zorder=1)
            has_data = True

        # ── Динамическая подстройка масштаба по данным ──────
        if has_data:
            # по X — границы эксперимента (и модели, если она выходит)
            xs = []
            ys = []
            if exp_df is not None and not exp_df.empty:
                xs.append(exp_df["day"].to_numpy())
                ys.append(exp_df["volume"].to_numpy())
            if traj_df is not None and not traj_df.empty:
                xs.append(traj_df["day"].to_numpy())
                ys.append(traj_df["volume"].to_numpy())

            x_all = np.concatenate(xs)
            y_all = np.concatenate(ys)

            x_min, x_max = float(np.min(x_all)), float(np.max(x_all))
            y_min, y_max = float(np.min(y_all)), float(np.max(y_all))

            # X: только по эксперименту + 5% запас
            if exp_df is not None and not exp_df.empty:
                ex = exp_df["day"].to_numpy()
                x_min = float(np.min(ex))
                x_max = float(np.max(ex))
            x_pad = (x_max - x_min) * 0.05 if x_max > x_min else 1.0

            # Y: по эксперименту + 10% запас; модель может выйти выше
            if exp_df is not None and not exp_df.empty:
                ey = exp_df["volume"].to_numpy()
                y_max_exp = float(np.max(ey))
            else:
                y_max_exp = y_max

            # учитываем модель: если она выше — берём её
            y_max_final = max(y_max_exp, y_max)
            y_pad = (y_max_final - y_min) * 0.10 if y_max_final > y_min else 1.0

            self.ax.set_xlim(x_min - x_pad, x_max + x_pad)
            self.ax.set_ylim(max(0.0, y_min - y_pad), y_max_final + y_pad)

            self.ax.legend(frameon=True, edgecolor="black", loc="upper left")
        else:
            # пустой график
            self.ax.set_xlim(0, 10)
            self.ax.set_ylim(0, 10)

        self.ax.set_title("Модель vs эксперимент")
        self.fig.tight_layout()
        self.canvas.draw_idle()