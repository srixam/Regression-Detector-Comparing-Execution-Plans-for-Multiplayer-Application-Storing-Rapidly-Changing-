"""
Page 5: Release Timeline
Visualizes deployment history, schema/index changes, and temporal correlation with regressions.
"""

import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from simulator.release_generator import release_tracker
from detector.detector_state import detector_state

st.set_page_config(page_title="Release Timeline | QueryGuard", page_icon="🚀", layout="wide")

st.title("🚀 Release Deployment Timeline & Correlation")
st.caption("Tracking application releases, database migrations, and subsequent query regressions")

releases = release_tracker.get_all_releases()
active_alerts = detector_state.get_active_alerts()

st.subheader("Recent Deployments & Migrations")
rel_rows = []
for r in releases:
    rel_rows.append({
        "Release": r["version"],
        "Deployed At": r["deployed_at"][:19].replace("T", " "),
        "Description": r["description"],
        "Schema Change": "⚠️ YES" if r.get("schema_change") else "NO",
        "Index Change": "🚨 YES" if r.get("index_change") else "NO"
    })

st.dataframe(pd.DataFrame(rel_rows), use_container_width=True)

st.markdown("---")
st.subheader("🔗 Temporal Correlation Flow")

correlated_alert = next((a for a in active_alerts if a.get("release_correlated")), None)

if correlated_alert:
    rel_data = correlated_alert["evidence_json"].get("release", {})
    st.error(f"**Regression Correlated with Release {rel_data.get('version')}**")
    
    flow_col1, flow_col2, flow_col3, flow_col4 = st.columns(4)
    with flow_col1:
        st.markdown("**1. Release Deployed**")
        st.info(f"Version: `{rel_data.get('version')}`\nTime: `{rel_data.get('deployed_at')[:19]}`")
    with flow_col2:
        st.markdown("**2. Index Alteration**")
        st.warning("Schema/Index change flag: `TRUE`\n`idx_player_session` dropped")
    with flow_col3:
        st.markdown("**3. Performance Shift**")
        st.warning(f"Latency increased by `+{correlated_alert['latency_change_pct']:.1f}%`\nOperator: `Seq Scan`")
    with flow_col4:
        st.markdown("**4. Regression Detected**")
        st.error(f"Detection Time: `{correlated_alert['detected_at'][:19]}`\nLead: `{rel_data.get('formatted_delta')}`")

    st.markdown(f"> [!IMPORTANT]\n> **Diagnostic Correlation:** `{rel_data.get('statement')}`. The regression occurred {rel_data.get('formatted_delta')} after deployment.")
else:
    st.info("No active query regressions are temporally correlated with recent releases. Baseline remains healthy or regressions are workload-related.")
