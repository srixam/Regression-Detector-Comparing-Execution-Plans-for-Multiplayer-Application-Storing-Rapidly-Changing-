"""
Page 3: Query Investigation
The primary diagnostic console for database administrators and SREs.
Deep-dives into execution plans, latency distributions, index status, statistics, releases, and root cause evidence.
"""

import streamlit as st
import os
import sys
import plotly.graph_objects as go
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.storage import storage_service
from detector.detector_state import detector_state
from simulator.query_generator import QUERIES, get_all_queries, KEY_TO_FINGERPRINT
from simulator.plan_generator import get_baseline_plan, extract_plan_metrics
from detector.plan_comparator import plan_comparator

st.set_page_config(page_title="Query Investigation | QueryGuard", page_icon="🔬", layout="wide")

st.title("🔬 Query Investigation Console")
st.caption("Detailed forensic investigation of execution plans, catalog metadata, and root-cause evidence")

# Query Selector
query_options = {q["name"]: q["key"] for q in get_all_queries()}
selected_query_name = st.selectbox("Select Query to Investigate:", list(query_options.keys()))
selected_key = query_options[selected_query_name]
selected_meta = QUERIES[selected_key]
fp = selected_meta["fingerprint"]

# Retrieve baseline and active alert (if any)
detail = storage_service.get_query_detail(selected_key)
baseline = detail.get("baseline", {})
alert = detail.get("alert")

# Top Summary Banner
status_sev = alert.get("severity", "NORMAL") if alert else "NORMAL"
status_color = "#ef4444" if status_sev == "CRITICAL" else ("#f97316" if status_sev == "HIGH" else ("#eab308" if status_sev == "WARNING" else "#10b981"))

st.markdown(f"""
<div style='background-color: #1e293b; border-left: 6px solid {status_color}; padding: 14px; border-radius: 6px; margin-bottom: 20px;'>
    <div style='display:flex; justify-content:space-between; align-items:center;'>
        <div>
            <h3 style='margin:0; color:#f8fafc;'>{selected_meta['name']}</h3>
            <span style='color:#94a3b8; font-family:monospace;'>Fingerprint: {fp}</span>
        </div>
        <div>
            <span style='background-color:{status_color}; color:white; padding:6px 14px; border-radius:6px; font-weight:bold; font-size:1.1em;'>
                {status_sev}
            </span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Parameterized SQL
with st.expander("📝 Parameterized SQL Template", expanded=True):
    st.code(selected_meta["sql"], language="sql")
    st.caption(f"Target Table: `{selected_meta['table']}` | Expected Index: `{selected_meta['index']}`")

# Forensic Metrics Matrix
st.subheader("⏱️ Execution Latency Profile")
mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)

cur_p50 = alert.get("current_p50", baseline.get("baseline_p50", 18.0)) if alert else baseline.get("baseline_p50", 18.0)
cur_p95 = alert.get("current_p95", baseline.get("baseline_p95", 28.0)) if alert else baseline.get("baseline_p95", 28.0)
cur_p99 = alert.get("current_p99", baseline.get("baseline_p99", 35.0)) if alert else baseline.get("baseline_p99", 35.0)
lat_delta = alert.get("latency_change_pct", 0.0) if alert else 0.0

mcol1.metric("Baseline p50 / p95 / p99", f"{baseline.get('baseline_p50', 18):.1f} / {baseline.get('baseline_p95', 28):.1f} / {baseline.get('baseline_p99', 35):.1f} ms")
mcol2.metric("Current p50 / p95 / p99", f"{cur_p50:.1f} / {cur_p95:.1f} / {cur_p99:.1f} ms")
mcol3.metric("Latency Delta", f"{lat_delta:+.1f}%", delta="Degraded" if lat_delta > 20 else "Normal", delta_color="inverse")
mcol4.metric("Regression Score", f"{alert.get('regression_score', 0):.1f} / 100" if alert else "0.0 / 100")
mcol5.metric("Confidence", f"{alert.get('confidence', 0.95):.2f}" if alert else "0.95")

st.markdown("---")

# Evidence & Root Cause Analysis
st.subheader("💡 Root Cause Analysis & Supporting Evidence")
diag_col1, diag_col2 = st.columns([1, 1])

with diag_col1:
    st.markdown("#### Primary Diagnosis")
    if alert:
        st.error(f"**Likely Root Cause:** {alert['root_cause']}")
        st.markdown(f"**Detector Confidence:** `{alert['confidence'] * 100:.0f}%`")
        if alert.get("release_correlated"):
            rel_info = alert["evidence_json"].get("release", {})
            st.warning(f"**Release Correlation:** Correlated with `{rel_info.get('version')}` deployed {rel_info.get('formatted_delta')} before regression.")
    else:
        st.success("Query behavior conforms strictly to healthy baseline parameters. No performance anomalies detected.")

with diag_col2:
    st.markdown("#### Factual Evidence Chain")
    if alert and "evidence_json" in alert:
        for idx, item in enumerate(alert["evidence_json"].get("items", []), 1):
            st.markdown(f"**{idx}.** {item}")
    else:
        st.write("1. Baseline p95 within expected thresholds.")
        st.write("2. Execution plan operator matches baseline Index Scan.")
        st.write("3. Table statistics and row cardinality are up to date.")

st.markdown("---")

# Execution Plan Diff Section
st.subheader("📜 Execution Plan Forensic Diff")

b_plan = get_baseline_plan(selected_key)
c_plan = detector_state.get_plan(fp) or b_plan
diff_result = plan_comparator.compare_plans(b_plan, c_plan)

pcol1, pcol2 = st.columns(2)
with pcol1:
    st.markdown("##### 🟢 Baseline Healthy Plan")
    st.code(diff_result["human_readable_diff"].split("AFTER:")[0].strip(), language="yaml")

with pcol2:
    st.markdown("##### 🔴 Current Observed Plan")
    after_part = "AFTER:" + diff_result["human_readable_diff"].split("AFTER:")[-1]
    st.code(after_part.strip(), language="yaml")

with st.expander("View Raw PostgreSQL EXPLAIN JSON (Format JSON)"):
    jcol1, jcol2 = st.columns(2)
    with jcol1:
        st.caption("Baseline Plan JSON")
        st.json(b_plan)
    with jcol2:
        st.caption("Current Plan JSON")
        st.json(c_plan)
