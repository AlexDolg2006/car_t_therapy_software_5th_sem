from pathlib import Path
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_agg  import FigureCanvasAgg
import matplotlib.pyplot as plt

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox)
from PySide6.QtCore import Qt

# --- Настройка шрифта: Times New Roman (с засечками), увеличенный размер ---
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
plt.rcParams['font.size'] = 18
plt.rcParams['axes.titlesize'] = 20
plt.rcParams['axes.labelsize'] = 18
plt.rcParams['xtick.labelsize'] = 18
plt.rcParams['ytick.labelsize'] = 18
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['mathtext.fontset'] = 'stix'   # шрифт для LaTeX-формул (похож на Times)
# ---------------------------------------------------------------------------

FIELDS = {
    "C":   (r"CAR-T клетки $C$",                 "steelblue"),
    "T":   (r"Концентрация $T$ (кл / мм³)",      "firebrick"),
    "I":   (r"Иммуносупрессия $I$",              "darkorange"),
    "a_t": (r"Активация $a_t$",                  "purple"),
    "Ch":  (r"Хемокины $Ch$",                    "seagreen"),
    "Im":  (r"Иммуномодуляторы $Im$",            "goldenrod"),
    # если у вас в данных ключи "rt" и "Dt", оставляем их как ключи, а подпись — LaTeX
    "rt":  (r"Скорость роста $r_T$",             "crimson"),
    "r_T": (r"Скорость роста $r_T$",             "crimson"),
    "Dt":  (r"Коэффициент диффузии $D_T$",       "navy"),
    "D_T": (r"Коэффициент диффузии $D_T$",       "navy"),
}


def _latex_label(name: str) -> str:
    """
    Преобразует имя параметра в LaTeX-строку для подписи оси.
    """
    # 1) Явные соответствия для самых частых случаев
    mapping = {
        "rt":   r"$r_T ({сут}^{-1})$",
        "r_T":  r"$r_T ({сут}^{-1})$",
        "rT":   r"$r_T ({сут}^{-1})$",
        "dt":   r"$D_T (мм² / сут)$",
        "Dt":   r"$D_T (мм² / сут)$",
        "D_T":  r"$D_T (мм² / сут)$",
        "dT":   r"$D_T (мм² / сут)$",
        "a_t":  r"$a_t$",
        "Ch":   r"$Ch$",
        "Im":   r"$Im$",
        "C":    r"$C$",
        "T":    r"$T$",
        "I":    r"$I$",
    }
    if name in mapping:
        return mapping[name]
    # 2) Общий случай: "some_T" -> "$\mathrm{some}_T$"
    if "_" in name:
        base, sub = name.split("_", 1)
        return rf"$\mathrm{{{base}}}_{{{sub}}}$"
    # 3) Фолбэк — как есть
    return name


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
        self.cb_field.setStyleSheet("font-size: 16px;")
        self.lbl_info = QLabel("данных нет")
        self.lbl_info.setStyleSheet("font-size: 16px;")
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
        param = _latex_label(self.summary["param"].iloc[0])
        x = self.summary["value"]
        for k, (title, color) in FIELDS.items():
            if k in self.summary.columns:
                ax.plot(x, self.summary[k], color=color,
                        linewidth=2.5, marker="o", markersize=6, label=title)
        ax.set_xlabel(param); ax.set_ylabel("Значение в точке (день)")
        ax.set_title(f"Зависимость от {param} — все поля")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.legend(fontsize=14, loc="best")
        ax.tick_params(axis='both', labelsize=18)
        fig.tight_layout(); fig.canvas.draw_idle()

    def _draw_one(self, key):
        fig = self.fig; fig.clear()
        ax = fig.add_subplot(111)
        if key not in self.summary.columns:
            ax.set_title("Нет данных"); fig.canvas.draw_idle(); return
        param = _latex_label(self.summary["param"].iloc[0])
        x = self.summary["value"]
        title, color = FIELDS[key]
        ax.plot(x, self.summary[key], color=color,
                linewidth=2.5, marker="o", markersize=7, label=title)
        ax.set_xlabel(param); ax.set_ylabel(title)
        ax.set_title(f"{title} — зависимость от {param}")
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.tick_params(axis='both', labelsize=18)
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
        param = _latex_label(self.summary["param"].iloc[0])

        # 1) все поля на одном графике
        fig = Figure(figsize=(11, 8)); FigureCanvasAgg(fig)
        ax = fig.add_subplot(111)
        for k, (title, color) in FIELDS.items():
            if k in self.summary.columns:
                ax.plot(self.summary["value"], self.summary[k],
                        color=color, lw=2.5, marker="o", ms=6, label=title)
        ax.set_xlabel(param); ax.set_ylabel("Значение в точке (день)")
        ax.set_title(f"Зависимость от {param} — все поля")
        ax.grid(True, ls="--", alpha=0.4)
        ax.legend(fontsize=14)
        ax.tick_params(axis='both', labelsize=18)
        fig.tight_layout()
        fig.savefig(out_dir / "all_fields.png", dpi=150)

        # 2) каждый столбец отдельно
        for k, (title, color) in FIELDS.items():
            if k not in self.summary.columns:
                continue
            fig = Figure(figsize=(9, 6)); FigureCanvasAgg(fig)
            ax = fig.add_subplot(111)
            ax.plot(self.summary["value"], self.summary[k],
                    color=color, lw=2.5, marker="o", ms=7, label=title)
            ax.set_xlabel(param); ax.set_ylabel(title)
            ax.set_title(f"{title} — зависимость от {param}")
            ax.grid(True, ls="--", alpha=0.4)
            ax.tick_params(axis='both', labelsize=18)
            fig.tight_layout()
            fig.savefig(out_dir / f"{k}.png", dpi=150)

        return out_dir