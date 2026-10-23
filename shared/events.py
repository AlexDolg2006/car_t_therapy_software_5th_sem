from dataclasses import dataclass

@dataclass
class SimulationStarted:
    config_id: str

@dataclass
class SimulationProgress:
    config_id: str
    percent: int

@dataclass
class SimulationFinished:
    config_id: str
    csv_path: str

@dataclass
class SimulationFailed:
    config_id: str
    error: str