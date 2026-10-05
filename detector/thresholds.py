"""
Configurable Thresholds for QueryGuard Regression Detection
Allows tuning detection sensitivity, severity cutoffs, persistence windows, and scoring weights.
"""

import os

class DetectorConfig:
    def __init__(self):
        # Latency percentage increase thresholds
        self.latency_warning_pct = float(os.getenv("THRESHOLD_WARNING_PCT", "20.0"))
        self.latency_high_pct = float(os.getenv("THRESHOLD_HIGH_PCT", "50.0"))
        self.latency_critical_pct = float(os.getenv("THRESHOLD_CRITICAL_PCT", "100.0"))
        
        # Persistence requirement (number of consecutive windows)
        self.persistence_windows = int(os.getenv("THRESHOLD_PERSISTENCE_WINDOWS", "3"))
        self.warning_persistence_windows = int(os.getenv("THRESHOLD_WARNING_PERSISTENCE_WINDOWS", "2"))

        # Cardinality error threshold
        self.cardinality_error_threshold = float(os.getenv("CARDINALITY_ERROR_THRESHOLD", "2.0"))

        # Severity score ranges (0 - 100)
        self.score_warning_cutoff = 30.0
        self.score_high_cutoff = 60.0
        self.score_critical_cutoff = 80.0

        # Hybrid scoring component weights (Must sum to 100.0)
        self.weight_latency = float(os.getenv("WEIGHT_LATENCY", "35.0"))
        self.weight_plan = float(os.getenv("WEIGHT_PLAN", "30.0"))
        self.weight_cardinality = float(os.getenv("WEIGHT_CARDINALITY", "15.0"))
        self.weight_index = float(os.getenv("WEIGHT_INDEX", "10.0"))
        self.weight_release_workload = float(os.getenv("WEIGHT_RELEASE_WORKLOAD", "10.0"))

        # Target evaluation metrics
        self.target_recall = 0.85
        self.target_precision = 0.85
        self.target_f1 = 0.85
        self.target_detection_latency_seconds = 60.0
        self.target_duplicate_recovery = 1.00
        self.target_late_recovery = 0.95
        self.target_out_of_order_recovery = 0.95

    def to_dict(self):
        return {
            "latency_warning_pct": self.latency_warning_pct,
            "latency_high_pct": self.latency_high_pct,
            "latency_critical_pct": self.latency_critical_pct,
            "persistence_windows": self.persistence_windows,
            "warning_persistence_windows": self.warning_persistence_windows,
            "cardinality_error_threshold": self.cardinality_error_threshold,
            "weights": {
                "latency": self.weight_latency,
                "plan": self.weight_plan,
                "cardinality": self.weight_cardinality,
                "index": self.weight_index,
                "release_workload": self.weight_release_workload
            },
            "score_cutoffs": {
                "NORMAL": [0.0, self.score_warning_cutoff - 0.1],
                "WARNING": [self.score_warning_cutoff, self.score_high_cutoff - 0.1],
                "HIGH": [self.score_high_cutoff, self.score_critical_cutoff - 0.1],
                "CRITICAL": [self.score_critical_cutoff, 100.0]
            }
        }

config = DetectorConfig()
