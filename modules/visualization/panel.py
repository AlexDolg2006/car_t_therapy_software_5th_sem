# modules/visualization/panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QLabel, QComboBox, QSlider,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, QThread
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import pandas as pd

from .spatial  import draw_spatial
from .slices   import draw_slice_x, draw_slice_y
from .overlay  import draw_overlay
from .dynamics import draw_total_dynamics, draw_center_dynamics
from .optimization_chart import OptimizationChart
from scipy.interpolate import UnivariateSpline

# ── Новая вкладка для сравнения ──────────────────────────────
class MultiMethodCompareChart(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.btn_run = QPushButton("Сравнить 3 метода (чистая модель)")
        self.btn_run.setMinimumHeight(30)
        
        top.addWidget(QLabel("Сравнение численных методов (без терапии)"))
        top.addStretch()
        top.addWidget(self.btn_run)
        layout.addLayout(top)

        self.fig = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar) 
        layout.addWidget(self.canvas)

        self._init_plot()

    def _init_plot(self, msg="Выберите CSV в 'Обучении' и нажмите кнопку"):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_xlabel("t, сут")
        ax.set_ylabel("Объем опухоли (мм³)")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.set_title(msg)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ★ НОВЫЙ МЕТОД: Расчет среднеквадратичной ошибки (RMSE)
    def _calc_rmse(self, exp_df, df_model):
        if exp_df is None or df_model is None or exp_df.empty or df_model.empty:
            return float('nan')
        
        # Считаем объем опухоли для модели
        xs = np.sort(df_model["x"].unique()); ys = np.sort(df_model["y"].unique())
        dx = np.diff(xs).mean() if len(xs) > 1 else 1.0
        dy = np.diff(ys).mean() if len(ys) > 1 else 1.0
        vol = df_model.groupby("time")["T"].sum() * (dx * dy)
        
        errors = []
        for _, row in exp_df.iterrows():
            t_exp = row["day"]
            v_exp = row["volume"]
            
            # Находим ближайший день в модели (интерполируем по времени)
            # Используем линейную интерполяцию для нахождения объема в момент t_exp
            v_model = np.interp(t_exp, vol.index, vol.values)
            
            errors.append((v_model - v_exp) ** 2)
            
        if not errors:
            return float('nan')
            
        return np.sqrt(np.mean(errors))

    def draw(self, exp_df=None, df_explicit=None, df_implicit=None, df_rk4=None):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_xlabel("t, сут")
        ax.set_ylabel("Объем опухоли (мм³)")
        ax.grid(True, linestyle=":", alpha=0.6)
        
        has_data = False

        # 1. Эксперимент + Аппроксимация
        if exp_df is not None and not exp_df.empty:
            ax.scatter(exp_df["day"], exp_df["volume"],
                       color="red", edgecolor="black", s=60, label="Эксперимент", zorder=5)
            
            try:
                x = exp_df["day"].values
                y = exp_df["volume"].values
                x_new = np.linspace(x.min(), x.max(), 300)
                s_val = len(x) * np.var(y) * 0.05 
                spl = UnivariateSpline(x, y, k=3, s=s_val)
                ax.plot(x_new, spl(x_new), color="red", linestyle="--", 
                        alpha=0.8, linewidth=2, label="Аппроксимация", zorder=4)
            except Exception as e:
                print(f"Ошибка аппроксимации: {e}")
            has_data = True

        # 2. Результаты 3 методов с расчетом ошибки
        methods = [
            (df_explicit, "Явный Эйлер", "blue"),
            (df_implicit, "Неявный Эйлер", "green"),
            (df_rk4,      "Рунге-Кутта 4", "purple")
        ]

        for df, label, color in methods:
            if df is not None and not df.empty:
                xs = np.sort(df["x"].unique()); ys = np.sort(df["y"].unique())
                dx = np.diff(xs).mean() if len(xs) > 1 else 1.0
                dy = np.diff(ys).mean() if len(ys) > 1 else 1.0
                vol = df.groupby("time")["T"].sum() * (dx * dy)
                
                # ★ Считаем ошибку для этого метода
                rmse = self._calc_rmse(exp_df, df)
                
                # Формируем подпись с ошибкой
                legend_label = f"{label} (RMSE: {rmse:.1f})" if not np.isnan(rmse) else label
                
                ax.plot(vol.index, vol.values, color=color, linewidth=2, label=legend_label)
                has_data = True

        if has_data:
            # Увеличиваем размер шрифта легенды, чтобы RMSE было хорошо видно
            ax.legend(fontsize=10, loc="upper left")
            ax.set_title("Сравнение методов (Рост опухоли без терапии)")
            if exp_df is not None and not exp_df.empty:
                # Даем немного места сверху для легенды
                ax.set_ylim(bottom=0, top=max(exp_df["volume"].max() * 1.4, 10))
        else:
            ax.set_title("Нет данных для отображения")

        self.fig.tight_layout()
        self.canvas.draw_idle()


# ── Обновленный VisualizationPanel ───────────────────────────
class VisualizationPanel(QWidget):
    compareRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self.df = None
        self._current_day = 0.0
        self.last_exp_csv = None

        layout = QVBoxLayout(self)

        # ── верхняя строка ───────────────────────────────────
        top = QHBoxLayout()
        self.combo_var = QComboBox()
        self.combo_var.addItems(["C","T","I","a_t","Ch","Im"])
        self.combo_var.currentTextChanged.connect(self.refresh)

        self.lbl_day = QLabel("день: —")
        self.slider_day = QSlider(Qt.Horizontal)
        self.slider_day.setRange(0, 1000)
        self.slider_day.valueChanged.connect(self._on_slider)

        top.addWidget(QLabel("Переменная:"))
        top.addWidget(self.combo_var)
        top.addWidget(self.lbl_day)
        top.addWidget(self.slider_day, stretch=1)
        layout.addLayout(top)

        # ── вкладки ──────────────────────────────────────────
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        self.tabs.addTab(self._make_tab(draw_spatial),         "2D-карта")
        self.tabs.addTab(self._make_tab(draw_overlay),         "C + T")
        self.tabs.addTab(self._make_tab(draw_slice_x),         "Срез по x")
        self.tabs.addTab(self._make_tab(draw_slice_y),         "Срез по y")
        self.tabs.addTab(self._make_tab(draw_total_dynamics),  "Динамика объёма")
        self.tabs.addTab(self._make_tab(draw_center_dynamics), "Центр")

        # Новая вкладка
        self.compare_chart = MultiMethodCompareChart()
        self.compare_chart.btn_run.clicked.connect(self._on_compare_clicked)
        self.tabs.addTab(self.compare_chart, "Сравнение методов")

        self.opt_chart = OptimizationChart()
        self.tabs.addTab(self.opt_chart, "Обучение")

        self.tabs.currentChanged.connect(self.refresh)

    def _make_tab(self, draw_func):
        w = QWidget()
        v = QVBoxLayout(w)
        fig = Figure(figsize=(8, 6))
        canvas = FigureCanvas(fig)
        v.addWidget(canvas)
        w._draw_func = draw_func
        w._fig = fig
        return w

    def _on_compare_clicked(self):
        if not self.last_exp_csv:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите CSV в вкладке 'Обучение'")
            return
        self.compareRequested.emit(self.last_exp_csv)
        self.compare_chart._init_plot("Идет расчет 3 методов... Подождите.")

    def update_compare_chart(self, exp_df, df_exp, df_imp, df_rk):
        self.compare_chart.draw(exp_df, df_exp, df_imp, df_rk)
        idx = self.tabs.indexOf(self.compare_chart)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def on_data_ready(self, df):
        self.df = df
        days = sorted(df["time"].unique())
        self._days = days
        self._current_day = days[-1]
        self.lbl_day.setText(f"день: {self._current_day:.1f}")
        self.refresh()

    def _on_slider(self, val):
        if self.df is None: return
        i = int(val / 1000 * (len(self._days) - 1))
        self._current_day = self._days[i]
        self.lbl_day.setText(f"день: {self._current_day:.1f}")
        self.refresh()

    def update_optimization_chart(self, exp_df, traj_df):
        self.opt_chart.draw(exp_df=exp_df, traj_df=traj_df)
        idx = self.tabs.indexOf(self.opt_chart)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)

    def refresh(self):
        if self.df is None: return
        tab = self.tabs.currentWidget()
        if tab is None: return
        if tab is self.opt_chart or tab is self.compare_chart:
            return
        var = self.combo_var.currentText()
        try:
            tab._draw_func(tab._fig, self.df, self._current_day, var)
        except Exception as e:
            tab._fig.clear()
            ax = tab._fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Ошибка: {e}", ha='center', va='center')
            tab._fig.canvas.draw_idle()