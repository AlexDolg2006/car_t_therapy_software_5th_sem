from pathlib import Path
import subprocess, json, shutil
from datetime import datetime
import pandas as pd

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
                               QPushButton, QComboBox, QLabel, QGroupBox,
                               QFileDialog, QMessageBox, QTextEdit,
                               QTableWidget, QTableWidgetItem, QCheckBox,
                               QDoubleSpinBox, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Signal, QObject, QThread


# ── Таблица пространства поиска ─────────────────────────────
OPTIMIZABLE = [
    ("Dt",        1e-6, 1e-2,  5e-5),
    ("rt",        1e-3, 1.0,   0.05),
    ("ht",        1e-3, 1.0,   0.05),
    ("a",         1e-3, 1.0,   0.10),
    ("b",         1e-3, 1.0,   0.05),
    ("g",         1e-3, 1.0,   0.01),
    ("T0_volume", 1.0,  500.0, 50.0),
]



class OptimParamTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(0, 5, parent)
        self.setHorizontalHeaderLabels(
            ["Параметр", "Опт.", "От", "До", "Старт"]
        )
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setMaximumHeight(240)

        for name, lo, hi, init in OPTIMIZABLE:
            r = self.rowCount()
            self.insertRow(r)
            self.setItem(r, 0, QTableWidgetItem(name))
            cb = QCheckBox(); cb.setChecked(True)
            self.setCellWidget(r, 1, cb)
            for col, value in ((2, lo), (3, hi), (4, init)):
                sp = QDoubleSpinBox()
                sp.setDecimals(8)
                sp.setRange(1e-12, 1e12)
                sp.setValue(value)
                self.setCellWidget(r, col, sp)

    def to_space_dict(self) -> dict:
        d = {}
        for r in range(self.rowCount()):
            name = self.item(r, 0).text()
            on   = self.cellWidget(r, 1).isChecked()
            lo   = self.cellWidget(r, 2).value()
            hi   = self.cellWidget(r, 3).value()
            init = self.cellWidget(r, 4).value()
            d[name] = {"on": int(on), "lo": lo, "hi": hi, "init": init,
                       "step": max((hi - lo) * 0.01, 1e-8)}
        return d


# ── Поток + сигналы ──────────────────────────────────────────
class _OptimizerSignals(QObject):
    log  = Signal(str)
    done = Signal(dict)
    fail = Signal(str)


class _OptimizerWorker(QThread):
    def __init__(self, exe: Path, csv_path: Path, method: str,
                 out_json: Path, params_json: Path, space_json: Path):
        super().__init__()
        self.exe = exe
        self.csv_path = csv_path
        self.method = method
        self.out_json = out_json
        self.params_json = params_json
        self.space_json = space_json
        self.signals = _OptimizerSignals()

    def run(self):
        try:
            cmd = [str(self.exe),
                   "--csv",    str(self.csv_path),
                   "--method", self.method,
                   "--out",    str(self.out_json)]
            if self.params_json is not None:
                cmd += ["--params", str(self.params_json)]
            if self.space_json is not None:
                cmd += ["--space",  str(self.space_json)]

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            for line in proc.stdout:
                self.signals.log.emit(line.rstrip())
            proc.wait()
            if proc.returncode != 0:
                raise RuntimeError(f"optimizer exited with code {proc.returncode}")
            result = json.loads(self.out_json.read_text())
            self.signals.done.emit(result)
        except Exception as e:
            self.signals.fail.emit(str(e))

# ── Панель ──────────────────────────────────────────────────
class OptimizationPanel(QWidget):
    coefficientsFound = Signal(dict)
    plotDataReady = Signal(object, object)
    csvSelected = Signal(str) # <--- НОВЫЙ СИГНАЛ

    def __init__(self, bin_dir: Path, data_dir: Path):
        super().__init__()
        self.exe = Path(bin_dir) / "grad_optim"
        self.data_dir = Path(data_dir)
        self.csv_path = None
        self.params_provider = None

        layout = QVBoxLayout(self)

        g = QGroupBox("Обучение по экспериментальным данным")
        f = QFormLayout(g)

        self.btn_csv = QPushButton("Выбрать CSV…")
        self.btn_csv.clicked.connect(self._choose_csv)
        self.lbl_csv = QLabel("(файл не выбран)")
        row = QHBoxLayout()
        row.addWidget(self.btn_csv)
        row.addWidget(self.lbl_csv, stretch=1)
        f.addRow("Данные:", row)

        self.cb_method = QComboBox()
        self.cb_method.addItems(["coord", "grad"])
        f.addRow("Метод:", self.cb_method)

        layout.addWidget(g)

        g2 = QGroupBox("Пространство поиска")
        v2 = QVBoxLayout(g2)
        self.tbl_space = OptimParamTable()
        v2.addWidget(self.tbl_space)
        layout.addWidget(g2)

        self.btn_run = QPushButton("Найти коэффициенты")
        self.btn_run.setMinimumHeight(36)
        self.btn_run.clicked.connect(self._run)
        layout.addWidget(self.btn_run)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, stretch=1)

    def _choose_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите CSV с данными", "",
            "CSV files (*.csv);;All files (*)"
        )
        if path:
            self.csv_path = Path(path)
            self.lbl_csv.setText(str(self.csv_path))
            self.csvSelected.emit(str(self.csv_path))
            try:
                exp_df = pd.read_csv(self.csv_path)
                if "day" in exp_df.columns and "volume" in exp_df.columns:
                    self.plotDataReady.emit(exp_df, None)
            except Exception as e:
                self.log.append(f"[warn] {e}")

    def _run(self):
        if self.csv_path is None:
            QMessageBox.warning(self, "Нет данных", "Сначала выберите CSV-файл.")
            return
        if not self.exe.exists():
            QMessageBox.critical(self, "Ошибка", f"Не найден бинарник:\n{self.exe}")
            return

        self.btn_run.setEnabled(False)
        self.log.clear()
        self.log.append(f"Запуск ({self.cb_method.currentText()})…")

        params_json = self.data_dir / "optim_params.json"
        if self.params_provider is not None:
            params = self.params_provider()
            params_json.write_text(json.dumps(params, indent=2))
            self.log.append(f"Параметры из GUI → {params_json.name}")

        space_json = self.data_dir / "optim_space.json"
        space_json.write_text(json.dumps(self.tbl_space.to_space_dict(), indent=2))
        self.log.append(f"Пространство поиска → {space_json.name}")

        out_json = self.data_dir / "best_params.json"
        self.thread = _OptimizerWorker(
            self.exe, self.csv_path,
            self.cb_method.currentText(),
            out_json, params_json, space_json
        )
        self.thread.signals.log.connect(self.log.append)
        self.thread.signals.done.connect(self._on_done)
        self.thread.signals.fail.connect(self._on_fail)
        self.thread.start()

    def _on_done(self, result: dict):
        self.btn_run.setEnabled(True)
        self.log.append("")
        self.log.append("=== ГОТОВО ===")
        for k, v in result.items():
            self.log.append(f"  {k} = {v}")

        exp_df = None
        traj_df = None
        try:
            exp_df = pd.read_csv(self.csv_path)
            if "day" not in exp_df.columns or "volume" not in exp_df.columns:
                exp_df = None
        except Exception:
            pass
        traj_path = result.get("traj_csv")
        if traj_path and Path(traj_path).exists():
            try:
                traj_df = pd.read_csv(traj_path)
            except Exception as e:
                self.log.append(f"[warn] trajectory: {e}")

        # ── Автосохранение в experiments/opt_<ts>/ ─────────
        try:
            self._save_session(result, exp_df, traj_df)
        except Exception as e:
            self.log.append(f"[warn] save session: {e}")

        self.plotDataReady.emit(exp_df, traj_df)
        self.coefficientsFound.emit(result)

    def _on_fail(self, msg: str):
        self.btn_run.setEnabled(True)
        self.log.append(f"ОШИБКА: {msg}")
        QMessageBox.critical(self, "Ошибка оптимизации", msg)

    def set_params_provider(self, callback):
        self.params_provider = callback

    # ── Сохранение сессии ──────────────────────────────────
    def _save_session(self, result, exp_df, traj_df):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = self.data_dir.parent / "experiments" / f"opt_{ts}"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 1) JSON с параметрами
        bp = self.data_dir / "best_params.json"
        if bp.exists():
            shutil.copy(bp, out_dir / "best_params.json")

        # 2) траектория
        traj = result.get("traj_csv")
        if traj and Path(traj).exists():
            shutil.copy(traj, out_dir / "trajectory.csv")

        # 3) пространство поиска
        sp = self.data_dir / "optim_space.json"
        if sp.exists():
            shutil.copy(sp, out_dir / "optim_space.json")

        # 4) экспериментальные данные
        if self.csv_path and self.csv_path.exists():
            shutil.copy(self.csv_path, out_dir / "experiment.csv")

        # 5) график fit.png
        try:
            self._save_fit_plot(exp_df, traj_df, result, out_dir / "fit.png")
        except Exception as e:
            self.log.append(f"[warn] fit.png: {e}")

        # 6) сводная таблица
        rows = [{"metric": k, "value": v} for k, v in result.items()
                if k != "traj_csv"]
        df = pd.DataFrame(rows)
        df.to_csv(out_dir / "summary.csv", index=False)
        try:
            (out_dir / "summary.md").write_text(df.to_markdown(index=False))
        except Exception:
            (out_dir / "summary.md").write_text(df.to_string(index=False))

        self.log.append(f"Результаты сохранены: {out_dir}")

    def _save_fit_plot(self, exp_df, traj_df, result, png_path):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 6))
        if exp_df is not None and not exp_df.empty:
            ax.scatter(exp_df["day"], exp_df["volume"],
                       color="red", edgecolor="black", s=60,
                       label="Эксперимент", zorder=3)
        if traj_df is not None and not traj_df.empty:
            ax.plot(traj_df["day"], traj_df["volume"],
                    color="black", linewidth=2.0, label="Модель", zorder=1)
        ax.set_xlabel("t, сут")
        ax.set_ylabel("V, мм³")
        ax.set_title(f"Оптимизация ({result.get('method','?')}), "
                     f"loss = {result.get('loss', 0):.3e}")
        ax.grid(True, linestyle=":", alpha=0.6)
        if (exp_df is not None) or (traj_df is not None):
            ax.legend()
        fig.tight_layout()
        fig.savefig(png_path, dpi=150)
        plt.close(fig)