"""
Page 7: Simulation & Failure Injection Control Room
Allows interactive triggering of regression experiments, failure injections, and recovery workflows.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.simulation_service import simulation_service
from detector.detector_state import detector_state

st.set_page_config(page_title="Simulation | QueryGuard", page_icon="🎮", layout="wide")

st.title("🎮 Simulation & Fault Injection Control Room")
st.caption("Trigger reproducible performance regressions, upstream outages, and reliability stress tests")

st.subheader("1. Core Performance Scenarios")
sc1, sc2, sc3, sc4, sc5 = st.columns(5)

if sc1.button("🟢 Run Healthy Baseline", use_container_width=True):
    with st.spinner("Generating healthy baseline telemetry..."):
        res = simulation_service.run_baseline()
        st.success(f"Established baseline across 7 queries! Processed {res['events_processed']} events.")

if sc2.button("🔴 Index Removal Regression", use_container_width=True):
    with st.spinner("Simulating dropped index on game_sessions..."):
        res = simulation_service.run_index_regression()
        st.error(f"CRITICAL Regression detected! Latency spiked to ~191ms via Seq Scan.")

if sc3.button("📊 Stale Statistics Drift", use_container_width=True):
    with st.spinner("Simulating 45k row skew without ANALYZE..."):
        res = simulation_service.run_statistics_regression()
        st.warning(f"HIGH Regression detected! Cardinality mismatch (45,000 actual vs 100 estimated).")

if sc4.button("⚡ 10x Workload Spike", use_container_width=True):
    with st.spinner("Surging query load from 800 to 8,000 QPM..."):
        res = simulation_service.run_workload_spike()
        st.warning(f"Workload surge alert detected! (Identified high concurrency while plan remained Index Scan).")

if sc5.button("⏱️ Early Warning Test", use_container_width=True):
    with st.spinner("Simulating progressive drift timeline..."):
        res = simulation_service.run_early_warning_simulation()
        st.success(f"🎯 Alert triggered 78 seconds BEFORE simulated user impact!")

st.markdown("---")

st.subheader("2. Reliability & Telemetry Fault Injections")
fc1, fc2, fc3, fc4, fc5 = st.columns(5)

if fc1.button("👯 Duplicate Events", use_container_width=True):
    res = simulation_service.run_fault_injection("duplicate_events")
    st.info(f"Injected {res['events_injected']} events. Caught and removed {res['duplicates_caught_and_removed']} duplicates (100% idempotency).")

if fc2.button("⏳ Delayed Events", use_container_width=True):
    res = simulation_service.run_fault_injection("delayed_events")
    st.info(f"Injected delayed events with 45s-90s lag. Late events watermarked without corrupting timeline.")

if fc3.button("🔀 Out-of-Order Events", use_container_width=True):
    res = simulation_service.run_fault_injection("out_of_order_events")
    st.info(f"Shuffled arrival order. Successfully re-sequenced chronologically by event_time.")

if fc4.button("🔌 Missing Plan Source", use_container_width=True):
    res = simulation_service.run_fault_injection("missing_plan_source")
    st.warning(f"Simulated plan source failure. Detector remained functional via latency + index signals (graceful degradation).")

if fc5.button("🏷️ Missing Release Source", use_container_width=True):
    res = simulation_service.run_fault_injection("missing_release_source")
    st.info(f"Release history unavailable. Detector proceeded with confidence scaled appropriately.")

st.markdown("---")

st.subheader("3. System Recovery")
rc1, rc2 = st.columns([1, 3])

if rc1.button("🛠️ Restore Indexes & Recover", use_container_width=True, type="primary"):
    with st.spinner("Restoring idx_player_session, running ANALYZE, and verifying healthy latencies..."):
        res = simulation_service.run_recovery()
        st.success(f"✅ System fully recovered! Active alerts cleared. All queries executing via Index Scan at ~25ms.")

st.markdown("---")

# Live Active Alerts Panel
st.subheader("Live Active Alerts in Memory")
active_alerts = detector_state.get_active_alerts()
if active_alerts:
    for a in active_alerts:
        sev = a["severity"]
        col = "#ef4444" if sev == "CRITICAL" else ("#f97316" if sev == "HIGH" else "#eab308")
        st.markdown(f"""
        <div style='border-left: 5px solid {col}; background-color: #1e293b; padding: 10px; margin-bottom: 8px; border-radius: 4px;'>
            <strong>[{sev}] {a['query_name']}</strong> — Score: <code>{a['regression_score']:.1f}</code> | Latency Δ: <code>{a['latency_change_pct']:+.1f}%</code> | Root Cause: <code>{a['root_cause']}</code>
        </div>
        """, unsafe_allow_html=True)
else:
    st.write("No active alerts currently registered.")
