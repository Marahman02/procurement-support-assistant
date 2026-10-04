"""Streamlit front end for the procurement support assistant."""

import os

import streamlit as st

import assistant
import retriever

st.set_page_config(page_title="Procurement Support Assistant")


@st.cache_resource
def load_index():
    """Build the ticket index once per server process."""
    return retriever.build_index()


def show_matches(matches):
    for m in matches:
        with st.expander(f"{m['id']}  (similarity {m['similarity']:.2f})"):
            st.text(m["text"])


# --- Sidebar: API key ---------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    entered_key = st.text_input("Anthropic API key", type="password")
    st.caption(
        "The key is used only for this session and is never stored. "
        "If left empty, the ANTHROPIC_API_KEY environment variable is used (for local runs)."
    )

api_key = entered_key or os.environ.get("ANTHROPIC_API_KEY")

# --- Main page ----------------------------------------------------------------
st.title("Procurement Support Assistant")
st.info("All data in this demo is synthetic.")

load_index()

incident = st.text_area("Describe the incident", height=150)

if st.button("Find similar cases", type="primary"):
    if not incident.strip():
        st.warning("Please describe the incident first.")
    else:
        with st.spinner("Searching past tickets..."):
            st.session_state.result = assistant.answer(incident, api_key=api_key)
        st.session_state.approved = False
        st.session_state.pop("report", None)

result = st.session_state.get("result")
if result is None:
    st.stop()

status = result["status"]

if status == "no_similar_cases":
    st.subheader("Closest tickets, none relevant")
    show_matches(result["matches"])
    st.stop()

if status == "error":
    st.error(result["message"])
    st.stop()

# status == "ok"
st.subheader("Similar tickets")
show_matches(result["matches"])

for warning in result.get("warnings", []):
    st.warning(warning)

if not result["root_causes"]:
    st.subheader("No applicable past cases")
    st.write(result["report_draft"])
    st.stop()

st.subheader("Root causes")
for rc in result["root_causes"]:
    cited = ", ".join(rc["cited_ids"]) or "no valid citation"
    st.markdown(f"- {rc['cause']}  \n  *Sources: {cited}*")

st.subheader("Resolution steps")
for i, step in enumerate(result["resolution_steps"], start=1):
    st.markdown(f"{i}. {step}")

st.subheader("Report draft")
approved = st.session_state.get("approved", False)
if "report" not in st.session_state:
    st.session_state.report = result["report_draft"]
st.text_area("Edit the report before approving", key="report", height=250, disabled=approved)

if approved:
    st.success("Status: Approved")
    st.download_button(
        "Download report",
        data=st.session_state.report,
        file_name="incident_report.txt",
        mime="text/plain",
    )
else:
    st.markdown("**Status: Draft, awaiting approval**")
    if st.button("Approve"):
        st.session_state.approved = True
        st.rerun()
