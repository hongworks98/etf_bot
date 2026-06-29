"""engines/rotation — RotationSignalEngine package"""
from engines.rotation.rotation_signal_engine import RotationSignalEngine
from engines.rotation.data_models import (
    RotationInput, RotationEngineResult, RotationResult,
    RotationConfig, RotationStage, RotationStrength,
    RotationTiming, RotationSpeedLevel, ConvictionLevel,
    RotationAttribution, RotationDirection, CostAnalysis,
    DashboardData, AuxMarketData, TrendInputData,
)

__all__ = [
    "RotationSignalEngine",
    "RotationInput", "RotationEngineResult", "RotationResult",
    "RotationConfig", "RotationStage", "RotationStrength",
    "RotationTiming", "RotationSpeedLevel", "ConvictionLevel",
    "RotationAttribution", "RotationDirection", "CostAnalysis",
    "DashboardData", "AuxMarketData", "TrendInputData",
]
