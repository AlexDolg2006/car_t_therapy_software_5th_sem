# modules/visualization/panel.py  (верхняя часть файла)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QTabWidget, QLabel, QComboBox, QSlider,
                               QPushButton, QMessageBox, QTableWidget,
                               QTableWidgetItem, QHeaderView, QCheckBox)
from PySide6.QtCore import Qt, Signal, QThread
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, NullFormatter
import numpy as np
import pandas as pd

from .spatial  import draw_spatial
from .slices   import draw_slice_x, draw_slice_y
from .overlay  import draw_overlay
from .dynamics import draw_total_dynamics, draw_center_dynamics
from .optimization_chart import OptimizationChart


DT_LIST = [0.4, 0.2, 0.1]      # ОДИНАКОВЫЕ шаги для ВСЕХ методов
DT_REF  = 0.0125                     # шаг эталона (RK4), в 4 раза меньше min(DT_LIST)
SAVE_DT = 2.0                        # общий шаг сохранения (кратен всем dt)
SMOOTH_W = 0.5                       # ширина сглаживания импульсов, дни
IMPL_TOL, IMPL_ITER = 1e-12, 200     # точное решение неявной системы
COMPARE_NX = COMPARE_NY = 40

METHODS = [
    ("explicit_euler", "Явный Эйлер",   "blue",   "o"),
    ("implicit_euler", "Неявный Эйлер", "green",  "s"),
    ("rk4",            "Рунге-Кутта 4", "purple", "^"),
]


class CompareWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(object, object)
    error    = Signal(str)

    def __init__(self, chart, cfg, smooth):
        super().__init__()
        self.chart, self.cfg, self.smooth = chart, cfg, smooth

    def run(self):
        try:
            self.progress.emit(1, f"Эталон (RK4, dt={DT_REF})...")
            t_ref, v_ref, t_cpu_ref, _ = self.chart._run_solver_once(
                self.cfg, "rk4", DT_REF, self.smooth)

            self.progress.emit(3, f"Проверка эталона (RK4, dt={2*DT_REF})...")
            t_chk, v_chk, _, _ = self.chart._run_solver_once(
                self.cfg, "rk4", 2 * DT_REF, self.smooth)
            v_scale = float(np.max(np.abs(v_ref))) or 1.0
            ref_self_err = float(np.max(np.abs(
                np.interp(t_ref, t_chk, v_chk) - v_ref)))

            results = {label: [] for _, label, _, _ in METHODS}
            total = len(METHODS) * len(DT_LIST)
            done = 0

            for key, label, _, _ in METHODS:
                for dt in DT_LIST:
                    done += 1
                    self.progress.emit(
                        5 + int(95 * done / total), f"{label}: dt={dt}")
                    rec = dict(dt_nominal=dt, dt=dt, err=np.nan,
                               rel_err=np.nan, time=np.nan, status="ok")
                    try:
                        t_m, v_m, elapsed, dt_act = self.chart._run_solver_once(
                            self.cfg, key, dt, self.smooth)
                        rec["dt"], rec["time"] = dt_act, elapsed
                        v_ref_on = np.interp(t_m, t_ref, v_ref)
                        diff = np.abs(v_m - v_ref_on)
                        if not np.all(np.isfinite(diff)):
                            rec["status"] = "неустойчив"
                        else:
                            rec["err"] = float(np.max(diff))
                            rec["rel_err"] = rec["err"] / v_scale
                    except Exception:
                        rec["status"] = "сбой"
                    results[label].append(rec)

            meta = dict(ref_self_err=ref_self_err,
                        ref_self_rel=ref_self_err / v_scale,
                        t_cpu_ref=t_cpu_ref, smooth=self.smooth)
            self.finished.emit(results, meta)
            self.progress.emit(100, "Готово")
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

class MultiMethodCompareChart(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg_provider    = None
        self._current_cfg    = None
        self._worker         = None
        self.progress_signal = None

        layout = QVBoxLayout(self)
        top = QHBoxLayout()
        self.btn_run = QPushButton("Сравнить 3 метода (эталон vs методы)")
        self.btn_run.setMinimumHeight(30)
        top.addWidget(QLabel("Сравнение численных методов"))
        top.addStretch()
        top.addWidget(self.btn_run)
        self.chk_smooth = QCheckBox("Гладкие импульсы терапии (для проверки порядка)")
        self.chk_smooth.setChecked(True)
        top.addWidget(self.chk_smooth)
        layout.addLayout(top)

        self.fig = Figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=3)

        self.lbl_ref = QLabel("")
        layout.addWidget(self.lbl_ref)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Метод", "dt", "max|V−V_ref|", "Отн. ошибка", "Время, с", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table, stretch=2)

        self._init_plot()

    def _init_plot(self, msg="Нажмите кнопку для запуска"):
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set_xlabel("Шаг по времени dt")
        ax.set_ylabel("Ошибка max|V_method − V_ref|")
        ax.grid(True, which="both", linestyle=":", alpha=0.6)
        ax.set_title(msg)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    def set_current_cfg(self, cfg):
        self._current_cfg = cfg

    def start_correct_comparison(self, cfg, exp_df=None):
        if self._worker is not None and self._worker.isRunning():
            return
        self.set_current_cfg(cfg)
        self._init_plot("Расчёт эталона и трёх методов…")
        self.table.setRowCount(0)
        self.lbl_ref.setText("")
        self.btn_run.setEnabled(False)
        smooth = SMOOTH_W if self.chk_smooth.isChecked() else 0.0
        self._worker = CompareWorker(self, cfg, smooth)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, p, text):
        if self.progress_signal is not None:
            self.progress_signal.emit(p, text)

    def _on_finished(self, results, meta):
        self.btn_run.setEnabled(True)
        self._plot(results)
        self._fill_table(results)
        self.lbl_ref.setText(
            f"Эталон: RK4, dt={DT_REF}. Самооценка точности эталона "
            f"(сравнение с dt={2*DT_REF}): {meta['ref_self_err']:.2e} "
            f"(отн. {meta['ref_self_rel']:.2e}). "
            f"Ошибки методов должны быть заметно больше этой величины.")

    def _on_error(self, msg):
        self.btn_run.setEnabled(True)
        self._init_plot("Ошибка — см. сообщение")
        QMessageBox.critical(self, "Ошибка сравнения", msg)

    # ── один запуск C++ решателя ─────────────────────────────────────
    def _run_solver_once(self, cfg, method: str, dt_target: float, smooth: float = 0.0):
        """Возвращает (t, V(t), время расчёта, фактический dt)."""
        import copy, tempfile, subprocess as sp, json, time
        from pathlib import Path

        cfg2 = copy.deepcopy(cfg)
        # C++ считает dt = Tt/Nt, поэтому Nt без «+1»
        cfg2.grid.Nt = max(1, int(round(cfg2.grid.Tt / dt_target)))
        dt_actual = cfg2.grid.Tt / cfg2.grid.Nt
        cfg2.therapy.method = method
        cfg2.grid.Nx = COMPARE_NX
        cfg2.grid.Ny = COMPARE_NY

        flat = {
            "Nx": cfg2.grid.Nx, "Ny": cfg2.grid.Ny,
            "Lx": cfg2.grid.Lx, "Ly": cfg2.grid.Ly,
            "Nt": cfg2.grid.Nt, "Tt": cfg2.grid.Tt,
            "T0_volume": cfg2.tumor.T0_volume, "sigma": cfg2.tumor.sigma,
            "x_center": cfg2.tumor.x_center, "y_center": cfg2.tumor.y_center,
            "num_vessels": cfg2.vessels.count, "vessel_seed": cfg2.vessels.seed,
            "day_cart": cfg2.therapy.dose_day, "day_chemo": cfg2.therapy.day_chemo,
            "day_immuno": cfg2.therapy.day_immuno, "bc": cfg2.therapy.bc,
            "method": cfg2.therapy.method,
            **{k: getattr(cfg2.params, k) for k in [
                "Dc", "Dt", "Dch", "Dim", "rc", "rt", "hc", "ht",
                "kct", "ki", "uc", "ut", "ui", "a", "b", "g", "deltach", "deltaim"
            ]}
        }

        root = Path(__file__).resolve().parents[2]
        exe = root / "bin" / "modeling_2d"

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            params_f = tmp / "params.json"
            out_csv  = tmp / "out.csv"
            params_f.write_text(json.dumps(flat, indent=2))

            cmd = [str(exe), "--out", str(out_csv), "--params", str(params_f),
                   "--method", method,
                   "--save_dt", str(SAVE_DT),
                   "--smooth", str(smooth),
                   "--tol", str(IMPL_TOL), "--max_iter", str(IMPL_ITER)]
            t_start = time.perf_counter()
            proc = sp.run(cmd, capture_output=True, text=True)
            elapsed = time.perf_counter() - t_start
            if proc.returncode != 0:
                raise RuntimeError(
                    f"{method} dt={dt_target} failed.\n{proc.stderr[-500:]}")
            df = pd.read_csv(out_csv)

        xs = np.sort(df["x"].unique()); ys = np.sort(df["y"].unique())
        cell = np.diff(xs).mean() * np.diff(ys).mean()
        vol = df.groupby("time")["T"].sum() * cell
        return vol.index.to_numpy(), vol.to_numpy(), elapsed, dt_actual

    # ── графики ──────────────────────────────────────────────────────
    @staticmethod
    def _fit_order(dts, errs):
        dts, errs = np.asarray(dts), np.asarray(errs)
        m = np.isfinite(errs) & (errs > 1e-14)   # отбрасываем «пол» округлений
        if m.sum() < 2:
            return None
        return float(np.polyfit(np.log10(dts[m]), np.log10(errs[m]), 1)[0])

    def _plot(self, results):
        self.fig.clear()
        ax1 = self.fig.add_subplot(121)
        ax2 = self.fig.add_subplot(122)
        styles = {label: (c, m) for _, label, c, m in METHODS}

        for label, recs in results.items():
            color, marker = styles[label]
            good = [r for r in recs if np.isfinite(r["err"]) and r["err"] > 0]
            if not good:
                continue
            dts  = np.array([r["dt"] for r in good])
            errs = np.array([r["err"] for r in good])
            tms  = np.array([r["time"] for r in good])

            # порядок сходимости - в подпись легенды, а не на график
            p = self._fit_order(dts, errs)
            lbl = f"{label} (p ≈ {p:.2f})" if p is not None else label

            ax1.loglog(dts, errs, color=color, marker=marker, markersize=8,
                       linewidth=2, label=lbl)
            ax2.loglog(tms, errs, color=color, marker=marker, markersize=8,
                       linewidth=2, label=label)

        ax1.set_xlabel("Шаг по времени Δt (лог. шкала сут)")
        ax1.set_ylabel("Ошибка max|V − V_ref| (лог. шкала мм³)")
        ax1.set_title("")
        ax1.grid(True, which="both", linestyle=":", alpha=0.6)
        ax1.legend(fontsize=9, loc="lower right")
        ax1.set_xticks(DT_LIST)
        ax1.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))
        ax1.xaxis.set_minor_formatter(NullFormatter())

        ax2.set_xlabel("Время вычислений, с")
        ax2.set_ylabel("Ошибка max|V − V_ref|")
        ax2.set_title("Точность vs стоимость")
        ax2.grid(True, which="both", linestyle=":", alpha=0.6)
        ax2.legend(fontsize=9, loc="best")

        self.fig.tight_layout()
        self.canvas.draw_idle()

        print("\n=== Сравнение численных методов (эталон: RK4, "
              f"dt={DT_REF}) ===")
        for label, recs in results.items():
            for r in recs:
                print(f"{label:<16} dt={r['dt']:<8.4f} err={r['err']:.4e} "
                      f"rel={r['rel_err']:.3e} time={r['time']:.3f}s "
                      f"[{r['status']}]")
            p = self._fit_order([r["dt"] for r in recs],
                                [r["err"] for r in recs])
            if p is not None:
                print(f"  порядок сходимости p ≈ {p:.2f}")

    def _fill_table(self, results):
        rows = [(label, r) for label, recs in results.items() for r in recs]
        self.table.setRowCount(len(rows))
        for i, (label, r) in enumerate(rows):
            vals = [
                label,
                f"{r['dt']:.4g}",
                f"{r['err']:.3e}" if np.isfinite(r["err"]) else "—",
                f"{r['rel_err']:.3e}" if np.isfinite(r["rel_err"]) else "—",
                f"{r['time']:.3f}" if np.isfinite(r["time"]) else "—",
                r["status"],
            ]
            for j, v in enumerate(vals):
                self.table.setItem(i, j, QTableWidgetItem(v))

class VisualizationPanel(QWidget):
    compareRequested = Signal(str)
    compareProgress  = Signal(int, str)
    compareFinished  = Signal()

    def __init__(self):
        super().__init__()
        self.df = None
        self._current_day = 0.0
        self.last_exp_csv = None
        self._last_exp_df = None
        self.cfg_provider = None

        layout = QVBoxLayout(self)

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

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, stretch=1)

        self.tabs.addTab(self._make_tab(draw_spatial),         "2D-карта")
        self.tabs.addTab(self._make_tab(draw_overlay),         "C + T")
        self.tabs.addTab(self._make_tab(draw_slice_x),         "Срез по x")
        self.tabs.addTab(self._make_tab(draw_slice_y),         "Срез по y")
        self.tabs.addTab(self._make_tab(draw_total_dynamics),  "Динамика объёма")
        self.tabs.addTab(self._make_tab(draw_center_dynamics), "Центр")

        self.compare_chart = MultiMethodCompareChart()
        self.compare_chart.progress_signal = self.compareProgress
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

    def set_cfg_provider(self, provider):
        self.cfg_provider = provider

    def _on_compare_clicked(self):
        if self.cfg_provider is None:
            QMessageBox.warning(self, "Нет конфигурации", "Не задан источник параметров.")
            return
        try:
            cfg = self.cfg_provider()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось получить cfg:\n{e}")
            return

        idx = self.tabs.indexOf(self.compare_chart)
        if idx >= 0:
            self.tabs.setCurrentIndex(idx)
        self.compare_chart.start_correct_comparison(cfg, self._last_exp_df)

    def update_compare_chart(self, exp_df=None):
        self._last_exp_df = exp_df
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
        if tab is None or tab is self.opt_chart or tab is self.compare_chart:
            return
        var = self.combo_var.currentText()
        try:
            tab._draw_func(tab._fig, self.df, self._current_day, var)
        except Exception as e:
            tab._fig.clear()
            ax = tab._fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Ошибка: {e}", ha='center', va='center')
            tab._fig.canvas.draw_idle()


