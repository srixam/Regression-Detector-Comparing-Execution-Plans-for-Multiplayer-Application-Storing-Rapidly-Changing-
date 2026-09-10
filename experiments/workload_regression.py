"""
Experiment 3: Workload Surge vs Plan Regression
Demonstrates:
1. Normal operation (~800 queries/min)
2. Traffic spike to ~8,000 queries/min (10x concurrency surge)
3. Latency increases due to queueing, but execution plans remain identical Index Scans
4. Proves QueryGuard detects WORKLOAD REGRESSION rather than falsely blaming execution plans
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.simulation_service import simulation_service
from detector.detector_state import detector_state
from simulator.query_generator import KEY_TO_FINGERPRINT

def run_experiment():
    print("=" * 70)
    print("EXPERIMENT 3: WORKLOAD SPIKE VS PLAN REGRESSION")
    print("=" * 70)

    print("\n[Phase 1] Establishing Baseline...")
    simulation_service.run_baseline()

    target_key = "get_active_sessions_on_server"
    target_fp = KEY_TO_FINGERPRINT[target_key]

    print("\n[Phase 2] Simulating Concurrency Spike (800 -> 8,000 QPM)...")
    res = simulation_service.run_workload_spike()

    alert = detector_state.get_alert_by_fingerprint(target_fp)
    if alert:
        print("\n[Phase 3] Alert Analysis:")
        print(f"  Query:            {alert['query_name']}")
        print(f"  Severity:         {alert['severity']}")
        print(f"  Plan Changed:     {alert['plan_changed']}")
        print(f"  Workload Changed: {alert['workload_changed']}")
        print(f"  Diagnosed Cause:  {alert['root_cause']}")
        print("\n  Evidence:")
        for idx, item in enumerate(alert["evidence_json"]["items"], 1):
            print(f"    {idx}. {item}")
        
        # Verify that QueryGuard did NOT falsely claim plan regression!
        assert alert["plan_changed"] is False, "Plan should not be flagged as changed!"
        assert "workload" in alert["root_cause"].lower() or "concurrency" in alert["root_cause"].lower(), "Should identify workload surge!"
        print("\n  SUCCESS: Detector correctly distinguished workload surge from plan regression!")
    else:
        print("  ERROR: No alert produced for workload surge!")

    print("\nExperiment 3 Completed Successfully.")

if __name__ == "__main__":
    run_experiment()
