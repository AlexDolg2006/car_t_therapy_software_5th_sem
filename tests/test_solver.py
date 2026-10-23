# tests/test_solver.py
from modules.solver import SolverRunner, SolverBackend
from shared.config_types import SimulationConfig
from pathlib import Path

class DummyBackend:
    def run(self, cfg, out_csv, on_progress=None, on_log=None):
        Path(out_csv).write_text("time,x,y,C,T,I,a_t,Ch,Im\n0,0,0,0,0,0,0,0,0\n")
        if on_progress: on_progress(100)
        return Path(out_csv)

def test_solver_runner_calls_backend(tmp_path):
    runner = SolverRunner(DummyBackend())
    csv = runner.run(SimulationConfig(), tmp_path / "out.csv")
    assert csv.exists()