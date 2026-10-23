from pathlib import Path
import subprocess, json, sys
from typing import Callable, Optional


class SolverRunner:
    def __init__(self, bin_dir: Path, data_dir: Path):
        self.bin_dir  = Path(bin_dir)
        self.data_dir = Path(data_dir)
        self.exe = self.bin_dir / "modeling_2d"

    def run(self, cfg, out_csv: Path,
            on_progress: Optional[Callable[[int], None]] = None,
            on_log: Optional[Callable[[str], None]] = None) -> Path:
        out_csv = Path(out_csv)
        out_csv.parent.mkdir(parents=True, exist_ok=True)

        flat = {
            "Nx": cfg.grid.Nx, "Ny": cfg.grid.Ny,
            "Lx": cfg.grid.Lx, "Ly": cfg.grid.Ly,
            "Nt": cfg.grid.Nt, "Tt": cfg.grid.Tt,
            "T0_volume": cfg.tumor.T0_volume,
            "sigma":     cfg.tumor.sigma,
            "x_center":  cfg.tumor.x_center,
            "y_center":  cfg.tumor.y_center,
            "method":    cfg.therapy.method,
            "bc":        cfg.therapy.bc,
            "day_cart":   cfg.therapy.dose_day,
            "day_chemo":  cfg.therapy.day_chemo,
            "day_immuno": cfg.therapy.day_immuno,
            "num_vessels": cfg.vessels.count,
            "vessel_seed": cfg.vessels.seed,
            **{k: getattr(cfg.params, k) for k in [
                "Dc", "Dt", "Dch", "Dim", "rc", "rt", "hc", "ht",
                "kct", "ki", "uc", "ut", "ui", "a", "b", "g",
                "deltach", "deltaim"
            ]}
        }

        params_file = out_csv.with_suffix(".params.json")
        params_file.write_text(json.dumps(flat, indent=2))

        if not self.exe.exists():
            raise FileNotFoundError(f"binary not found: {self.exe}")

        proc = subprocess.Popen(
            [str(self.exe),
             "--out",    str(out_csv),
             "--params", str(params_file),
             "--method", cfg.therapy.method],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
        
        full_log = []
        for line in proc.stdout:
            full_log.append(line)
            if on_log:
                on_log(line.rstrip())
            if on_progress and "Сохранён шаг" in line:
                try:
                    parts = line.split("из")
                    cur = int(parts[0].split()[-1])
                    tot = int(parts[1].split()[0])
                    on_progress(int(100 * cur / tot))
                except Exception:
                    pass
        proc.wait()
        
        if proc.returncode != 0:
            # Собираем последние 15 строк вывода для отображения ошибки
            err_msg = "".join(full_log[-15:]).strip()
            if not err_msg:
                err_msg = f"Моделирование завершилось с кодом {proc.returncode}"
            raise RuntimeError(err_msg)
            
        return out_csv