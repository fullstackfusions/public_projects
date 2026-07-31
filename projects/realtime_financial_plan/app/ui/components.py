import streamlit as st
import plotly.graph_objects as go

NODES = ["Extract", "Align", "Generate", "Refine"]


def meeting_bar(prospect_name: str, platform: str, elapsed_label: str):
    st.markdown(
        f"""
        <div class="meeting-bar">
            <div class="left">
                <span class="live-dot"></span>
                <b>Live</b> — {platform} · Financial Planning Review with {prospect_name}
                <span class="platform-pill">🎙️ Listening</span>
            </div>
            <div>{elapsed_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pipeline_strip(active_node: str | None, completed_nodes: set[str]):
    cells = []
    for node in NODES:
        cls = "pipeline-node"
        if node in completed_nodes and node != active_node:
            cls += " done"
        if node == active_node:
            cls += " active"
        cells.append(f'<div class="{cls}">{node}</div>')
    st.markdown(f'<div class="pipeline-strip">{"".join(cells)}</div>', unsafe_allow_html=True)


def transcript_box(lines: list[dict]):
    rows = []
    for line in lines:
        cls = "speaker-advisor" if line["speaker"] == "Advisor" else "speaker-prospect"
        rows.append(
            f'<div class="transcript-line"><span class="{cls}">{line["speaker"]}:</span> {line["text"]}</div>'
        )
    st.markdown(f'<div class="transcript-box">{"".join(rows)}</div>', unsafe_allow_html=True)


def insight_card(label: str, value: str):
    st.markdown(
        f"""<div class="insight-card">
            <div class="insight-label">{label}</div>
            <div class="insight-value">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def flag_badge(text: str):
    st.markdown(f'<span class="badge-flag">⚠ {text}</span>', unsafe_allow_html=True)


def narrative_block(text: str):
    st.markdown(f'<div class="proposal-narrative">{text}</div>', unsafe_allow_html=True)


def asset_mix_donut(mix: dict, title: str = ""):
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Equity", "Fixed Income"],
                values=[mix["equity_pct"], mix["fixed_income_pct"]],
                hole=0.62,
                marker=dict(colors=["#2563eb", "#94a3b8"]),
                textinfo="label+percent",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=230,
        showlegend=False,
        title=title,
        title_font_size=13,
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def version_chips(versions: list[dict], current_version: int):
    chips = []
    for v in versions:
        cls = "version-chip current" if v["version"] == current_version else "version-chip"
        chips.append(f'<span class="{cls}">V{v["version"]}</span>')
    st.markdown(" ".join(chips), unsafe_allow_html=True)
