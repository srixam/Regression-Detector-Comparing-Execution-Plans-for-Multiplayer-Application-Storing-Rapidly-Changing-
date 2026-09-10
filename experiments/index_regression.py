"""
Experiment 1: Index Removal Regression & Recovery
Demonstrates:
1. Baseline with active index idx_player_session (Index Scan, p95 ~24ms)
2. Removal of index causing Seq Scan and p95 ~191ms
3. Detection of CRITICAL regression with evidence and plan diff
4. Index restoration and performance recovery
"""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.simulation_service import simulation_service
from detector.detector_state import detector_state
from simulator.query_generator import KEY_TO_FINGERPRINT

def run_experiment():
    print("=" * 70)
    print("EXPERIMENT 1: INDEX REMOVAL & RESTORATION REGRESSION")
    print("=" * 70)

    # Phase 1: Establish Healthy Baseline
    print("\n[Phase 1] Establishing Healthy Baseline...")
    base_res = simulation_service.run_baseline()
    print(f"  Processed {base_res['events_processed']} events. Baseline established.")

    target_key = "get_active_player_session"
    target_fp = KEY_TO_FINGERPRINT[target_key]

    # Phase 2: Trigger Index Regression
    print("\n[Phase 2] Simulating Index Removal (idx_player_session)...")
    reg_res = simulation_service.run_index_regression()
    print(f"  Processed {reg_res['events_processed']} events under degraded index conditions.")

    alert = detector_state.get_alert_by_fingerprint(target_fp)
    if alert:
        print("\n[Phase 3] Regression Alert Detected:")
        print(f"  Query:       {alert['query_name']} ({alert['query_fingerprint']})")
        print(f"  Severity:    {alert['severity']}")
        print(f"  Score:       {alert['regression_score']} / 100")
        print(f"  Confidence:  {alert['confidence']}")
        print(f"  Root Cause:  {alert['root_cause']}")
        print(f"  Baseline p95: {alert['baseline_p95']:.1f} ms -> Current p95: {alert['current_p95']:.1f} ms ({alert['latency_change_pct']:+.1f}%)")
        print("\n  Evidence Items:")
        for idx, item in enumerate(alert["evidence_json"]["items"], 1):
            print(f"    {idx}. {item}")
        print("\n  Plan Diff:")
        print("  " + "\n  ".join(alert["evidence_json"]["plan_diff"].split("\n")[:12]))
    else:
        print("  ERROR: No alert generated for index removal!")

    # Phase 4: Recovery
    print("\n[Phase 4] Restoring Index and Validating Recovery...")
    rec_res = simulation_service.run_recovery()
    print(f"  {rec_res['recovery_status']}")
    cleared_alert = detector_state.get_alert_by_fingerprint(target_fp)
    print(f"  Active Alert Cleared: {cleared_alert is None}")
    print("\nExperiment 1 Completed Successfully.")

if __name__ == "__main__":
    run_experiment()
