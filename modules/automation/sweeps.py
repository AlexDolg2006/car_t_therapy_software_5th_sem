from dataclasses import dataclass
from typing import List, Any
import numpy as np


SWEEPABLE = {
    # коэффициенты модели
    "Dc":      ("params", "Dc"),
    "Dt":      ("params", "Dt"),
    "Dch":     ("params", "Dch"),
    "Dim":     ("params", "Dim"),
    "rc":      ("params", "rc"),
    "rt":      ("params", "rt"),
    "hc":      ("params", "hc"),
    "ht":      ("params", "ht"),
    "kct":     ("params", "kct"),
    "ki":      ("params", "ki"),
    "uc":      ("params", "uc"),
    "ut":      ("params", "ut"),
    "ui":      ("params", "ui"),
    "a":       ("params", "a"),
    "b":       ("params", "b"),
    "g":       ("params", "g"),
    "deltach": ("params", "deltach"),
    "deltaim": ("params", "deltaim"),
    # начальные условия
    "T0_volume": ("tumor", "T0_volume"),
    "sigma":     ("tumor", "sigma"),
    # сетка
    "Nx":  ("grid", "Nx"),
    "Ny":  ("grid", "Ny"),
    "Nt":  ("grid", "Nt"),
    "Tt":  ("grid", "Tt"),
    # терапия
    "day_cart":   ("therapy", "dose_day"),
    "day_chemo":  ("therapy", "day_chemo"),
    "day_immuno": ("therapy", "day_immuno"),
}


@dataclass
class Sweep:
    param: str
    start: float
    stop:  float
    step:  float

    def values(self) -> List[float]:
        n = int(round((self.stop - self.start) / self.step)) + 1
        return list(np.linspace(self.start, self.stop, n))


def set_nested(obj, path: tuple, value: Any):
    section, field = path
    setattr(getattr(obj, section), field, value)