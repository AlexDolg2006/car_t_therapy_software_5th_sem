from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QGroupBox, QComboBox, QDoubleSpinBox,
                               QPushButton, QProgressBar, QLabel, QMessageBox)
from PySide6.QtCore import QThread, Signal
from pathlib import Path
import traceback
import pandas as pd

from .sweeps import Sweep, SWEEPABLE
from .experiment import ExperimentManager


class SweepThread(QThread):
    progress = Signal(int, str)
    log      = Signal(str)
    ok       = Signal(str, object)   # exp_dir, summary DataFrame
    fail     = Signal(str)

    def __init__(self, manager, base_cfg, sweep):
        super().__init__()
        self.manager = manager
        self.base_cfg = base_cfg
        self.sweep = sweep

    def run(self):
        try:
            exp_dir, summary = self.manager.run_sweep(
                self.base_cfg, self.sweep,
                on_progress=lambda p, m: self.progress.emit(p, m),
                on_log=self.log.emit,
            )
            self.ok.emit(str(exp_dir), summary)
        except Exception as e:
            self.fail.emit(f"{e}\n\n{traceback.format_exc()}")


class SweepControlPanel(QWidget):
    """Левая панель сверху: настройка и запуск sweep-серии."""
    sweepFinished = Signal(str, object)   # exp_dir, summary DataFrame

    def __init__(self, manager: ExperimentManager, cfg_provider):
        super().__init__()
        self.manager = manager
        self.cfg_provider = cfg_provider

        layout = QVBoxLayout(self)

        g = QGroupBox("Параметрический анализ")
        f = QFormLayout(g)

        self.cb_param = QComboBox()
        for name in SWEEPABLE.keys():
            self.cb_param.addItem(name)

        self.sp_from = QDoubleSpinBox(); self.sp_from.setRange(-1e9, 1e9); self.sp_from.setDecimals(6)
        self.sp_to   = QDoubleSpinBox(); self.sp_to.setRange(-1e9, 1e9); self.sp_to.setDecimals(6)
        self.sp_step = QDoubleSpinBox(); self.sp_step.setRange(1e-9, 1e9); self.sp_step.setDecimals(6)
        self.sp_step.setValue(0.01)

        f.addRow("Параметр:", self.cb_param)
        f.addRow("От:",  self.sp_from)
        f.addRow("До:",  self.sp_to)
        f.addRow("Шаг:", self.sp_step)

        layout.addWidget(g)

        row = QHBoxLayout()
        self.btn_run = QPushButton("Запустить серию")
        self.btn_run.setMinimumHeight(34)
        self.btn_run.clicked.connect(self.on_run)
        row.addWidget(self.btn_run)
        layout.addLayout(row)

        self.progress = QProgressBar(); self.progress.setRange(0, 100)
        layout.addWidget(self.progress)

        self.status = QLabel("Готово.")
        layout.addWidget(self.status)

        self.cb_param.currentTextChanged.connect(self._sync_defaults)
        self._sync_defaults(self.cb_param.currentText())

    def _sync_defaults(self, name):
        try:
            cfg = self.cfg_provider()
            section, field = SWEEPABLE[name]
            val = float(getattr(getattr(cfg, section), field))
        except Exception:
            return
        self.sp_from.setValue(val * 0.5 if val != 0 else 0.0)
        self.sp_to.setValue(val * 1.5 if val != 0 else 1.0)

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

        self.thread = SweepThread(self.manager, base_cfg, sweep)
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
        # сообщаем вкладке справа
        self.sweepFinished.emit(exp_dir, summary)

    def _on_fail(self, msg):
        self.btn_run.setEnabled(True)
        self.status.setText("Ошибка.")
        QMessageBox.critical(self, "Ошибка", msg)