"""Custom CSS to make the app read as an embedded meeting-app side panel
(Webex/Zoom/Teams), not a standalone data-entry tool."""

CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1180px;}

.meeting-bar {
    display: flex; align-items: center; justify-content: space-between;
    background: #1b1f23; color: #f4f6f8; border-radius: 10px;
    padding: 0.65rem 1rem; margin-bottom: 0.9rem; font-size: 0.92rem;
}
.meeting-bar .left { display: flex; align-items: center; gap: 0.6rem; }
.live-dot {
    height: 9px; width: 9px; border-radius: 50%; background: #ff4d4f;
    display: inline-block; animation: pulse 1.4s infinite;
}
@keyframes pulse { 0% {opacity:1;} 50% {opacity:0.3;} 100% {opacity:1;} }
.meeting-bar .platform-pill {
    background: rgba(255,255,255,0.12); padding: 2px 10px; border-radius: 999px;
    font-size: 0.78rem; margin-left: 0.4rem;
}

.pipeline-strip {
    display: flex; gap: 0.5rem; margin-bottom: 1rem;
}
.pipeline-node {
    flex: 1; text-align: center; padding: 0.55rem 0.4rem; border-radius: 8px;
    font-size: 0.82rem; font-weight: 600; border: 1px solid rgba(120,120,120,0.25);
    background: rgba(120,120,120,0.08); color: inherit;
}
.pipeline-node.active {
    background: #2563eb22; border-color: #2563eb; color: #2563eb;
}
.pipeline-node.done {
    background: #16a34a1a; border-color: #16a34a; color: #16a34a;
}

.transcript-box {
    border: 1px solid rgba(120,120,120,0.25); border-radius: 10px;
    padding: 0.7rem 0.9rem; max-height: 230px; overflow-y: auto;
    background: rgba(120,120,120,0.05); margin-bottom: 0.6rem;
}
.transcript-line { margin: 0.15rem 0; font-size: 0.88rem; line-height: 1.35; }
.speaker-advisor { color: #2563eb; font-weight: 600; }
.speaker-prospect { color: #b45309; font-weight: 600; }

.insight-card {
    border-radius: 10px; border: 1px solid rgba(120,120,120,0.22);
    padding: 0.75rem 0.9rem; margin-bottom: 0.55rem; background: rgba(120,120,120,0.04);
}
.insight-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.04em; opacity: 0.65; }
.insight-value { font-size: 1.02rem; font-weight: 600; margin-top: 0.1rem; }

.proposal-narrative {
    border-left: 3px solid #2563eb; padding: 0.6rem 0.9rem;
    background: rgba(37,99,235,0.06); border-radius: 0 8px 8px 0;
    font-size: 0.92rem; line-height: 1.5; margin-bottom: 0.8rem;
}

.version-chip {
    display: inline-block; padding: 1px 9px; border-radius: 999px;
    background: rgba(120,120,120,0.15); font-size: 0.75rem; margin-right: 0.35rem;
}
.version-chip.current { background: #2563eb; color: white; }

.badge-flag {
    display: inline-block; background: #f59e0b22; color: #b45309;
    padding: 2px 8px; border-radius: 6px; font-size: 0.78rem; font-weight: 600;
}
</style>
"""
