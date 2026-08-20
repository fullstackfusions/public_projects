import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app import mock_engine as engine
from app.ui.theme import CSS
from app.ui import components as ui

st.set_page_config(page_title="Live Plan Copilot", page_icon="💬", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

RISK_LEVELS = ["conservative", "moderate", "aggressive"]


def init_state(prospect_key: str):
    prospect = engine.get_prospect(prospect_key)
    st.session_state.prospect_key = prospect_key
    st.session_state.transcript_idx = 0
    st.session_state.stage = "waiting"  # waiting -> extracted -> aligned -> generated
    st.session_state.proposal = None
    st.session_state.versions = []
    st.session_state.committed_age = prospect["retirement_age_default"]
    st.session_state.committed_risk = prospect["risk_tolerance_default"]
    st.session_state.advisor_approved = False
    st.session_state.ips = None
    st.session_state.rebalance = None
    st.session_state.elapsed = 0


def run_pipeline(trigger: str):
    prospect_key = st.session_state.prospect_key
    proposal = engine.build_proposal(
        prospect_key,
        st.session_state.committed_age,
        st.session_state.committed_risk,
        trigger,
    )
    st.session_state.proposal = proposal
    version_num = len(st.session_state.versions) + 1
    st.session_state.versions.append(
        {
            "version": version_num,
            "trigger": trigger,
            "asset_mix": proposal["asset_mix"],
            "risk_tolerance": proposal["risk_tolerance"],
            "retirement_age": proposal["retirement_age"],
        }
    )
    st.session_state.stage = "generated"


if "prospect_key" not in st.session_state:
    init_state("sarah")

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### 🎛️ Demo Controls")
    st.caption("Stands in for the live meeting-app audio feed + advisor console.")

    prospect_choice = st.selectbox(
        "Prospect in meeting",
        options=["sarah", "marcus"],
        format_func=lambda k: engine.get_prospect(k)["name"],
        index=["sarah", "marcus"].index(st.session_state.prospect_key),
    )
    if prospect_choice != st.session_state.prospect_key:
        init_state(prospect_choice)
        st.rerun()

    prospect = engine.get_prospect(st.session_state.prospect_key)
    total_lines = len(prospect["transcript"])

    st.divider()
    st.markdown("**Simulated live audio → transcript**")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("▶ Next line", width="stretch", disabled=st.session_state.transcript_idx >= total_lines):
            st.session_state.transcript_idx += 1
            st.rerun()
    with col_b:
        if st.button("⏮ Reset", width="stretch"):
            init_state(st.session_state.prospect_key)
            st.rerun()

    if st.session_state.transcript_idx >= total_lines and st.session_state.stage == "waiting":
        if st.button("🧠 Run Extract → Align → Generate", type="primary", width="stretch"):
            st.session_state.stage = "extracted"
            run_pipeline("initial generation")
            st.rerun()
    elif st.session_state.stage == "waiting":
        st.caption(f"Advance transcript ({st.session_state.transcript_idx}/{total_lines} lines) to unlock the AI run.")

    st.divider()
    st.caption("💡 In production this panel is a Webex/Zoom/Teams side-panel app; the transcript comes from the meeting platform's live audio/captions API, not manual upload.")

# ---------------------------------------------------------------- top bar
ui.meeting_bar(prospect["name"], prospect["meeting_platform"], f"⏱ {st.session_state.transcript_idx * 18}s elapsed")

completed = set()
active = None
if st.session_state.stage == "waiting":
    active = "Extract" if st.session_state.transcript_idx > 0 else None
elif st.session_state.stage in ("extracted", "aligned", "generated"):
    completed = {"Extract", "Align", "Generate"}
    active = "Refine" if len(st.session_state.versions) > 1 else "Generate"
ui.pipeline_strip(active, completed)

tab_live, tab_onboard, tab_rebalance = st.tabs(["🎙️ Live Session", "✅ One-Click Onboarding", "🔁 Day-One Rebalance"])

# ================================================================ TAB 1
with tab_live:
    left, right = st.columns([1, 1.15], gap="large")

    with left:
        st.subheader("Live Transcript")
        visible_lines = prospect["transcript"][: st.session_state.transcript_idx]
        if visible_lines:
            ui.transcript_box(visible_lines)
        else:
            st.info("Waiting for the meeting audio to start... click **Next line** in the sidebar to simulate live captions.")

        st.subheader("Extracted Insights")
        if st.session_state.stage == "waiting":
            st.caption("Populates once Extract has parsed the statements + transcript.")
        else:
            ep = prospect["extracted_profile"]
            c1, c2 = st.columns(2)
            with c1:
                ui.insight_card("Total Assets", f"${ep['total_assets']:,}")
            with c2:
                ui.insight_card("Liquid Cash", f"${ep['liquid_cash']:,}")
            ui.insight_card("Goals", " · ".join(ep["goals"]))
            ui.flag_badge(ep["concentration_flag"])

    with right:
        st.subheader("Generated Proposal")
        if st.session_state.proposal is None:
            st.caption("Run the pipeline from the sidebar to generate the first proposal.")
        else:
            proposal = st.session_state.proposal
            ui.version_chips(st.session_state.versions, proposal_version := len(st.session_state.versions))
            ui.narrative_block(proposal["narrative"])

            dc1, dc2 = st.columns([1, 1])
            with dc1:
                ui.asset_mix_donut(proposal["asset_mix"], title=f"{proposal['risk_label']} mix")
            with dc2:
                st.markdown("**Recommended funds**")
                for f in proposal["recommended_funds"]:
                    st.markdown(f"- {f}")
                st.markdown(f"**Target retirement age:** {proposal['retirement_age']}")

            st.markdown("##### 🎚️ Tweak live — Refine loop re-runs Align → Generate")
            new_age = st.slider("Retirement age", 45, 70, st.session_state.committed_age, key="age_slider")
            new_risk = st.select_slider(
                "Risk tolerance", options=RISK_LEVELS, value=st.session_state.committed_risk, key="risk_slider"
            )

            if new_age != st.session_state.committed_age or new_risk != st.session_state.committed_risk:
                trigger_bits = []
                if new_age != st.session_state.committed_age:
                    trigger_bits.append(f"retirement age changed to {new_age}")
                if new_risk != st.session_state.committed_risk:
                    trigger_bits.append(f"risk tolerance changed to {new_risk}")
                st.session_state.committed_age = new_age
                st.session_state.committed_risk = new_risk
                run_pipeline(" and ".join(trigger_bits))
                st.rerun()

            with st.expander(f"📜 Version history ({len(st.session_state.versions)} versions)"):
                for v in reversed(st.session_state.versions):
                    st.markdown(
                        f"**V{v['version']}** — _{v['trigger']}_ — "
                        f"{v['asset_mix']['equity_pct']}/{v['asset_mix']['fixed_income_pct']} mix, "
                        f"retire at {v['retirement_age']}, {v['risk_tolerance']}"
                    )

            st.divider()
            if not st.session_state.advisor_approved:
                if st.button("✅ Advisor Approves — Accept Proposal", type="primary"):
                    st.session_state.advisor_approved = True
                    st.session_state.ips = engine.build_ips(st.session_state.prospect_key, proposal)
                    st.rerun()
            else:
                st.success("Proposal accepted. Head to **One-Click Onboarding** →")

# ================================================================ TAB 2
with tab_onboard:
    st.subheader("Scenario 3 — One-Click Onboarding")
    if not st.session_state.advisor_approved:
        st.info("Waiting for advisor approval in the Live Session tab.")
    else:
        st.success("Proposal accepted — downstream automation triggered.")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.markdown("**🏦 Custodian Platform**")
            st.progress(100, text="Account open triggered")
        with p2:
            st.markdown("**📇 Client Source**")
            st.progress(100, text="Client record synced")
        with p3:
            st.markdown("**📄 IPS**")
            st.progress(100, text="Populated & compliance-flagged")

        st.markdown("##### Your Account Setup Summary")
        ips = st.session_state.ips
        mix = ips["target_asset_mix"]
        sc1, sc2 = st.columns([1, 1.3])
        with sc1:
            ui.asset_mix_donut(mix, title="Your target mix")
        with sc2:
            ui.insight_card("Account type", ips["account_type"])
            ui.insight_card("Goal this account is built for", ips["objective"])
            ui.insight_card("Review frequency", ips["review_frequency"])
            st.caption(
                f"This mix ({mix['equity_pct']}% equity / {mix['fixed_income_pct']}% fixed income) is now the "
                f"official record your account will be managed and reviewed against — no separate paperwork needed."
            )

        with st.expander("🔧 Technical / compliance record (advisor view — not for client screen-share)"):
            st.json(ips)

# ================================================================ TAB 3
with tab_rebalance:
    st.subheader("Scenario 4 — Day-One Portfolio Rebalance")
    if not st.session_state.advisor_approved:
        st.info("Available once the account is opened in One-Click Onboarding.")
    else:
        if st.session_state.rebalance is None:
            if st.button("💰 Simulate funds landing in new account"):
                st.session_state.rebalance = engine.build_rebalance(
                    st.session_state.prospect_key, st.session_state.proposal
                )
                st.rerun()
        else:
            rb = st.session_state.rebalance
            rc1, rc2 = st.columns(2)
            with rc1:
                ui.asset_mix_donut(rb["current_mix"], title="Current mix (as funded)")
            with rc2:
                ui.asset_mix_donut(rb["target_mix"], title="IPS target mix")
            st.caption(f"Cash position landing: ${rb['cash_position']:,}")

            st.markdown("##### Proposed Trades — Review & Submit")
            st.table(rb["trades"])
            if st.button("📤 Submit rebalance orders", type="primary"):
                st.success("Orders submitted for advisor sign-off. Lifecycle: proposal → funded → invested, complete.")
