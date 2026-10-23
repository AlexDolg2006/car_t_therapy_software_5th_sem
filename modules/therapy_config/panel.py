from PySide6.QtWidgets import (QWidget, QFormLayout, QDoubleSpinBox,
                               QSpinBox, QComboBox, QGroupBox,
                               QVBoxLayout, QScrollArea)
from PySide6.QtCore import Signal
from shared.config_types import SimulationConfig


def _dspin(lo, hi, val, step=0.01, decimals=5):
    s = QDoubleSpinBox()
    s.setRange(lo, hi)
    s.setDecimals(decimals)
    s.setSingleStep(step)
    s.setValue(val)
    return s



class TherapyConfigPanel(QWidget):
    configChanged = Signal(object)

    def __init__(self):
        super().__init__()
        self.cfg = SimulationConfig()

        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        scroll.setWidget(container)

        # ── 1. Начальные условия (опухоль) ────────────────────
        g_nu = QGroupBox("Начальные условия (опухоль)")
        f_nu = QFormLayout(g_nu)

        self.sp_T0    = _dspin(0.0,  1e6,  self.cfg.tumor.T0_volume, step=1.0,    decimals=2)
        self.sp_sigma = _dspin(1e-6, 1.0,  self.cfg.tumor.sigma,     step=0.0001, decimals=6)
        self.sp_xc    = _dspin(0.0,  10000, self.cfg.tumor.x_center, step=1.0,    decimals=2)
        self.sp_yc    = _dspin(0.0,  10000, self.cfg.tumor.y_center, step=1.0,    decimals=2)

        f_nu.addRow("T0 (мм³):", self.sp_T0)
        f_nu.addRow("σ:",        self.sp_sigma)
        f_nu.addRow("x центра:", self.sp_xc)
        f_nu.addRow("y центра:", self.sp_yc)
        layout.addWidget(g_nu)

        # ── 1b. Сосуды ────────────────────────────────────────
        g_v = QGroupBox("Сосуды (источники терапии)")
        f_v = QFormLayout(g_v)

        self.sp_num_vessels = QSpinBox()
        self.sp_num_vessels.setRange(1, 10000)
        self.sp_num_vessels.setValue(self.cfg.vessels.count)

        self.sp_vessel_seed = QSpinBox()
        self.sp_vessel_seed.setRange(0, 2**31 - 1)
        self.sp_vessel_seed.setValue(self.cfg.vessels.seed)

        f_v.addRow("Кол-во сосудов:", self.sp_num_vessels)
        f_v.addRow("Seed (воспроизв.):", self.sp_vessel_seed)
        layout.addWidget(g_v)

        # ── 2. Расчётная сетка и время ────────────────────────
        g_grid = QGroupBox("Расчётная сетка и время")
        f_grid = QFormLayout(g_grid)

        self.sp_Nx = QSpinBox(); self.sp_Nx.setRange(10, 2000);    self.sp_Nx.setValue(self.cfg.grid.Nx)
        self.sp_Ny = QSpinBox(); self.sp_Ny.setRange(10, 2000);    self.sp_Ny.setValue(self.cfg.grid.Ny)
        self.sp_Nt = QSpinBox(); self.sp_Nt.setRange(10, 1000000); self.sp_Nt.setValue(self.cfg.grid.Nt)
        self.sp_Tt = _dspin(1.0, 100000, self.cfg.grid.Tt, step=10.0, decimals=2)
        self.sp_Lx = _dspin(1.0, 10000,  self.cfg.grid.Lx, step=10.0, decimals=2)
        self.sp_Ly = _dspin(1.0, 10000,  self.cfg.grid.Ly, step=10.0, decimals=2)

        f_grid.addRow("Nx:",        self.sp_Nx)
        f_grid.addRow("Ny:",        self.sp_Ny)
        f_grid.addRow("Nt:",        self.sp_Nt)
        f_grid.addRow("Tt (дней):", self.sp_Tt)
        f_grid.addRow("Lx:",        self.sp_Lx)
        f_grid.addRow("Ly:",        self.sp_Ly)
        layout.addWidget(g_grid)

        # ── 3. Коэффициенты модели ────────────────────────────
        g_p = QGroupBox("Коэффициенты модели")
        f_p = QFormLayout(g_p)

        self.sp_Dc  = _dspin(0.0, 1.0,  self.cfg.params.Dc,  step=0.001,   decimals=5)
        self.sp_Dt  = _dspin(0.0, 1.0,  self.cfg.params.Dt,  step=0.00001, decimals=7)
        self.sp_Dch = _dspin(0.0, 1.0,  self.cfg.params.Dch, step=0.001,   decimals=5)
        self.sp_Dim = _dspin(0.0, 1.0,  self.cfg.params.Dim, step=0.001,   decimals=5)

        self.sp_rc  = _dspin(0.0, 10.0, self.cfg.params.rc,  step=0.01,  decimals=5)
        self.sp_rt  = _dspin(0.0, 10.0, self.cfg.params.rt,  step=0.01,  decimals=5)
        self.sp_hc  = _dspin(0.0, 10.0, self.cfg.params.hc,  step=0.001, decimals=5)
        self.sp_ht  = _dspin(0.0, 10.0, self.cfg.params.ht,  step=0.001, decimals=5)

        self.sp_kct = _dspin(0.0, 10.0, self.cfg.params.kct, step=0.01,  decimals=5)
        self.sp_ki  = _dspin(0.0, 10.0, self.cfg.params.ki,  step=0.001, decimals=5)

        self.sp_uc  = _dspin(0.0, 10.0, self.cfg.params.uc,  step=0.01,  decimals=5)
        self.sp_ut  = _dspin(0.0, 10.0, self.cfg.params.ut,  step=0.01,  decimals=5)
        self.sp_ui  = _dspin(0.0, 10.0, self.cfg.params.ui,  step=0.01,  decimals=5)

        self.sp_a   = _dspin(0.0, 10.0, self.cfg.params.a,   step=0.01,  decimals=5)
        self.sp_b   = _dspin(0.0, 10.0, self.cfg.params.b,   step=0.01,  decimals=5)
        self.sp_g   = _dspin(0.0, 10.0, self.cfg.params.g,   step=0.001, decimals=5)

        self.sp_dch = _dspin(0.0, 10.0, self.cfg.params.deltach, step=0.001, decimals=5)
        self.sp_dim = _dspin(0.0, 10.0, self.cfg.params.deltaim, step=0.001, decimals=5)

        for label, w in [
            ("Dc (дифф. CAR-T):",       self.sp_Dc),
            ("Dt (дифф. опухоли):",     self.sp_Dt),
            ("Dch (дифф. химии):",      self.sp_Dch),
            ("Dim (дифф. иммуномод.):", self.sp_Dim),
            ("rc (рост CAR-T):",        self.sp_rc),
            ("rt (рост опухоли):",      self.sp_rt),
            ("hc (гибель CAR-T):",      self.sp_hc),
            ("ht (гибель опухоли):",    self.sp_ht),
            ("kct (убийство T):",       self.sp_kct),
            ("ki (инакт. CAR-T):",      self.sp_ki),
            ("uc (химия→CAR-T):",       self.sp_uc),
            ("ut (химия→T):",           self.sp_ut),
            ("ui (иммуномод.→I):",      self.sp_ui),
            ("a (распад I):",           self.sp_a),
            ("b (продукция I):",        self.sp_b),
            ("g (antigen escape):",     self.sp_g),
            ("deltach (распад Ch):",    self.sp_dch),
            ("deltaim (распад Im):",    self.sp_dim),
        ]:
            f_p.addRow(label, w)
        layout.addWidget(g_p)

        # ── 4. Метод и ГУ ─────────────────────────────────────
        g_m = QGroupBox("Метод и граничные условия")
        f_m = QFormLayout(g_m)

        self.cb_method = QComboBox()
        self.cb_method.addItems(["explicit_euler", "implicit_euler", "rk4"])
        self.cb_method.setCurrentText(self.cfg.therapy.method)

        self.cb_bc = QComboBox()
        self.cb_bc.addItems(["neumann", "dirichlet", "periodic"])
        self.cb_bc.setCurrentText(self.cfg.therapy.bc)

        f_m.addRow("Метод:", self.cb_method)
        f_m.addRow("ГУ:",    self.cb_bc)
        layout.addWidget(g_m)

        # ── 5. Терапия ────────────────────────────────────────
        g_t = QGroupBox("Терапия")
        f_t = QFormLayout(g_t)
        self.sp_day_cart   = _dspin(0.0, 1000, self.cfg.therapy.dose_day,   step=1.0, decimals=2)
        self.sp_day_chemo  = _dspin(0.0, 1000, self.cfg.therapy.day_chemo,  step=1.0, decimals=2)
        self.sp_day_immuno = _dspin(0.0, 1000, self.cfg.therapy.day_immuno, step=1.0, decimals=2)
        f_t.addRow("День CAR-T:",      self.sp_day_cart)
        f_t.addRow("День химии:",      self.sp_day_chemo)
        f_t.addRow("День иммуномод.:", self.sp_day_immuno)
        layout.addWidget(g_t)

        layout.addStretch()

        # ── Сигналы ───────────────────────────────────────────
        for w in [
            self.sp_T0, self.sp_sigma, self.sp_xc, self.sp_yc,
            self.sp_num_vessels, self.sp_vessel_seed,
            self.sp_Nx, self.sp_Ny, self.sp_Nt, self.sp_Tt,
            self.sp_Lx, self.sp_Ly,
            self.sp_Dc, self.sp_Dt, self.sp_Dch, self.sp_Dim,
            self.sp_rc, self.sp_rt, self.sp_hc, self.sp_ht,
            self.sp_kct, self.sp_ki,
            self.sp_uc, self.sp_ut, self.sp_ui,
            self.sp_a, self.sp_b, self.sp_g,
            self.sp_dch, self.sp_dim,
            self.sp_day_cart, self.sp_day_chemo, self.sp_day_immuno,
        ]:
            w.valueChanged.connect(self._emit)

        self.cb_bc.currentTextChanged.connect(self._emit)
        self.cb_method.currentTextChanged.connect(self._emit)

        # ★ ПРИНУДИТЕЛЬНАЯ СИНХРОНИЗАЦИЯ cfg ↔ виджеты при старте
        self._emit()

    def _emit(self):
        # НУ
        self.cfg.tumor.T0_volume = self.sp_T0.value()
        self.cfg.tumor.sigma     = self.sp_sigma.value()
        self.cfg.tumor.x_center  = self.sp_xc.value()
        self.cfg.tumor.y_center  = self.sp_yc.value()

        # сосуды
        self.cfg.vessels.count = self.sp_num_vessels.value()
        self.cfg.vessels.seed  = self.sp_vessel_seed.value()

        # сетка
        self.cfg.grid.Nx = self.sp_Nx.value()
        self.cfg.grid.Ny = self.sp_Ny.value()
        self.cfg.grid.Nt = self.sp_Nt.value()
        self.cfg.grid.Tt = self.sp_Tt.value()
        self.cfg.grid.Lx = self.sp_Lx.value()
        self.cfg.grid.Ly = self.sp_Ly.value()

        # коэффициенты
        p = self.cfg.params
        p.Dc  = self.sp_Dc.value();   p.Dt  = self.sp_Dt.value()
        p.Dch = self.sp_Dch.value();  p.Dim = self.sp_Dim.value()
        p.rc  = self.sp_rc.value();   p.rt  = self.sp_rt.value()
        p.hc  = self.sp_hc.value();   p.ht  = self.sp_ht.value()
        p.kct = self.sp_kct.value();  p.ki  = self.sp_ki.value()
        p.uc  = self.sp_uc.value();   p.ut  = self.sp_ut.value()
        p.ui  = self.sp_ui.value()
        p.a   = self.sp_a.value();    p.b   = self.sp_b.value()
        p.g   = self.sp_g.value()
        p.deltach = self.sp_dch.value()
        p.deltaim = self.sp_dim.value()

        # метод / ГУ
        self.cfg.therapy.method = self.cb_method.currentText()
        self.cfg.therapy.bc     = self.cb_bc.currentText()

        # терапия
        self.cfg.therapy.dose_day   = self.sp_day_cart.value()
        self.cfg.therapy.day_chemo  = self.sp_day_chemo.value()
        self.cfg.therapy.day_immuno = self.sp_day_immuno.value()

        self.configChanged.emit(self.cfg)

    def get_config(self):
        self._emit()
        return self.cfg


    def apply_coefficients(self, result: dict):
        """Обновляет поля коэффициентов значениями из оптимизации."""
        mapping = {
            "Dt":        self.sp_Dt,
            "rt":        self.sp_rt,
            "ht":        self.sp_ht,
            "a":         self.sp_a,
            "b":         self.sp_b,
            "g":         self.sp_g,
            "T0_volume": self.sp_T0,
        }
        for key, widget in mapping.items():
            if key in result:
                widget.setValue(float(result[key]))
        self._emit()   # синхронизирует cfg с новыми значениями

    def apply_coefficients(self, result: dict):
        """Обновляет поля коэффициентов значениями из оптимизации."""
        mapping = {
            "Dt":        self.sp_Dt,
            "rt":        self.sp_rt,
            "ht":        self.sp_ht,
            "a":         self.sp_a,
            "b":         self.sp_b,
            "g":         self.sp_g,
            "T0_volume": self.sp_T0,
        }
        for key, widget in mapping.items():
            if key in result:
                widget.setValue(float(result[key]))
        self._emit()