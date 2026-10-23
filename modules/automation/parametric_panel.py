from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                               QGroupBox, QComboBox, QDoubleSpinBox,
                               QPushButton, QProgressBar, QLabel, QMessageBox)
from PySide6.QtCore import QThread, Signal
import traceback

from .sweeps import Sweep, SWEEPABLE
from .experiment import ExperimentManager


class SweepThread(QThread):
    progress = Signal(int, str)
    log      = Signal(str)
    ok       = Signal(str, object)
    fail     = Signal(str)

    def __init__(self, manager, base_cfg, sweep,
                 x_target, y_target, day_target):
        super().__init__()
        self.manager = manager
        self.base_cfg = base_cfg
        self.sweep = sweep
        self.x_target = x_target
        self.y_target = y_target
        self.day_target = day_target

    def run(self):
        try:
            exp_dir, summary = self.manager.run_sweep(
                self.base_cfg, self.sweep,
                x_target=self.x_target,
                y_target=self.y_target,
                day_target=self.day_target,
                on_progress=lambda p, m: self.progress.emit(p, m),
                on_log=self.log.emit,
            )
            self.ok.emit(str(exp_dir), summary)
        except Exception as e:
            self.fail.emit(f"{e}\n\n{traceback.format_exc()}")


class SweepControlPanel(QWidget):
    sweepFinished = Signal(str, object)

    def __init__(self, manager: ExperimentManager, cfg_provider):
        super().__init__()
        self.manager = manager
        self.cfg_provider = cfg_provider

        layout = QVBoxLayout(self)

        # ── Развёртка параметра ──
        g_param = QGroupBox("Развёртка параметра")
        f_param = QFormLayout(g_param)
        self.cb_param = QComboBox()
        for name in SWEEPABLE.keys():
            self.cb_param.addItem(name)

        self.sp_from = QDoubleSpinBox(); self.sp_from.setRange(-1e9, 1e9); self.sp_from.setDecimals(6)
        self.sp_to   = QDoubleSpinBox(); self.sp_to.setRange(-1e9, 1e9); self.sp_to.setDecimals(6)
        self.sp_step = QDoubleSpinBox(); self.sp_step.setRange(1e-9, 1e9); self.sp_step.setDecimals(6)
        self.sp_step.setValue(0.01)

        f_param.addRow("Параметр:", self.cb_param)
        f_param.addRow("От:",  self.sp_from)
        f_param.addRow("До:",  self.sp_to)
        f_param.addRow("Шаг:", self.sp_step)
        layout.addWidget(g_param)

        # ── Точка наблюдения ──
        g_pt = QGroupBox("Точка наблюдения")
        f_pt = QFormLayout(g_pt)
        self.sp_x = QDoubleSpinBox(); self.sp_x.setRange(0, 10000); self.sp_x.setDecimals(3)
        self.sp_y = QDoubleSpinBox(); self.sp_y.setRange(0, 10000); self.sp_y.setDecimals(3)
        self.sp_day = QDoubleSpinBox(); self.sp_day.setRange(0, 100000); self.sp_day.setDecimals(3)
        self.sp_day.setValue(100.0)

        f_pt.addRow("x:",     self.sp_x)
        f_pt.addRow("y:",     self.sp_y)
        f_pt.addRow("День:",  self.sp_day)
        layout.addWidget(g_pt)

        # кнопка + прогресс
        self.btn_run = QPushButton("Запустить серию")
        self.btn_run.setMinimumHeight(36)
        self.btn_run.clicked.connect(self.on_run)
        layout.addWidget(self.btn_run)

        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.status = QLabel("Готово.")
        layout.addWidget(self.status)
        layout.addStretch()

        info = QLabel(
            "Все остальные параметры берутся со вкладки «Коэффициенты».\n"
            "Меняется только выбранный параметр.\n"
            "Значения полей берутся в точке (x, y) в указанный день\n"
            "(ближайший сохранённый в CSV)."
        )
        info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info)

        self.cb_param.currentTextChanged.connect(self._sync_defaults)
        self._sync_defaults(self.cb_param.currentText())

    def _sync_defaults(self, name):
        try:
            cfg = self.cfg_provider()
            section, field = SWEEPABLE[name]
            val = float(getattr(getattr(cfg, section), field))
        except Exception:
            val = 0.0
        self.sp_from.setValue(val * 0.5 if val != 0 else 0.0)
        self.sp_to.setValue(val * 1.5 if val != 0 else 1.0)

        try:
            cfg = self.cfg_provider()
            self.sp_x.setValue(float(getattr(cfg.tumor, "x_center", 50.0)))
            self.sp_y.setValue(float(getattr(cfg.tumor, "y_center", 50.0)))
            # по умолчанию — середина по времени
            self.sp_day.setValue(float(cfg.grid.Tt) / 2.0)
        except Exception:
            pass

    def on_run(self):
        name = self.cb_param.currentText()
        a, b, s = self.sp_from.value(), self.sp_to.value(), self.sp_step.value()
        if s <= 0 or b <= a:
            QMessageBox.warning(self, "Ошибка", "Проверьте диапазон и шаг")
            return

        sweep = Sweep(param=name, start=a, stop=b, step=s)
        base_cfg = self.cfg_provider()

        self.btn_run.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Запуск серии...")

        self.thread = SweepThread(
            self.manager, base_cfg, sweep,
            x_target=self.sp_x.value(),
            y_target=self.sp_y.value(),
            day_target=self.sp_day.value(),
        )
        self.thread.progress.connect(lambda p, m: (self.progress.setValue(p),
                                                   self.status.setText(m)))
        self.thread.log.connect(self.status.setText)
        self.thread.ok.connect(self._on_done)
        self.thread.fail.connect(self._on_fail)
        self.thread.start()

    def _on_done(self, exp_dir, summary):
        self.btn_run.setEnabled(True)
        self.progress.setValue(100)
        self.status.setText(f"Готово: {exp_dir}")
        self.sweepFinished.emit(exp_dir, summary)

    def _on_fail(self, msg):
        self.btn_run.setEnabled(True)
        self.status.setText("Ошибка.")
        QMessageBox.critical(self, "Ошибка", msg)