"""
Page 4: Plan Comparison
Interactive visual execution plan tree comparator and operator diff view.
"""

import streamlit as st
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from detector.detector_state import detector_state
from simulator.query_generator import QUERIES, get_all_queries
from simulator.plan_generator import get_baseline_plan, extract_plan_metrics
from detector.plan_comparator import plan_comparator

st.set_page_config(page_title="Plan Comparison | QueryGuard", page_icon="🌲", layout="wide")

st.title("🌲 Execution Plan Comparator")
st.caption("Side-by-side operator trees, cost comparisons, and buffer I/O changes")

query_options = {q["name"]: q["key"] for q in get_all_queries()}
selected_query_name = st.selectbox("Select Query Plan to Compare:", list(query_options.keys()))
selected_key = query_options[selected_query_name]
selected_meta = QUERIES[selected_key]
fp = selected_meta["fingerprint"]

b_plan = get_baseline_plan(selected_key)
c_plan = detector_state.get_plan(fp) or b_plan

diff = plan_comparator.compare_plans(b_plan, c_plan)
b_meta = diff["baseline_metrics"]
c_meta = diff["current_metrics"]

# Status Badge
if diff["plan_changed"]:
    st.error(f"⚠️ **Plan Regression Detected:** `{diff['diff_summary']}` | Cost Delta: `{diff['cost_change_pct']:+.1f}%`")
else:
    st.success("✅ **Plan Stable:** Current execution plan matches baseline operator tree.")

st.markdown("---")

# Visual Tree Diagram
col_tree1, col_tree2 = st.columns(2)

with col_tree1:
    st.subheader("Baseline Plan Operator Tree")
    b_tree = f"""
    ┌───────────────────────────────┐
    │ Operator:  {b_meta.get('node_type', 'N/A'):<18} │
    │ Relation:  {b_meta.get('relation', 'N/A'):<18} │
    │ Index:     {b_meta.get('index_name', 'none'):<18} │
    │ Cost:      {b_meta.get('startup_cost', 0):.2f} .. {b_meta.get('total_cost', 0):.2f}    │
    │ Buffers:   {b_meta.get('shared_hit_blocks', 0)} hit, {b_meta.get('shared_read_blocks', 0)} read │
    └───────────────────────────────┘
    """
    st.code(b_tree, language="text")

with col_tree2:
    st.subheader("Current Plan Operator Tree")
    c_tree = f"""
    ┌───────────────────────────────┐
    │ Operator:  {c_meta.get('node_type', 'N/A'):<18} │
    │ Relation:  {c_meta.get('relation', 'N/A'):<18} │
    │ Index:     {c_meta.get('index_name', 'none'):<18} │
    │ Cost:      {c_meta.get('startup_cost', 0):.2f} .. {c_meta.get('total_cost', 0):.2f}    │
    │ Buffers:   {c_meta.get('shared_hit_blocks', 0)} hit, {c_meta.get('shared_read_blocks', 0)} read │
    └───────────────────────────────┘
    """
    st.code(c_tree, language="text")

# Metric Delta Breakdown Table
st.subheader("Detailed Metric Comparison")
metrics_table = [
    {"Metric": "Node Type", "Baseline": b_meta.get("node_type"), "Current": c_meta.get("node_type"), "Diff": "Changed" if b_meta.get("node_type") != c_meta.get("node_type") else "Match"},
    {"Metric": "Target Relation", "Baseline": b_meta.get("relation"), "Current": c_meta.get("relation"), "Diff": "Match"},
    {"Metric": "Index Used", "Baseline": b_meta.get("index_name"), "Current": c_meta.get("index_name"), "Diff": "Dropped / Missing" if b_meta.get("index_name") != c_meta.get("index_name") else "Match"},
    {"Metric": "Total Cost", "Baseline": f"{b_meta.get('total_cost', 0):.2f}", "Current": f"{c_meta.get('total_cost', 0):.2f}", "Diff": f"{diff['cost_change_pct']:+.1f}%"},
    {"Metric": "Estimated Rows", "Baseline": f"{b_meta.get('estimated_rows', 0):,.0f}", "Current": f"{c_meta.get('estimated_rows', 0):,.0f}", "Diff": "Stable"},
    {"Metric": "Actual Rows", "Baseline": f"{b_meta.get('actual_rows', 0):,.0f}", "Current": f"{c_meta.get('actual_rows', 0):,.0f}", "Diff": "Stable"},
    {"Metric": "Shared Read Blocks (Disk)", "Baseline": b_meta.get("shared_read_blocks", 0), "Current": c_meta.get("shared_read_blocks", 0), "Diff": f"+{diff.get('read_blocks_diff', 0)} blocks"}
]

st.dataframe(pd.DataFrame(metrics_table), use_container_width=True)

st.markdown("---")
st.subheader("Human-Readable Plan Diff")
st.code(diff["human_readable_diff"], language="yaml")
