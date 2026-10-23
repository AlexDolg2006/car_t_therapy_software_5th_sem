from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass
class GridConfig:
    Nx: int = 100; Ny: int = 100
    Lx: float = 100.0; Ly: float = 100.0
    Nt: int = 2000; Tt: float = 400.0


@dataclass
class TumorConfig:
    T0_volume: float = 50.0
    sigma: float = 0.003
    x_center: float = 50.0
    y_center: float = 50.0


@dataclass
class TherapyConfig:
    method: Literal["explicit_euler", "implicit_euler", "rk4"] = "explicit_euler"
    bc: Literal["neumann", "dirichlet", "periodic"] = "neumann"
    dose_day: float = 0.0
    day_chemo: float = 30.0
    day_immuno: float = 30.0


@dataclass
class ModelParams:
    Dc: float = 0.05;   Dt: float = 0.00005
    Dch: float = 0.015; Dim: float = 0.015
    rc: float = 0.5;    rt: float = 0.1
    hc: float = 0.001;  ht: float = 0.004
    kct: float = 0.64;  ki: float = 0.03
    uc: float = 0.1;    ut: float = 0.10; ui: float = 0.2
    a: float = 0.1;     b: float = 0.1;  g: float = 0.05
    deltach: float = 0.04; deltaim: float = 0.03


@dataclass
class VesselsConfig:
    count: int = 33
    seed: int = 42


@dataclass
class SimulationConfig:
    grid: GridConfig = field(default_factory=GridConfig)
    tumor: TumorConfig = field(default_factory=TumorConfig)
    therapy: TherapyConfig = field(default_factory=TherapyConfig)
    params: ModelParams = field(default_factory=ModelParams)
    vessels: VesselsConfig = field(default_factory=VesselsConfig)

    def to_dict(self):
        return asdict(self)

    def to_dict_flat(self):
        return {
            "Nx": self.grid.Nx, "Ny": self.grid.Ny,
            "Lx": self.grid.Lx, "Ly": self.grid.Ly,
            "Nt": self.grid.Nt, "Tt": self.grid.Tt,
            "T0_volume": self.tumor.T0_volume,
            "sigma":     self.tumor.sigma,
            "x_center":  self.tumor.x_center,
            "y_center":  self.tumor.y_center,
            "method":    self.therapy.method,
            "bc":        self.therapy.bc,
            "day_cart":   self.therapy.dose_day,
            "day_chemo":  self.therapy.day_chemo,
            "day_immuno": self.therapy.day_immuno,
            "num_vessels": self.vessels.count,
            "vessel_seed": self.vessels.seed,
            **{k: getattr(self.params, k) for k in [
                "Dc", "Dt", "Dch", "Dim", "rc", "rt", "hc", "ht",
                "kct", "ki", "uc", "ut", "ui", "a", "b", "g",
                "deltach", "deltaim"
            ]}
        }