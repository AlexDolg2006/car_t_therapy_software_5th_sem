from pathlib import Path
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg  import FigureCanvasAgg

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox)
from PySide6.QtCore import Qt


FIELDS = {
    "C":   ("CAR-T клетки C",       "steelblue"),
    "T":   ("Опухоль T",            "firebrick"),
    "I":   ("Иммуносупрессия I",    "darkorange"),
    "a_t": ("Активация a_t",        "purple"),
    "Ch":  ("Хемокины Ch",          "seagreen"),
    "Im":  ("Иммуномодуляторы Im",  "goldenrod"),
}


class ParametricView(QWidget):
    def __init__(self):
        super().__init__()
        self.summary: pd.DataFrame | None = None

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.cb_field = QComboBox()
        self.cb_field.addItem("Все", userData="__all__")
        for key, (title, _) in FIELDS.items():
            self.cb_field.addItem(title, userData=key)
        self.cb_field.currentIndexChanged.connect(self._redraw)
        self.lbl_info = QLabel("данных нет")
        top.addWidget(QLabel("Поле:"))
        top.addWidget(self.cb_field)
        top.addStretch()
        top.addWidget(self.lbl_info)
        layout.addLayout(top)

        self.fig = Figure(figsize=(9, 7))
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, stretch=1)
        self._draw_empty()

    def load_sweep(self, exp_dir: str, summary: pd.DataFrame):
        self.summary = summary
        if summary is not None and not summary.empty:
            param = summary["param"].iloc[0]
            xp = summary["x_point"].iloc[0] if "x_point" in summary.columns else "?"
            yp = summary["y_point"].iloc[0] if "y_point" in summary.columns else "?"
            day = summary["day_used"].iloc[0] if "day_used" in summary.columns else "?"
            self.lbl_info.setText(
                f"параметр: {param}, точка: ({xp:.1f}, {yp:.1f}), день: {day:.1f}"
            )
        else:
            self.lbl_info.setText("данных нет")
        self._redraw()

    def _redraw(self):
        if self.summary is None or self.summary.empty:
            self._draw_empty(); return
        key = self.cb_field.currentData()
        if key == "__all__":
            self._draw_all()
        else:
            self._draw_one(key)

    def _draw_all(self):
        fig = self.fig; fig.clear()
        ax = fig.add_subplot(111)
        param = self.summary["param"].iloc[0]
        x = self.summary["value"]
        for k, (title, color) in FIELDS.items():
            if k in self.summary.columns:
                ax.plot(x, self.summary[k], color=color,
                        linewidth=2, marker="o", markersize=4, label=title)
        ax.set_xlabel(param); ax.set_ylabel("Значение в точке (день)")
        ax.set_title(f"Зависимость от {param} — все поля")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(fontsize=9, loc="best")
        fig.tight_layout(); fig.canvas.draw_idle()

    def _draw_one(self, key):
        fig = self.fig; fig.clear()
        ax = fig.add_subplot(111)
        if key not in self.summary.columns:
            ax.set_title("Нет данных"); fig.canvas.draw_idle(); return
        param = self.summary["param"].iloc[0]
        x = self.summary["value"]
        title, color = FIELDS[key]
        ax.plot(x, self.summary[key], color=color,
                linewidth=2, marker="o", markersize=5, label=title)
        ax.set_xlabel(param); ax.set_ylabel(title)
        ax.set_title(f"{title} — зависимость от {param}")
        ax.grid(True, linestyle="--", alpha=0.4)
        fig.tight_layout(); fig.canvas.draw_idle()

    def _draw_empty(self):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_title("Запустите параметрический анализ слева")
        ax.grid(True, linestyle="--", alpha=0.3)
        self.fig.tight_layout(); self.fig.canvas.draw_idle()

    # ── ★ Сохранение PNG ───────────────────────────────────
    def save_pngs(self, out_dir: str | Path) -> Path:
        if self.summary is None or self.summary.empty:
            raise RuntimeError("Нет данных для сохранения")
        out_dir = Path(out_dir) / "plots"
        out_dir.mkdir(parents=True, exist_ok=True)
        param = self.summary["param"].iloc[0]

        # 1) все поля на одном графике
        fig = Figure(figsize=(9, 7)); FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        for k, (title, color) in FIELDS.items():
            if k in self.summary.columns:
                ax.plot(self.summary["value"], self.summary[k],
                        color=color, lw=2, marker="o", ms=4, label=title)
        ax.set_xlabel(param); ax.set_ylabel("Значение в точке (день)")
        ax.set_title(f"Зависимость от {param} — все поля")
        ax.grid(True, ls="--", alpha=0.4); ax.legend(fontsize=9)
        fig.tight_layout()
        fig.savefig(out_dir / "all_fields.png", dpi=150)

        # 2) каждый столбец отдельно
        for k, (title, color) in FIELDS.items():
            if k not in self.summary.columns:
                continue
            fig = Figure(figsize=(8, 5)); FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)
            ax.plot(self.summary["value"], self.summary[k],
                    color=color, lw=2, marker="o", ms=5, label=title)
            ax.set_xlabel(param); ax.set_ylabel(title)
            ax.set_title(f"{title} — зависимость от {param}")
            ax.grid(True, ls="--", alpha=0.4)
            fig.tight_layout()
            fig.savefig(out_dir / f"{k}.png", dpi=150)

        return out_dir