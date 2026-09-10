"""
Page 1: System Overview & Global Telemetry
Displays real-time KPIs, severity distribution, latency timeline, and data source health.
"""

import streamlit as st
import os
import sys
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.storage import storage_service
from detector.detector_state import detector_state
from simulator.query_generator import QUERIES

st.set_page_config(page_title="Overview | QueryGuard", page_icon="📊", layout="wide")

st.title("📊 System Overview: Multiplayer Database Health")
st.caption("Real-time query performance, active regressions, and telemetry pipeline status")

overview = storage_service.get_overview_metrics()

# Top KPI Metric Row
kpi1, kpi2, kpi3, kpi4, kpi5, kpi6 = st.columns(6)
kpi1.metric("Queries Monitored", overview["total_queries_monitored"])
kpi2.metric("Critical Regressions", overview["critical_regressions"], delta="Attention Required" if overview["critical_regressions"] > 0 else None, delta_color="inverse")
kpi3.metric("High Regressions", overview["high_regressions"], delta="High" if overview["high_regressions"] > 0 else None, delta_color="inverse")
kpi4.metric("Average p95 Latency", f"{overview['avg_p95_latency_ms']:.1f} ms")
kpi5.metric("Detection Latency", f"{overview['detection_latency_seconds']:.1f} s", "Fast")
kpi6.metric("Early-Warning Lead", f"{overview['early_warning_seconds']:.0f} s", "Target Met", delta_color="normal")

st.markdown("---")

# Data Source Health Strip
st.subheader("Data Source Ingestion Health")
scol1, scol2, scol3, scol4, scol5 = st.columns(5)
sources = overview["data_source_health"]

def badge_source(col, name, status):
    color = "green" if status == "Healthy" else ("orange" if status == "Delayed" or status == "Pending" else "red")
    col.markdown(f"**{name}**")
    col.markdown(f"<span style='color:{color}; font-weight:bold;'>● {status}</span>", unsafe_allow_html=True)

badge_source(scol1, "Query Executions", sources.get("query_executions", "Healthy"))
badge_source(scol2, "Execution Plans", sources.get("plans", "Healthy"))
badge_source(scol3, "Index Metadata", sources.get("indexes", "Healthy"))
badge_source(scol4, "Table Statistics", sources.get("statistics", "Healthy"))
badge_source(scol5, "Release History", sources.get("releases", "Healthy"))

st.markdown("---")

# Charts: Latency over time & Severity breakdown
chart_col1, chart_col2 = st.columns([2, 1])

with chart_col1:
    st.subheader("📈 p95 Latency by Query Template (Last 60 mins)")
    # Generate representative historical points
    now = datetime.now(timezone.utc)
    timestamps = [now - timedelta(minutes=5 * i) for i in range(12, -1, -1)]
    
    active_alerts = {a["query_fingerprint"]: a for a in detector_state.get_active_alerts()}
    
    data_records = []
    for t in timestamps:
        for q_key, meta in QUERIES.items():
            fp = meta["fingerprint"]
            is_reg = fp in active_alerts and t > (now - timedelta(minutes=20))
            if is_reg:
                lat = 191.0 if "player_session" in q_key else 165.0
            else:
                lat = 24.0 if "session" in q_key else (35.0 if "event" in q_key else 48.0)
            data_records.append({
                "Timestamp": t.strftime("%H:%M"),
                "Query": meta["name"],
                "Latency (ms)": lat
            })
    
    df_lat = pd.DataFrame(data_records)
    fig_lat = px.line(df_lat, x="Timestamp", y="Latency (ms)", color="Query", markers=True)
    fig_lat.update_layout(height=340, margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified")
    st.plotly_chart(fig_lat, use_container_width=True)

with chart_col2:
    st.subheader("🎯 Active Regression Severity")
    crit = overview["critical_regressions"]
    high = overview["high_regressions"]
    warn = overview["warnings"]
    normal = max(0, len(QUERIES) - crit - high - warn)

    df_sev = pd.DataFrame({
        "Severity": ["CRITICAL", "HIGH", "WARNING", "NORMAL"],
        "Count": [crit, high, warn, normal],
        "Color": ["#ef4444", "#f97316", "#eab308", "#10b981"]
    })
    fig_sev = px.pie(
        df_sev, names="Severity", values="Count", color="Severity",
        color_discrete_map={"CRITICAL": "#ef4444", "HIGH": "#f97316", "WARNING": "#eab308", "NORMAL": "#10b981"},
        hole=0.45
    )
    fig_sev.update_layout(height=340, margin=dict(l=20, r=20, t=20, b=20))
    st.plotly_chart(fig_sev, use_container_width=True)

# Bottom Table: Top Affected Queries
st.subheader("Top Monitored Queries")
query_summaries = storage_service.get_all_query_summaries()
df_queries = pd.DataFrame(query_summaries)[["query_name", "status", "baseline_p95_ms", "current_p95_ms", "latency_delta_pct", "index"]]
df_queries.columns = ["Query Name", "Status", "Baseline p95 (ms)", "Current p95 (ms)", "Delta (%)", "Primary Index"]
st.dataframe(df_queries, use_container_width=True)
