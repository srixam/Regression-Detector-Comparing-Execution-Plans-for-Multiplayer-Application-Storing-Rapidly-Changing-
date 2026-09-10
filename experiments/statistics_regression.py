"""
Experiment 2: Stale Optimizer Statistics & Cardinality Drift
Demonstrates:
1. Skewed data insertions without running ANALYZE
2. Massive cardinality estimation error (100 estimated vs 45,000 actual)
3. Suboptimal join strategy selection and query slowdown
4. Detection of Stale Statistics regression
5. Running ANALYZE and verifying performance recovery
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.simulation_service import simulation_service
from detector.detector_state import detector_state
from simulator.query_generator import KEY_TO_FINGERPRINT

def run_experiment():
    print("=" * 70)
    print("EXPERIMENT 2: STALE STATISTICS & CARDINALITY DRIFT")
    print("=" * 70)

    # Establish baseline
    print("\n[Phase 1] Establishing Baseline...")
    simulation_service.run_baseline()

    target_key = "region_leaderboard"
    target_fp = KEY_TO_FINGERPRINT[target_key]

    # Trigger Stale Statistics
    print("\n[Phase 2] Simulating Data Drift & Stale Statistics without ANALYZE...")
    res = simulation_service.run_statistics_regression()
    
    alert = detector_state.get_alert_by_fingerprint(target_fp)
    if alert:
        print("\n[Phase 3] Stale Statistics Alert Detected:")
        print(f"  Query:       {alert['query_name']}")
        print(f"  Severity:    {alert['severity']}")
        print(f"  Score:       {alert['regression_score']}")
        print(f"  Root Cause:  {alert['root_cause']}")
        print("\n  Evidence Items:")
        for idx, item in enumerate(alert["evidence_json"]["items"], 1):
            print(f"    {idx}. {item}")
    else:
        print("  ERROR: No alert generated for stale statistics!")

    # Recovery via ANALYZE
    print("\n[Phase 4] Simulating ANALYZE players Execution & Recovery...")
    rec_res = simulation_service.run_recovery()
    print(f"  {rec_res['recovery_status']}")
    print("\nExperiment 2 Completed Successfully.")

if __name__ == "__main__":
    run_experiment()
