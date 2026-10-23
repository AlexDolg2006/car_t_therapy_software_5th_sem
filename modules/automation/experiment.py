from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import copy

import numpy as np
import pandas as pd

from shared.config_types import SimulationConfig
from .sweeps import Sweep, SWEEPABLE, set_nested


@dataclass
class SweepResult:
    param: str
    value: float
    csv: Path


def _aggregate_run(df: pd.DataFrame) -> dict:
    """Интегральные показатели эффективности терапии по одному прогону."""
    if df is None or df.empty:
        return {}
    xs = np.sort(df["x"].unique())
    ys = np.sort(df["y"].unique())
    dx = np.diff(xs).mean() if len(xs) > 1 else 1.0
    dy = np.diff(ys).mean() if len(ys) > 1 else 1.0
    cell = dx * dy

    vol = df.groupby("time")["T"].sum() * cell
    if vol.empty:
        return {}
    v0 = float(vol.iloc[0])
    vT = float(vol.iloc[-1])
    t  = vol.index.to_numpy(dtype=float)

    auc = float(np.trapz(vol.to_numpy(), t)) if len(t) > 1 else 0.0
    t_min = float(t[np.argmin(vol.to_numpy())]) if len(t) else 0.0

    v_half = 0.5 * v0
    below = t[vol.to_numpy() <= v_half]
    t_half = float(below[0]) if len(below) else float("nan")

    return {
        "V0":            v0,
        "V_final":       vT,
        "V_min":         float(vol.min()),
        "reduction_%":   (1.0 - vT / v0) * 100.0 if v0 > 0 else 0.0,
        "AUC_tumor":     auc,
        "t_Vmin":        t_min,
        "t_half":        t_half,
        "mean_C":        float(df["C"].mean()),
        "mean_I":        float(df["I"].mean()),
        "max_C":         float(df["C"].max()),
        "max_T":         float(df["T"].max()),
    }


class ExperimentManager:
    def __init__(self, runner, experiments_dir: Path):
        self.runner = runner
        self.root = Path(experiments_dir)

    def run_sweep(self,
                  base_cfg: SimulationConfig,
                  sweep: Sweep,
                  x_target: float,
                  y_target: float,
                  day_target: float,
                  on_progress=None,
                  on_log=None):
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        tag = f"{ts}_{sweep.param}"
        exp_dir = self.root / tag
        exp_dir.mkdir(parents=True, exist_ok=True)

        values = sweep.values()
        results: list[SweepResult] = []
        agg_rows: list[dict] = []

        for idx, val in enumerate(values):
            cfg = copy.deepcopy(base_cfg)
            set_nested(cfg, SWEEPABLE[sweep.param], val)

            out_csv = exp_dir / f"run_{idx:04d}.csv"
            if on_log:
                on_log(f"[{idx+1}/{len(values)}] {sweep.param} = {val:.5g} → {out_csv.name}")

            def _prog(p, _idx=idx, _n=len(values), _v=val):
                if on_progress:
                    on_progress(int(100 * (_idx + p/100) / _n),
                                f"{sweep.param} = {_v:.5g}")

            self.runner.run(cfg, out_csv,
                            on_progress=_prog if on_progress else None,
                            on_log=on_log)

            (exp_dir / f"run_{idx:04d}.params.json").write_text(
                json.dumps(cfg.to_dict(), indent=2)
            )
            results.append(SweepResult(param=sweep.param, value=val, csv=out_csv))

            # ★ интегральные метрики
            try:
                df_run = pd.read_csv(out_csv)
                agg = _aggregate_run(df_run)
                agg_rows.append({"value": val, **agg})
            except Exception as e:
                if on_log:
                    on_log(f"[warn] aggregate {out_csv.name}: {e}")

        summary = self._build_summary_point(
            results, sweep.param,
            x_target=x_target, y_target=y_target, day_target=day_target,
        )
        summary.to_csv(exp_dir / "summary.csv", index=False)

        # ★ сводная таблица эффективности
        if agg_rows:
            pd.DataFrame(agg_rows).sort_values("value").to_csv(
                exp_dir / "efficiency_summary.csv", index=False
            )

        (exp_dir / "view.json").write_text(json.dumps({
            "param": sweep.param,
            "x_target": x_target,
            "y_target": y_target,
            "day_target": day_target,
        }, indent=2))

        if on_progress:
            on_progress(100, "Готово")
        return exp_dir, summary

    def _build_summary_point(self, results, param,
                             x_target, y_target, day_target):
        rows = []
        for r in results:
            try:
                df = pd.read_csv(r.csv)
            except Exception:
                continue
            if df.empty:
                continue
            days = df["time"].unique()
            day_used = float(min(days, key=lambda d: abs(d - day_target)))
            d = df[df["time"] == day_used]
            if d.empty:
                continue
            d = d.copy()
            d["_dist"] = (d["x"] - x_target) ** 2 + (d["y"] - y_target) ** 2
            point = d.loc[d["_dist"].idxmin()]
            rows.append({
                "param": param,
                "value": r.value,
                "day_used": day_used,
                "x_point": float(point["x"]),
                "y_point": float(point["y"]),
                "C":   float(point["C"]),
                "T":   float(point["T"]),
                "I":   float(point["I"]),
                "a_t": float(point["a_t"]),
                "Ch":  float(point["Ch"]),
                "Im":  float(point["Im"]),
            })
        return pd.DataFrame(rows).sort_values("value")