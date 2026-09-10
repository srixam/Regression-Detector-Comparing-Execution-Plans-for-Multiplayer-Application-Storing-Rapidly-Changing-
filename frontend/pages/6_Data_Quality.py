"""
Page 6: Data Quality & Pipeline Health
Monitors telemetry ingestion reliability, deduplication rates, late-event tracking, and missing sources.
"""

import streamlit as st
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from pipeline.data_quality import data_quality_tracker

st.set_page_config(page_title="Data Quality | QueryGuard", page_icon="🧹", layout="wide")

st.title("🧹 Telemetry Pipeline & Data Quality Monitor")
st.caption("Tracking event reliability, deduplication, chronological reordering, and missing sources")

dq = data_quality_tracker.get_quality_report()

# Top KPIs
k1, k2, k3, k4 = st.columns(4)
k1.metric("Overall Health Score", f"{dq['overall_health_score']}%", delta="Degraded" if dq['overall_health_score'] < 85 else "Healthy")
k2.metric("Duplicates Dropped", f"{dq['duplicates_removed']}", delta="100% Idempotent")
k3.metric("Late Events Watermarked", f"{dq['late_events_count']}")
k4.metric("Out-of-Order Reordered", f"{dq['out_of_order_count']}")

st.markdown("---")

# Upstream Source Status Cards
st.subheader("Upstream Telemetry Source Health")
c1, c2, c3, c4, c5 = st.columns(5)

def render_source_card(col, name, status):
    col.markdown(f"""
    <div style='background-color:#1e293b; border-radius:6px; padding:12px; border: 1px solid #334155; text-align:center;'>
        <h4 style='margin:0; color:#f8fafc;'>{name}</h4>
        <p style='margin:5px 0 0 0; font-weight:bold; color:{"#10b981" if status=="Healthy" else ("#eab308" if status in ["Delayed", "Pending"] else "#ef4444")};'>
            ● {status}
        </p>
    </div>
    """, unsafe_allow_html=True)

sources = dq.get("sources", {})
render_source_card(c1, "Query Executions", sources.get("query_executions", "Healthy"))
render_source_card(c2, "Execution Plans", sources.get("plans", "Healthy"))
render_source_card(c3, "Index Metadata", sources.get("indexes", "Healthy"))
render_source_card(c4, "Table Statistics", sources.get("statistics", "Healthy"))
render_source_card(c5, "Release History", sources.get("releases", "Healthy"))

st.markdown("---")

# Event Processing Counters
st.subheader("Pipeline Reliability Metrics")
rcol1, rcol2 = st.columns(2)

with rcol1:
    st.markdown("""
    #### 🛡️ Deduplication & Ordering Guarantees
    - **Deduplication:** Hash-based idempotency key cache eliminates double-counting without state corruption.
    - **Late Arrival:** Events arriving beyond the configured watermark are tracked to prevent skewing current operational percentiles.
    - **Out-of-Order:** Events arriving out of chronological order are re-sequenced by `event_time` in sliding memory buffers.
    """)

with rcol2:
    st.markdown("#### 📊 Event Volume Breakdown")
    st.write(f"- **Total Events Processed:** `{dq['total_events']:,}`")
    st.write(f"- **Duplicates Received:** `{dq['duplicates_received']:,}`")
    st.write(f"- **Duplicates Removed:** `{dq['duplicates_removed']:,}`")
    st.write(f"- **Late Events Flagged:** `{dq['late_events_count']:,}`")
    st.write(f"- **Out-of-Order Shuffles Reconstructed:** `{dq['out_of_order_count']:,}`")
    st.write(f"- **Last Event Ingestion Timestamp:** `{dq['last_event_time'][:19]}`")

st.markdown("---")
st.info("💡 **Graceful Degradation:** When execution plans or release history sources are offline, QueryGuard re-weights available signals (e.g. latency + cardinality), reduces confidence appropriately, and continues detecting regressions rather than crashing.")
