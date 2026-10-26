import streamlit as st


def inject_theme():
    st.markdown(
        """
        <style>
        :root {
            --bg:#070B12;
            --surface:#0D131D;
            --surface-2:#101925;
            --surface-3:#142031;
            --border:rgba(148,163,184,.13);
            --border-strong:rgba(148,163,184,.22);
            --text:#F5F8FC;
            --muted:#8C9DB2;
            --accent:#5DD6C7;
            --accent-soft:rgba(93,214,199,.10);
            --blue:#7B8CFF;
            --success:#48C78E;
            --warning:#ECBC53;
            --danger:#EE657C;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(circle at 80% -15%, rgba(123,140,255,.07), transparent 29%),
                radial-gradient(circle at 10% 10%, rgba(93,214,199,.045), transparent 26%),
                var(--bg) !important;
            color:var(--text);
        }

        [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
        #MainMenu, footer, [data-testid="stSidebar"] {display:none !important;visibility:hidden !important;}

        .block-container {max-width:1480px;padding-top:.65rem;padding-bottom:2.5rem;}
        h1,h2,h3,h4,h5,h6,p,span,label,div {letter-spacing:0;}
        a {color:var(--accent);}

        .rta-brand-wrap {display:flex;align-items:center;gap:.72rem;min-height:50px;}
        .rta-mark {width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;
            color:#071018;font-weight:950;font-size:1rem;background:linear-gradient(135deg,#5DD6C7,#7B8CFF);
            box-shadow:0 8px 26px rgba(93,214,199,.11);}
        .rta-brand {font-size:1.02rem;font-weight:900;color:#fff;line-height:1;}
        .rta-brand-sub {font-size:.61rem;color:#70839A;margin-top:.22rem;letter-spacing:.09em;text-transform:uppercase;}
        .rta-top-rule {height:1px;background:var(--border);margin:.45rem 0 1.05rem;}

        .rta-page-heading {display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin:.15rem 0 1rem;}
        .rta-page-title {font-size:1.8rem;font-weight:900;line-height:1.12;color:#fff;}
        .rta-page-subtitle {font-size:.84rem;line-height:1.55;color:#8496AA;margin-top:.32rem;max-width:820px;}
        .rta-badge {display:inline-flex;border:1px solid var(--border);border-radius:999px;padding:.35rem .62rem;
            background:rgba(16,25,37,.82);font-size:.65rem;color:#B6C2D0;font-weight:800;letter-spacing:.055em;text-transform:uppercase;}
        .rta-badge-live::before {content:"";width:7px;height:7px;border-radius:999px;background:var(--success);margin-right:.45rem;
            box-shadow:0 0 0 4px rgba(72,199,142,.09);}

        .rta-section-heading {margin:1.15rem 0 .65rem;}
        .rta-section-title {font-size:1.08rem;font-weight:850;color:#F2F6FA;}
        .rta-section-subtitle {font-size:.76rem;color:#75879B;margin-top:.2rem;line-height:1.48;}

        .rta-metric-card, .rta-market-card, .rta-panel, .rta-empty-state {
            border:1px solid var(--border);background:linear-gradient(180deg,rgba(16,25,37,.93),rgba(11,18,28,.93));
            border-radius:15px;box-shadow:0 12px 38px rgba(0,0,0,.10);}
        .rta-metric-card {padding:.95rem 1rem;min-height:108px;}
        .rta-metric-label {font-size:.64rem;color:#74879D;font-weight:820;letter-spacing:.08em;text-transform:uppercase;}
        .rta-metric-value {font-size:1.36rem;color:#fff;font-weight:900;margin:.35rem 0 .18rem;line-height:1.12;}
        .rta-metric-meta {font-size:.71rem;color:#8193A8;line-height:1.38;}
        .rta-card-success {border-color:rgba(72,199,142,.24);}
        .rta-card-warning {border-color:rgba(236,188,83,.24);}
        .rta-card-danger {border-color:rgba(238,101,124,.24);}
        .rta-card-accent {border-color:rgba(93,214,199,.24);}

        .rta-market-card {padding:1rem 1.05rem;min-height:145px;}
        .rta-market-card-top {display:flex;align-items:flex-start;justify-content:space-between;gap:.5rem;}
        .rta-symbol {font-size:.95rem;font-weight:900;color:#F5F8FC;}
        .rta-asset-name {font-size:.68rem;color:#71849A;margin-top:.15rem;}
        .rta-market-price {font-size:1.55rem;font-weight:900;color:#fff;margin:1.05rem 0 .72rem;}
        .rta-market-footer {display:flex;align-items:center;justify-content:space-between;gap:.6rem;color:#7F91A6;font-size:.66rem;}
        .rta-risk-chip {font-size:.58rem;font-weight:850;letter-spacing:.06em;text-transform:uppercase;border-radius:999px;padding:.28rem .48rem;border:1px solid var(--border);}
        .rta-risk-low {color:#76D7AB;background:rgba(72,199,142,.07);border-color:rgba(72,199,142,.18);}
        .rta-risk-medium {color:#E9C872;background:rgba(236,188,83,.07);border-color:rgba(236,188,83,.18);}
        .rta-risk-high {color:#F08093;background:rgba(238,101,124,.07);border-color:rgba(238,101,124,.18);}
        .rta-dot {display:inline-block;width:6px;height:6px;border-radius:99px;margin-right:.28rem;}
        .rta-dot-success {background:var(--success);}.rta-dot-danger {background:var(--danger);}

        .rta-panel {padding:1.05rem 1.1rem;}
        .rta-signal-row {display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.82rem 0;border-bottom:1px solid rgba(148,163,184,.09);}
        .rta-signal-row:last-child {border-bottom:0;}
        .rta-signal-label {font-size:.75rem;color:#E5EBF2;font-weight:760;}
        .rta-signal-note {font-size:.64rem;color:#71849A;margin-top:.14rem;}
        .rta-signal-value {font-size:.82rem;color:#F5F8FC;font-weight:850;text-align:right;}

        .rta-login-cta {display:flex;align-items:center;justify-content:space-between;gap:1.5rem;border:1px solid rgba(93,214,199,.18);
            border-radius:16px;padding:1.05rem 1.15rem;background:linear-gradient(135deg,rgba(93,214,199,.055),rgba(123,140,255,.035));}
        .rta-login-cta-title {font-size:.95rem;font-weight:850;color:#F5F8FC;}
        .rta-login-cta-copy {font-size:.72rem;color:#8092A6;margin-top:.2rem;line-height:1.45;}
        .rta-login-cta-tag {font-size:.61rem;color:#80E0D5;font-weight:850;letter-spacing:.09em;border:1px solid rgba(93,214,199,.18);border-radius:999px;padding:.35rem .55rem;}

        .rta-empty-state {padding:1.25rem;text-align:center;}
        .rta-empty-title {font-size:.9rem;font-weight:800;color:#DDE5ED;}
        .rta-empty-copy {font-size:.71rem;color:#778A9F;margin-top:.25rem;}

        .rta-about-hero {border:1px solid var(--border);border-radius:18px;padding:1.5rem 1.55rem;background:linear-gradient(135deg,rgba(17,28,42,.96),rgba(10,17,27,.96));}
        .rta-about-kicker {font-size:.66rem;color:#6FDFD1;font-weight:850;letter-spacing:.1em;text-transform:uppercase;}
        .rta-about-title {font-size:2rem;color:#fff;font-weight:900;line-height:1.08;margin:.55rem 0 .6rem;}
        .rta-about-copy {font-size:.84rem;line-height:1.65;color:#899BAF;max-width:880px;}
        .rta-flow {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:.35rem;align-items:center;}
        .rta-flow-node {border:1px solid var(--border);border-radius:11px;padding:.72rem .35rem;text-align:center;color:#CBD5E0;background:rgba(16,25,37,.75);font-size:.63rem;font-weight:780;}
        .rta-flow-arrow {color:#455A70;text-align:center;font-size:.85rem;}
        .rta-note {border-left:3px solid var(--accent);background:rgba(93,214,199,.04);border-radius:0 12px 12px 0;padding:.72rem .85rem;color:#A4B2C1;font-size:.72rem;line-height:1.5;}

        .stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button, div[data-testid="stPopover"] > button {
            border-radius:9px !important;border:1px solid var(--border-strong) !important;min-height:2.35rem;font-weight:760 !important;box-shadow:none !important;transition:all .16s ease !important;}
        button[data-testid="stBaseButton-secondary"] {background:rgba(10,16,25,.62) !important;color:#AAB7C6 !important;}
        button[data-testid="stBaseButton-secondary"]:hover {border-color:rgba(93,214,199,.32) !important;color:#fff !important;background:rgba(16,25,37,.94) !important;}
        button[data-testid="stBaseButton-primary"] {background:linear-gradient(135deg,#5DD6C7,#7B8CFF) !important;color:#061019 !important;border-color:transparent !important;}

        div[data-testid="stMetric"] {background:rgba(13,20,31,.74);border:1px solid var(--border);border-radius:13px;padding:.76rem .86rem;}
        div[data-testid="stMetricLabel"] {color:#7F91A6;} div[data-testid="stMetricValue"] {color:#fff;}
        [data-testid="stDataFrame"] {border:1px solid var(--border);border-radius:13px;overflow:hidden;}
        [data-testid="stExpander"] {border:1px solid var(--border);border-radius:13px;background:rgba(13,20,31,.44);}
        [data-baseweb="tab-list"] {gap:.25rem;border-bottom:1px solid var(--border);}
        [data-baseweb="tab"] {border-radius:8px 8px 0 0;padding:.48rem .72rem;color:#8EA0B4;}
        [data-baseweb="select"] > div, input {background:#0D141F !important;}


        .rta-forecast-banner {display:grid;grid-template-columns:auto 1fr 1.7fr;gap:1rem;align-items:center;
            border:1px solid rgba(232,184,109,.28);border-radius:14px;padding:.82rem 1rem;margin:.2rem 0 .95rem;
            background:linear-gradient(90deg,rgba(232,184,109,.07),rgba(93,214,199,.045));font-size:.7rem;color:#D6DFE8;}
        .rta-live-pulse {display:inline-block;width:8px;height:8px;border-radius:99px;background:#48C78E;margin-right:.45rem;
            box-shadow:0 0 0 5px rgba(72,199,142,.08);}
        .rta-forecast-banner-main {font-size:.78rem;color:#F5F8FC;}
        .rta-forecast-banner-sub {font-size:.68rem;color:#8FA0B4;line-height:1.4;}
        .rta-legend-note {margin-top:.4rem;border-top:1px solid rgba(148,163,184,.08);padding-top:.65rem;color:#8798AC;font-size:.68rem;line-height:1.5;}
        .rta-review-note {margin-top:1rem;border:1px solid rgba(123,140,255,.22);border-radius:14px;padding:.85rem 1rem;
            background:rgba(123,140,255,.055);color:#AAB7C7;font-size:.72rem;line-height:1.55;}

        @media (max-width: 1050px) {
            .rta-page-title {font-size:1.5rem;}
            .rta-flow {grid-template-columns:1fr;}
            .rta-flow-arrow {transform:rotate(90deg);}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
