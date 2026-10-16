import os
from datetime import date, datetime

import streamlit as st
from dotenv import load_dotenv
from google import genai

from database import action, setup
from gemma_agent import get_action, reply


load_dotenv()
setup()
st.set_page_config(
    page_title="CampusCare",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    :root { --bg:#0b1220; --panel:#111b2d; --panel-2:#16243a; --text:#f1f5f9; --muted:#94a3b8; --line:#243550; --blue:#70b7ff; --green:#62dfaf; }
    html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
    .stApp { background:radial-gradient(circle at 80% 0%, #142b49 0, var(--bg) 35%); color:var(--text); }
    .block-container { max-width:1260px; padding:2.2rem 2.5rem 4rem; }
    h1,h2,h3 { font-family:'Space Grotesk',sans-serif; color:var(--text); letter-spacing:-.035em; }
    h1 { font-size:clamp(2.2rem,5vw,4.4rem); line-height:1.03; }
    h2 { margin-top:1.8rem; }
    .topbar { display:flex; justify-content:space-between; align-items:center; color:var(--muted); font-size:.85rem; margin-bottom:2.8rem; }
    .brand { color:var(--text); font:700 1.15rem 'Space Grotesk',sans-serif; }
    .brand span { color:var(--green); }
    .hero { max-width:850px; margin:0 auto 2rem; text-align:center; }
    .eyebrow { color:var(--green); text-transform:uppercase; letter-spacing:.18em; font-size:.7rem; font-weight:700; }
    .hero p { color:var(--muted); font-size:1.05rem; margin:0 auto 1.7rem; max-width:620px; }
    .status { display:inline-flex; align-items:center; gap:.45rem; border:1px solid var(--line); color:var(--muted); border-radius:99px; padding:.38rem .75rem; font-size:.76rem; }
    .dot { width:7px; height:7px; border-radius:50%; background:var(--green); box-shadow:0 0 10px var(--green); }
    .dot-off { background:#fbbf24; box-shadow:none; }
    .panel { background:rgba(17,27,45,.8); border:1px solid var(--line); border-radius:20px; padding:1.2rem; }
    .prompt-title { color:var(--muted); font-size:.8rem; font-weight:600; margin-bottom:.55rem; }
    .mini-card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:1rem; height:100%; }
    .mini-label { color:var(--muted); font-size:.75rem; }
    .mini-value { color:var(--text); font:600 1.4rem 'Space Grotesk',sans-serif; margin-top:.25rem; }
    .doctor-card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem; margin:.55rem 0; }
    .doctor-name { color:var(--text); font:600 1rem 'Space Grotesk',sans-serif; }
    .doctor-specialty { color:var(--blue); font-size:.82rem; font-weight:600; margin:.18rem 0 .55rem; }
    .doctor-meta { color:var(--muted); font-size:.78rem; }
    .info-card { border-left:3px solid var(--blue); background:var(--panel); border-radius:0 10px 10px 0; padding:.75rem 1rem; margin:.45rem 0; color:var(--muted); }
    .info-card strong { color:var(--text); }
    .stButton > button, .stFormSubmitButton > button { border-radius:10px; min-height:2.7rem; font-weight:700; }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background:var(--green); color:#071711; border:0; }
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stDateInput input, .stTimeInput input { background:var(--panel); color:var(--text); border-color:var(--line); }
    [data-testid="stTabs"] button { color:var(--muted); }
    [data-testid="stTabs"] button[aria-selected="true"] { color:var(--green); }
    [data-testid="stExpander"] { background:rgba(17,27,45,.65); border:1px solid var(--line); border-radius:14px; }
    [data-testid="stChatMessage"] { background:var(--panel); border:1px solid var(--line); border-radius:14px; }
    .stCaption, footer { color:var(--muted); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def gemma_client(user_key=None):
    # Checks the user input first, falls back to .env if empty
    key = user_key or os.getenv("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key else None


def ask_agent(question, client):
    try:
        task = get_action(client, question)
        result = action(task) if task.get("action") != "answer" else task
        return reply(client, question, result)
    except (RuntimeError, ValueError, KeyError) as error:
        return f"I couldn't complete that request: {error}"

# This adds the password box to the sidebar and sends it directly to your client builder
client = gemma_client(st.sidebar.text_input("Gemini API Key", type="password"))

today = date.today()
doctors_today = action({"action": "list_doctors", "appointment_date": today.isoformat()})["doctors"]
available_count = sum(doctor["available_on_date"] for doctor in doctors_today)
total_slots = sum(max(doctor["remaining_slots"], 0) for doctor in doctors_today)

st.markdown(
    '<div class="topbar"><div class="brand">Campus<span>Care</span> ✦</div>'
    '<div>College Medical Centre &nbsp;·&nbsp; 24/7 emergency support</div></div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="hero"><div class="eyebrow">Your private care companion</div>'
    '<h1>How can we help<br>you feel better?</h1>'
    '<p>Ask about care, availability, appointments, or centre information. '
    'Your assistant will guide you to the right next step.</p></div>',
    unsafe_allow_html=True,
)
status_class = "" if client else "dot-off"
status_text = "AI assistant online" if client else "AI assistant offline · add GEMINI_API_KEY"
st.markdown(
    f'<div style="text-align:center;margin-bottom:1.7rem"><span class="status"><span class="dot {status_class}"></span>{status_text}</span></div>',
    unsafe_allow_html=True,
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<div class="prompt-title">Try asking</div>', unsafe_allow_html=True)
prompt_cols = st.columns(4)
prompts = [
    "Which providers are available today?",
    "What are the centre hours?",
    "Help me book an appointment",
    "Who can I contact in an emergency?",
]
for column, prompt in zip(prompt_cols, prompts):
    with column:
        if st.button(prompt, use_container_width=True, disabled=not client):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.session_state.pending_question = prompt
st.markdown("</div>", unsafe_allow_html=True)

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

question = st.chat_input("Ask CampusCare anything...", disabled=not client)
question = question or st.session_state.pop("pending_question", None)
if question and client:
    if not st.session_state.chat_history or st.session_state.chat_history[-1]["content"] != question:
        st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)
    answer = ask_agent(question, client)
    with st.chat_message("assistant"):
        st.write(answer)
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

if not client:
    st.warning(
        "⚠️ **AI Assistant Offline**\n\n"
        "To talk to CampusCare, you need to provide your own Gemini API key:\n"
        "1. Open the **sidebar menu** by clicking the **`>`** arrow in the top-left corner of this page.\n"
        "2. Paste your key into the **Gemini API Key** field.\n"
        "3. Press Enter to activate the assistant!"
    )


stat_cols = st.columns(3)
for column, label, value in zip(
    stat_cols,
    ["Providers today", "Open appointment slots", "Emergency support"],
    [available_count, total_slots, "24 × 7"],
):
    with column:
        st.markdown(
            f'<div class="mini-card"><div class="mini-label">{label}</div><div class="mini-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

tab_care, tab_booking, tab_info = st.tabs(["Care directory", "Book an appointment", "Centre information"])

with tab_care:
    st.subheader("Care directory")
    selected_date = st.date_input("Check availability for", today, key="directory_date")
    result = action({"action": "list_doctors", "appointment_date": selected_date.isoformat()})
    for doctor in result["doctors"]:
        scheduled = "Scheduled" if doctor["available_on_date"] else "Not scheduled"
        left, right = st.columns([5, 1])
        with left:
            st.markdown(
                f'<div class="doctor-card"><div class="doctor-name">{doctor["name"]}</div>'
                f'<div class="doctor-specialty">{doctor["specialization"]}</div>'
                f'<div class="doctor-meta">{doctor["working_days"]} &nbsp;·&nbsp; {doctor["working_hours"]}'
                f' &nbsp;·&nbsp; {scheduled}</div></div>',
                unsafe_allow_html=True,
            )
        with right:
            st.metric("Slots", f'{max(doctor["remaining_slots"], 0)}/{doctor["daily_capacity"]}')

with tab_booking:
    st.subheader("Book an appointment")
    st.caption("Choose a provider and time. We will confirm your booking immediately.")
    doctors = action({"action": "list_doctors"})["doctors"]
    with st.form("booking"):
        doctor = st.selectbox("Provider", [d["name"] for d in doctors])
        person_col, email_col = st.columns(2)
        with person_col:
            patient = st.text_input("Your name")
        with email_col:
            email = st.text_input("Email address")
        date_col, time_col = st.columns(2)
        with date_col:
            appointment_date = st.date_input("Date", today, min_value=today)
        with time_col:
            appointment_time = st.time_input("Time")
        reason = st.text_area("Reason for visit", placeholder="A short description helps us prepare.")
        submitted = st.form_submit_button("Confirm appointment", type="primary", use_container_width=True)
    if submitted:
        if not patient.strip() or not email.strip() or not reason.strip():
            st.error("Please complete your name, email, and reason for visit.")
        else:
            result = action({
                "action": "book_appointment", "doctor_name": doctor,
                "patient_name": patient.strip(), "patient_email": email.strip(),
                "appointment_date": appointment_date.isoformat(),
                "appointment_time": appointment_time.strftime("%H:%M"),
                "reason": reason.strip(),
            })
            (st.success if "message" in result else st.error)(result.get("message") or result.get("error"))

with tab_info:
    st.subheader("Centre information")
    centre = action({"action": "centre_information"})
    info_cols = st.columns(2)
    with info_cols[0]:
        st.markdown("#### Hours")
        for item in centre["hours"]:
            st.markdown(
                f'<div class="info-card"><strong>{item["day_group"]}</strong><br>{item["timings"]}</div>',
                unsafe_allow_html=True,
            )
    with info_cols[1]:
        st.markdown("#### Contact directory")
        for item in centre["contacts"]:
            st.markdown(
                f'<div class="info-card"><strong>{item["contact_person"]}</strong><br>{item["phone"]}</div>',
                unsafe_allow_html=True,
            )

with st.expander("Staff tools", expanded=False):
    st.caption("Restricted operational controls. Public users do not need this section.")
    doctors = action({"action": "list_doctors"})["doctors"]
    with st.form("admin"):
        doctor = st.selectbox("Provider to update", [d["name"] for d in doctors])
        pin = st.text_input("Admin PIN", type="password")
        days = st.text_input("Working days")
        hours = st.text_input("Working hours")
        capacity = st.number_input("Daily capacity", min_value=1, value=10)
        submitted = st.form_submit_button("Update schedule", type="primary")
    if submitted:
        result = action({
            "action": "edit_doctor", "doctor_name": doctor, "admin_pin": pin,
            "working_days": days or None, "working_hours": hours or None,
            "daily_capacity": capacity,
        })
        (st.success if "message" in result else st.error)(result.get("message") or result.get("error"))

st.divider()
st.caption(
    f"CampusCare · Last refreshed {datetime.now().strftime('%d %b %Y, %I:%M %p')} "
    "· For emergencies, contact the centre directly."
)
