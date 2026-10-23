import sys
from pathlib import Path
import copy
import pandas as pd

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                               QHBoxLayout, QVBoxLayout, QPushButton,
                               QProgressBar, QLabel, QMessageBox, QTabWidget)
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QThread, Signal, QObject

from modules.therapy_config.panel import TherapyConfigPanel
from modules.visualization.panel import VisualizationPanel
from modules.visualization.parametric import ParametricView
from modules.automation import OptimizationPanel
from modules.automation.parametric_panel import SweepControlPanel
from modules.automation.experiment import ExperimentManager
from modules.solver.runner import SolverRunner

PROJECT_ROOT = Path(__file__).parent
BIN_DIR      = PROJECT_ROOT / "bin"
DATA_DIR     = PROJECT_ROOT / "data"
EXP_DIR      = PROJECT_ROOT / "experiments"


class SolverSignals(QObject):
    progress = Signal(int)
    log      = Signal(str)
    ok       = Signal(str)
    fail     = Signal(str)


class SolverThread(QThread):
    def __init__(self, runner, cfg, out_csv):
        super().__init__()
        self.runner = runner
        self.cfg = cfg
        self.out_csv = out_csv
        self.signals = SolverSignals()

    def run(self):
        try:
            path = self.runner.run(
                self.cfg, self.out_csv,
                on_progress=self.signals.progress.emit,
                on_log=self.signals.log.emit,
            )
            self.signals.ok.emit(str(path))
        except Exception as e:
            self.signals.fail.emit(str(e))


# ★ Поток для сравнения трёх методов (чистая модель, без терапии)
class CompareThread(QThread):
    finished = Signal(object, object, object, object)  # exp_df, df_exp, df_imp, df_rk
    error    = Signal(str)

    def __init__(self, runner, base_cfg, csv_path):
        super().__init__()
        self.runner = runner
        self.base_cfg = base_cfg
        self.csv_path = csv_path

    def run(self):
        try:
            exp_df = None
            if self.csv_path and Path(self.csv_path).exists():
                exp_df = pd.read_csv(self.csv_path)

            methods = ["explicit_euler", "implicit_euler", "rk4"]
            results = {}

            for m in methods:
                cfg = copy.deepcopy(self.base_cfg)
                cfg.therapy.method = m
                
                # ★ ОТКЛЮЧАЕМ ТЕРАПИЮ (модель чистой опухоли)
                cfg.therapy.dose_day = 0.0       
                cfg.therapy.day_chemo = 9999.0   
                cfg.therapy.day_immuno = 9999.0  
                cfg.vessels.count = 0            
                
                out_csv = DATA_DIR / f"compare_{m}.csv"
                self.runner.run(cfg, out_csv)
                results[m] = pd.read_csv(out_csv)

            self.finished.emit(
                exp_df,
                results["explicit_euler"],
                results["implicit_euler"],
                results["rk4"],
            )
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAR-T Desktop")
        self.resize(1600, 900)

        self.runner = SolverRunner(BIN_DIR, DATA_DIR)
        self.exp_manager = ExperimentManager(self.runner, EXP_DIR)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        body = QHBoxLayout()

        # ── ЛЕВАЯ ПАНЕЛЬ ─────────────────────────────────────
        self.left_tabs = QTabWidget()
        self.left_tabs.setMinimumWidth(420)
        self.left_tabs.setMaximumWidth(560)

        self.panel_cfg = TherapyConfigPanel()
        self.left_tabs.addTab(self.panel_cfg, "Коэффициенты")

        self.panel_opt = OptimizationPanel(BIN_DIR, DATA_DIR)
        self.left_tabs.addTab(self.panel_opt, "Обучение")

        self.panel_sweep = SweepControlPanel(
            manager=self.exp_manager,
            cfg_provider=lambda: self.panel_cfg.get_config(),
        )
        self.left_tabs.addTab(self.panel_sweep, "Параметрический анализ")

        # ── ПРАВАЯ ЧАСТЬ ─────────────────────────────────────
        self.right_tabs = QTabWidget()

        self.panel_viz = VisualizationPanel()
        self.right_tabs.addTab(self.panel_viz, "Визуализация")

        self.panel_param = ParametricView()
        self.right_tabs.addTab(self.panel_param, "Параметрический анализ")

        body.addWidget(self.left_tabs,  3)
        body.addWidget(self.right_tabs, 7)
        root.addLayout(body, stretch=1)

        # ── Нижняя строка ────────────────────────────────────
        bottom = QHBoxLayout()
        self.btn_run = QPushButton("Вычислить")
        self.btn_run.setMinimumHeight(40)
        self.btn_run.clicked.connect(self.on_run)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status = QLabel("Готово.")
        bottom.addWidget(self.btn_run)
        bottom.addWidget(self.progress, stretch=1)
        root.addLayout(bottom)
        root.addWidget(self.status)

        # ── Связи ────────────────────────────────────────────
        self.panel_opt.set_params_provider(
            lambda: self.panel_cfg.get_config().to_dict_flat()
        )
        self.panel_opt.coefficientsFound.connect(self._apply_optimized)
        self.panel_opt.plotDataReady.connect(self.panel_viz.update_optimization_chart)
        self.panel_sweep.sweepFinished.connect(self._on_sweep_done)

        # ★ ИСПРАВЛЕНО: связываем сигнал и слот с одним аргументом (str)
        self.panel_opt.csvSelected.connect(self._on_csv_selected)
        self.panel_viz.compareRequested.connect(self._on_compare_requested)

    def _on_progress(self, value: int):
        self.progress.setValue(value)

    def _on_log(self, text: str):
        self.status.setText(text)

    def _apply_optimized(self, result: dict):
        try:
            self.panel_cfg.apply_coefficients(result)
            self.status.setText("Коэффициенты обновлены из оптимизации.")
            self.left_tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось применить:\n{e}")

    def _on_sweep_done(self, exp_dir: str, summary):
        self.panel_param.load_sweep(exp_dir, summary)
        self.right_tabs.setCurrentWidget(self.panel_param)
        self.status.setText(f"Серия готова: {exp_dir}")
        try:
            out = self.panel_param.save_pngs(Path(exp_dir))
            self.status.setText(f"Серия готова, графики: {out}")
        except Exception as e:
            self.status.setText(f"Серия готова, но графики не сохранены: {e}")

    # ★ Слот принимает только один аргумент (csv_path)
    def _on_csv_selected(self, path: str):
        self.panel_viz.last_exp_csv = path

    def _on_compare_requested(self, csv_path: str):
        cfg = self.panel_cfg.get_config()
        self.btn_run.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Запуск сравнения 3 методов...")

        self.compare_thread = CompareThread(self.runner, cfg, csv_path)
        self.compare_thread.finished.connect(self._on_compare_done)
        self.compare_thread.error.connect(self._on_compare_fail)
        self.compare_thread.start()

    def _on_compare_done(self, exp_df, df_exp, df_imp, df_rk):
        self.btn_run.setEnabled(True)
        self.progress.setValue(100)
        self.status.setText("Сравнение 3 методов завершено.")
        self.panel_viz.update_compare_chart(exp_df, df_exp, df_imp, df_rk)

    def _on_compare_fail(self, msg: str):
        self.btn_run.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText("Ошибка сравнения.")
        QMessageBox.critical(self, "Ошибка сравнения методов", msg)

    def on_run(self):
        cfg = self.panel_cfg.get_config()
        out_csv = DATA_DIR / "car-t-2d.csv"
        self.btn_run.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Запуск C++...")

        self.thread = SolverThread(self.runner, cfg, out_csv)
        self.thread.signals.progress.connect(self._on_progress)
        self.thread.signals.log.connect(self._on_log)
        self.thread.signals.ok.connect(self.on_done)
        self.thread.signals.fail.connect(self.on_fail)
        self.thread.start()

    def on_done(self, csv_path):
        self.btn_run.setEnabled(True)
        self.status.setText(f"Готово: {csv_path}")
        try:
            df = pd.read_csv(csv_path)
            self.panel_viz.on_data_ready(df)
            self.right_tabs.setCurrentWidget(self.panel_viz)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать CSV:\n{e}")

    def on_fail(self, msg):
        self.btn_run.setEnabled(True)
        self.progress.setValue(0)
        self.status.setText("Ошибка.")
        QMessageBox.critical(self, "Ошибка расчета", msg)


def _apply_light_palette(app):
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(245, 245, 245))
    palette.setColor(QPalette.WindowText,      QColor(20, 20, 20))
    palette.setColor(QPalette.Base,            QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase,   QColor(240, 240, 240))
    palette.setColor(QPalette.ToolTipBase,     QColor(255, 255, 220))
    palette.setColor(QPalette.ToolTipText,     QColor(20, 20, 20))
    palette.setColor(QPalette.Text,            QColor(20, 20, 20))
    palette.setColor(QPalette.Button,          QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText,      QColor(20, 20, 20))
    palette.setColor(QPalette.BrightText,      QColor(255, 0, 0))
    palette.setColor(QPalette.Link,            QColor(0, 102, 204))
    palette.setColor(QPalette.Highlight,       QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Disabled, QPalette.Text,       QColor(150, 150, 150))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(150, 150, 150))
    app.setPalette(palette)


def main():
    app = QApplication(sys.argv)
    _apply_light_palette(app)
    w = MainWindow()
    w.show()
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
        sys.exit(0)


if __name__ == "__main__":
    main()