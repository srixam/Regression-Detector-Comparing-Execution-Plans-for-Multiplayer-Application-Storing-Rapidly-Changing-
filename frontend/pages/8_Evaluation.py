"""
Page 8: Evaluation & Benchmark Scorecard
Renders confusion matrix, precision/recall/F1 metrics, error analysis, and target scorecard.
"""

import streamlit as st
import os
import sys
import pandas as pd
import plotly.figure_factory as ff

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from experiments.evaluation import evaluation_engine

st.set_page_config(page_title="Evaluation | QueryGuard", page_icon="📈", layout="wide")

st.title("📈 Scientific Evaluation & Benchmark Scorecard")
st.caption("Empirical verification of regression detection accuracy, false rates, early warning, and reliability")

# Trigger Benchmark
if st.button("🔄 Re-run Empirical Benchmark (30 Scenarios)", type="primary"):
    with st.spinner("Executing controlled benchmark scenarios against labeled ground truth..."):
        st.session_state["benchmark_results"] = evaluation_engine.run_benchmark(num_scenarios=30)
        st.success("Benchmark completed successfully!")

if "benchmark_results" not in st.session_state:
    st.session_state["benchmark_results"] = evaluation_engine.run_benchmark(num_scenarios=30)

res = st.session_state["benchmark_results"]

# Primary Scorecard
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Precision", f"{res['precision'] * 100:.1f}%", "Target ≥ 85%")
m2.metric("Recall", f"{res['recall'] * 100:.1f}%", "Target ≥ 85%")
m3.metric("F1 Score", f"{res['f1_score'] * 100:.1f}%", "Target ≥ 85%")
m4.metric("Early-Warning Lead", f"{res['early_warning_seconds']:.0f} s", "Detected before user impact")
m5.metric("Detection Latency", f"{res['detection_latency_seconds']:.1f} s", "Target < 60s")

st.markdown("---")

# Confusion Matrix & Reliability Rates
c_col1, c_col2 = st.columns([1, 1])

with c_col1:
    st.subheader("Confusion Matrix")
    cm = res["confusion_matrix"]
    z = [[cm["TP"], cm["FN"]], [cm["FP"], cm["TN"]]]
    x = ["Predicted Regression", "Predicted Normal"]
    y = ["Actual Regression", "Actual Normal"]
    
    fig_cm = ff.create_annotated_heatmap(
        z, x=x, y=y, colorscale="Blues", showscale=True
    )
    fig_cm.update_layout(height=280, margin=dict(l=40, r=40, t=30, b=30))
    st.plotly_chart(fig_cm, use_container_width=True)

with c_col2:
    st.subheader("Pipeline Reliability Recovery")
    st.markdown(f"- **Duplicate Event Recovery Rate:** `{res['duplicate_recovery_rate'] * 100:.1f}%` (Target: 100.0%)")
    st.markdown(f"- **Late-Event Recovery Rate:** `{res['late_event_recovery_rate'] * 100:.1f}%` (Target: ≥ 95.0%)")
    st.markdown(f"- **Out-of-Order Recovery Rate:** `{res['out_of_order_recovery_rate'] * 100:.1f}%` (Target: ≥ 95.0%)")
    st.markdown(f"- **False Positive Rate (FPR):** `{res['false_positive_rate'] * 100:.1f}%`")
    st.markdown(f"- **False Negative Rate (FNR):** `{res['false_negative_rate'] * 100:.1f}%`")

st.markdown("---")

# Target vs Measured Scorecard
st.subheader("🎯 Project Target vs Measured Results")
df_targets = pd.DataFrame(res["target_vs_measured"])
st.dataframe(df_targets, use_container_width=True)

st.markdown("---")

# False Positive & False Negative Error Analysis
st.subheader("🔍 Error Analysis: False Positives & False Negatives")
tab_fp, tab_fn = st.tabs(["False Positives (FP)", "False Negatives (FN)"])

with tab_fp:
    fps = res.get("false_positive_details", [])
    if fps:
        for item in fps:
            st.warning(f"**Query:** `{item['query']}` | **Scenario:** `{item['scenario']}`")
            st.write(f"- **Predicted Result:** `{item['predicted_result']}` (Ground Truth: `{item['ground_truth']}`)")
            st.write(f"- **Root Reason:** {item['reason']}")
            st.write(f"- **Proposed Improvement:** {item['potential_improvement']}")
    else:
        st.success("No False Positives observed in this evaluation run (100% specificity).")

with tab_fn:
    fns = res.get("false_negative_details", [])
    if fns:
        for item in fns:
            st.error(f"**Query:** `{item['query']}` | **Scenario:** `{item['scenario']}`")
            st.write(f"- **Expected Result:** `{item['expected_result']}` (Detector Result: `{item['detector_result']}`)")
            st.write(f"- **Root Reason:** {item['reason']}")
            st.write(f"- **Proposed Improvement:** {item['potential_improvement']}")
    else:
        st.success("No False Negatives observed in this evaluation run (100% sensitivity).")

st.markdown("---")
st.subheader("Scenario-by-Scenario Evaluation Log")
df_scenarios = pd.DataFrame(res["scenarios_evaluated"])
st.dataframe(df_scenarios, use_container_width=True)
