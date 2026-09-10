"""
QueryGuard UI Theme & Executive Dashboard Components
Styles the application to match the OptiRoute/modern dark-slate executive dashboard aesthetic.
"""

import streamlit as st

def apply_custom_theme():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* Global Background and Typography */
        html, body, [class*="css"], .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #0b0f19 !important;
            color: #f8fafc;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #0b101d !important;
            border-right: 1px solid #1e293b !important;
            padding-top: 1rem;
        }

        /* Top Header Area */
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0 20px 0;
            border-bottom: 1px solid #1e293b;
            margin-bottom: 24px;
        }
        .dashboard-title {
            font-size: 1.65rem;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            letter-spacing: -0.02em;
        }
        .dashboard-subtitle {
            font-size: 0.88rem;
            color: #94a3b8;
            margin-top: 4px;
        }
        .header-badges {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .badge-active {
            background: rgba(16, 185, 129, 0.12);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 9999px;
            padding: 5px 14px;
            font-size: 0.82rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .badge-meta {
            color: #94a3b8;
            font-size: 0.85rem;
            font-weight: 500;
        }

        /* Executive Metric Cards (Exact match to uploaded UI) */
        .metric-card-container {
            background: #131b2e;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 18px 20px;
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }
        .metric-card-container:hover {
            border-color: #334155;
            transform: translateY(-1px);
        }
        .metric-icon-box {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            flex-shrink: 0;
        }
        .metric-content {
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .metric-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #94a3b8;
            font-weight: 600;
            margin-bottom: 2px;
        }
        .metric-value {
            font-size: 1.55rem;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
        }
        .metric-subtext {
            font-size: 0.75rem;
            color: #64748b;
            margin-top: 3px;
        }
        .subtext-highlight {
            color: #10b981;
            font-weight: 500;
        }
        .subtext-alert {
            color: #ef4444;
            font-weight: 500;
        }

        /* Card Colors */
        .icon-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.25); }
        .icon-green { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25); }
        .icon-purple { background: rgba(139, 92, 246, 0.15); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.25); }
        .icon-teal { background: rgba(20, 184, 166, 0.15); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.25); }
        .icon-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
        .icon-cyan { background: rgba(6, 182, 212, 0.15); color: #38bdf8; border: 1px solid rgba(6, 182, 212, 0.25); }
        .icon-rose { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.25); }

        /* Modern Table Card Container */
        .table-card {
            background: #131b2e;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        }
        .table-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .table-title {
            font-size: 1.05rem;
            font-weight: 600;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Primary Purple Gradient Button */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 10px 24px !important;
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            box-shadow: 0 4px 14px rgba(99, 102, 241, 0.35) !important;
            transition: all 0.2s ease !important;
        }
        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #4f46e5 0%, #4338ca 100%) !important;
            box-shadow: 0 6px 18px rgba(99, 102, 241, 0.45) !important;
            transform: translateY(-1px);
        }
        
        /* Secondary Button */
        .stButton > button:not([kind="primary"]) {
            background: #1e293b !important;
            color: #cbd5e1 !important;
            border: 1px solid #334155 !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.15s ease !important;
        }
        .stButton > button:not([kind="primary"]):hover {
            background: #273549 !important;
            color: white !important;
            border-color: #475569 !important;
        }

        /* Pill Badges in Tables */
        .pill-success {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }
        .pill-critical {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }
        .pill-warning {
            background: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }
        .pill-info {
            background: rgba(99, 102, 241, 0.15);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.78rem;
            font-weight: 600;
            display: inline-block;
        }

        /* Clean Streamlit Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #0b101d;
            padding: 6px;
            border-radius: 10px;
            border: 1px solid #1e293b;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 6px;
            color: #94a3b8;
            font-weight: 500;
            padding: 8px 16px;
        }
        .stTabs [aria-selected="true"] {
            background-color: #1e293b !important;
            color: #ffffff !important;
            font-weight: 600 !important;
        }
    </style>
    """, unsafe_allow_html=True)

def render_executive_header(title="QueryGuard | Multiplayer Query Regression Detector", subtitle="Operational Command Dashboard & Execution Plan Regression Solver"):
    from database.connection import db
    db_status = "PostgreSQL 16 Active" if db.is_postgres() else "Engine Active (SQLite/Telemetry)"
    st.markdown(f"""
    <div class="dashboard-header">
        <div>
            <h1 class="dashboard-title">{title}</h1>
            <div class="dashboard-subtitle">{subtitle}</div>
        </div>
        <div class="header-badges">
            <div class="badge-active">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#10b981;"></span>
                {db_status}
            </div>
            <div class="badge-meta">7 Queries | 10k Players | 100k Events</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_metric_card(icon, icon_style, label, value, subtext="", is_highlight=False, is_alert=False):
    sub_class = "subtext-highlight" if is_highlight else ("subtext-alert" if is_alert else "")
    return f"""
    <div class="metric-card-container">
        <div class="metric-icon-box {icon_style}">
            {icon}
        </div>
        <div class="metric-content">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtext {sub_class}">{subtext}</div>
        </div>
    </div>
    """
