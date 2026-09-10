"""
Page 2: Regression Alerts
Interactive table of active query regressions with severity badges, scores, and quick drill-downs.
"""

import streamlit as st
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from detector.detector_state import detector_state
from simulator.query_generator import QUERIES

st.set_page_config(page_title="Regression Alerts | QueryGuard", page_icon="🚨", layout="wide")

st.title("🚨 Query Regression Alerts")
st.caption("Active performance regressions identified before simulated user impact")

alerts = detector_state.get_active_alerts()

if not alerts:
    st.info("✅ No active query regressions detected. All queries are executing within healthy baseline parameters.")
    st.markdown("*(Tip: Navigate to the **7_Simulation** page to trigger an index removal or workload spike scenario!)*")
else:
    # Filter controls
    f_col1, f_col2 = st.columns([1, 3])
    with f_col1:
        severity_filter = st.selectbox("Filter by Severity", ["ALL", "CRITICAL", "HIGH", "WARNING"])
    
    filtered_alerts = alerts
    if severity_filter != "ALL":
        filtered_alerts = [a for a in alerts if a.get("severity") == severity_filter]

    st.write(f"Showing **{len(filtered_alerts)}** alert(s):")

    # Build display table
    table_rows = []
    for a in filtered_alerts:
        q_name = a.get("query_name", a.get("query_fingerprint"))
        table_rows.append({
            "Regression ID": a.get("regression_id"),
            "Severity": a.get("severity"),
            "Query": q_name,
            "Score": f"{a.get('regression_score', 0):.1f} / 100",
            "Latency Δ": f"{a.get('latency_change_pct', 0):+.1f}%",
            "Plan Changed": "⚠️ YES" if a.get("plan_changed") else "NO",
            "Index Changed": "🚨 MISSING" if a.get("index_changed") else "OK",
            "Release Correlated": "🔗 YES" if a.get("release_correlated") else "NO",
            "Confidence": f"{a.get('confidence', 0):.2f}",
            "Detected At": a.get("detected_at", "")[:19].replace("T", " ")
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True)

    st.markdown("---")
    st.subheader("🔍 Alert Quick View & Evidence")
    
    selected_id = st.selectbox("Select an alert to view immediate root cause & evidence:", [a["regression_id"] for a in filtered_alerts])
    selected_alert = next((a for a in filtered_alerts if a["regression_id"] == selected_id), None)

    if selected_alert:
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown(f"### {selected_alert['severity']} REGRESSION: {selected_alert['query_name']}")
            st.markdown(f"**Likely Root Cause:** `{selected_alert['root_cause']}`")
            st.markdown(f"**Detector Confidence:** `{selected_alert['confidence']}`")
            st.markdown(f"**Baseline p95:** `{selected_alert['baseline_p95']:.1f} ms` ➡️ **Current p95:** `{selected_alert['current_p95']:.1f} ms`")
            
            sub = selected_alert["evidence_json"].get("subscores", {})
            st.markdown("**Hybrid Signal Subscores:**")
            st.write(f"- Latency: `{sub.get('latency', 0):.2f}` | Plan: `{sub.get('plan', 0):.2f}` | Cardinality: `{sub.get('cardinality', 0):.2f}` | Index: `{sub.get('index', 0):.2f}`")

        with c2:
            st.markdown("#### Evidence Items:")
            for idx, item in enumerate(selected_alert["evidence_json"].get("items", []), 1):
                st.markdown(f"**{idx}.** {item}")

        st.info("👉 To inspect full execution plans, buffer reads, and SQL statements, open **3_Query_Investigation**.")
