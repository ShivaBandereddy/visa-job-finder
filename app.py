import re
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Visa Job Finder", page_icon="🌍", layout="wide")

st.markdown(
    """
<style>
.hero {background: linear-gradient(135deg, #4F46E5, #7C3AED); padding: 28px 32px; border-radius: 16px; margin-bottom: 24px;}
.hero h1 {color: white; margin: 0; font-size: 2rem;}
.hero p {color: #E0E7FF; margin: 8px 0 0 0; font-size: 1.05rem;}
</style>
<div class="hero">
<h1>🌍 Visa Sponsorship Job Finder</h1>
<p>Find HR and recruitment jobs in Europe, check sponsors, match your CV and track applications.</p>
</div>
""",
    unsafe_allow_html=True,
)

if "tracker" not in st.session_state:
    st.session_state["tracker"] = pd.DataFrame(
        columns=["Title", "Company", "Location", "Link", "Status"]
    )

countries = [
    "United Kingdom",
    "Ireland",
    "Netherlands",
    "Poland",
    "Portugal",
    "Malta",
    "Sweden",
    "Norway",
]

VISA_WORDS = ["visa sponsor", "sponsorship", "sponsor", "relocation", "relocate", "work permit", "blue card"]

STATUSES = ["Saved", "Applied", "Interview", "Offer", "Rejected"]

GEMINI_MODEL = "gemini-3.5-flash-lite"


def clean_text(text):
    return re.sub(r"<[^>]+>", "", text or "")


def normalize(name):
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    words = [w for w in name.split() if w not in ("ltd", "limited", "plc", "llp", "inc", "llc")]
    return " ".join(words)


def mentions_visa(job):
    text = (job.get("title", "") + " " + clean_text(job.get("snippet", ""))).lower()
    return any(word in text for word in VISA_WORDS)


def sponsor_routes(job, sponsors):
    return sponsors.get(normalize(job.get("company", "")))


@st.cache_data
def load_uk_sponsors():
    try:
        df = pd.read_csv("uk_sponsors.csv", encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv("uk_sponsors.csv", encoding="latin-1")
    df["key"] = df["Organisation Name"].apply(normalize)
    routes = df.groupby("key")["Route"].apply(lambda r: ", ".join(sorted(set(r.dropna()))))
    return routes.to_dict()


@st.cache_data(ttl=3600)
def fetch_jobs(api_key, keyword, location):
    url = f"https://jooble.org/api/{api_key}"
    payload = {"keywords": keyword, "location": location}
    response = requests.post(url, json=payload, timeout=20)
    if response.status_code != 200:
        return response.status_code, []
    return 200, response.json().get("jobs", [])


def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"x-goog-api-key": st.secrets["GEMINI_API_KEY"]}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, headers=headers, json=body, timeout=60)
    if response.status_code != 200:
        return f"Gemini error {response.status_code}: {response.text[:200]}"
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def make_prompt(cv, job):
    return f"""You are an experienced HR recruiter. Compare this CV with this job.
Reply exactly in this format:
Score: <number from 0 to 100>
Reasons:
- three short reasons why the CV fits
Gaps:
- two short missing skills or requirements

CV:
{cv[:4000]}

Job title: {job.get("title", "")}
Company: {job.get("company", "")}
Job description: {clean_text(job.get("snippet", ""))}
"""


def make_letter_prompt(cv, job):
    return f"""You are an experienced HR professional writing a job application.
Write a tailored cover letter in English, maximum 250 words, professional but warm.
Use ONLY facts that appear in the CV. Do not invent skills, employers or numbers.
Start with "Dear Hiring Manager," and end with "Kind regards,\\n[Your Name]".

CV:
{cv[:4000]}

Job title: {job.get("title", "")}
Company: {job.get("company", "")}
Job description: {clean_text(job.get("snippet", ""))}
"""


# ---------- Sidebar: search filters ----------
st.sidebar.header("🔎 Search filters")

country = st.sidebar.selectbox("Country", countries)

keyword = st.sidebar.selectbox(
    "Role keyword",
    ["HR", "Recruiter", "Talent Acquisition", "People Operations", "Payroll", "Onboarding", "HR Manager"],
)

city = st.sidebar.text_input("City (optional)", "", placeholder="e.g. Amsterdam, Edinburgh")

only_visa = st.sidebar.checkbox("Only visa / relocation jobs")
only_sponsor = st.sidebar.checkbox("Only licensed sponsors (UK only)")

search_clicked = st.sidebar.button("Search jobs", type="primary", use_container_width=True)

st.sidebar.caption("Free API limits apply. Use Match score and Cover letter only on jobs you like.")

# ---------- Tabs ----------
tab_jobs, tab_tracker = st.tabs(["🔎 Job results", "📋 My tracker"])

with tab_jobs:
    with st.expander("📄 Your CV (used for match score and cover letter)", expanded=True):
        cv_text = st.text_area(
            "Paste your CV text here (remove phone, address and email first)",
            height=180,
        )
        if cv_text:
            st.caption(f"CV loaded: {len(cv_text.split())} words")

    # ----- Search -----
    if search_clicked:
        location = city if city else country
        status, jobs = fetch_jobs(st.secrets["JOOBLE_API_KEY"], keyword, location)

        if status != 200:
            st.error(f"Error {status}. Check your key in Secrets.")
        else:
            if only_sponsor:
                if country != "United Kingdom":
                    st.info("Sponsor check works for the UK only.")
                else:
                    sponsors_now = load_uk_sponsors()
                    jobs = [job for job in jobs if sponsor_routes(job, sponsors_now)]

            if only_visa:
                jobs = [job for job in jobs if mentions_visa(job)]

            st.session_state["jobs"] = jobs
            st.session_state["searched_country"] = country
            st.session_state["scores"] = {}
            st.session_state["letters"] = {}

    # ----- Results -----
    if "jobs" not in st.session_state:
        st.info("👈 Choose a country and role in the sidebar, then click **Search jobs**.")
    elif len(st.session_state["jobs"]) == 0:
        st.warning("No jobs matched. Try another city, or turn off the filters.")
    else:
        jobs = st.session_state["jobs"]
        sponsors = load_uk_sponsors() if st.session_state["searched_country"] == "United Kingdom" else {}

        st.subheader(f"{len(jobs)} jobs found")

        for i, job in enumerate(jobs):
            routes = sponsor_routes(job, sponsors)

            with st.container(border=True):
                st.markdown(f"#### {job.get('title', 'No title')}")
                st.caption(f"🏢 {job.get('company', '')}  ·  📍 {job.get('location', '')}")

                badges = []
                if mentions_visa(job):
                    badges.append(":green-badge[✅ Visa / relocation]")
                if routes:
                    badges.append(f":blue-badge[🛂 UK sponsor: {routes}]")
                if badges:
                    st.markdown(" ".join(badges))

                st.write(clean_text(job.get("snippet", ""))[:300])

                col1, col2, col3, col4 = st.columns(4)
                col1.link_button("Open job", job.get("link", ""), use_container_width=True)
                match_clicked = col2.button("Match score", key=f"match_{i}", use_container_width=True)
                letter_clicked = col3.button("Cover letter", key=f"letter_{i}", use_container_width=True)
                save_clicked = col4.button("Save job", key=f"save_{i}", use_container_width=True)

                if match_clicked:
                    if not cv_text:
                        st.warning("Paste your CV text above first.")
                    else:
                        with st.spinner("Asking Gemini..."):
                            st.session_state["scores"][i] = ask_gemini(make_prompt(cv_text, job))

                if letter_clicked:
                    if not cv_text:
                        st.warning("Paste your CV text above first.")
                    else:
                        with st.spinner("Writing cover letter..."):
                            st.session_state["letters"][i] = ask_gemini(make_letter_prompt(cv_text, job))

                if save_clicked:
                    link = job.get("link", "")
                    tracker = st.session_state["tracker"]
                    if link in tracker["Link"].values:
                        st.info("Already saved.")
                    else:
                        new_row = pd.DataFrame([{
                            "Title": job.get("title", ""),
                            "Company": job.get("company", ""),
                            "Location": job.get("location", ""),
                            "Link": link,
                            "Status": "Saved",
                        }])
                        st.session_state["tracker"] = pd.concat([tracker, new_row], ignore_index=True)
                        st.success("Saved to tracker ✅ (see the My tracker tab)")

                if i in st.session_state["scores"]:
                    st.info(st.session_state["scores"][i])

                if i in st.session_state["letters"]:
                    st.text_area(
                        "Cover letter draft (edit and copy)",
                        st.session_state["letters"][i],
                        height=300,
                        key=f"letter_box_{i}",
                    )

with tab_tracker:
    st.subheader("My Application Tracker")

    current = st.session_state["tracker"]
    if "Status" in current.columns:
        counts = current["Status"].value_counts()
    else:
        counts = {}

    metric_cols = st.columns(len(STATUSES))
    for metric_col, status_name in zip(metric_cols, STATUSES):
        metric_col.metric(status_name, int(counts.get(status_name, 0)))

    uploaded = st.file_uploader("Load a saved tracker CSV (optional)", type="csv")
    if uploaded is not None and st.button("Load this CSV"):
        st.session_state["tracker"] = pd.read_csv(uploaded)
        st.rerun()

    edited = st.data_editor(
        st.session_state["tracker"],
        column_config={
            "Status": st.column_config.SelectboxColumn("Status", options=STATUSES),
            "Link": st.column_config.LinkColumn("Link"),
        },
        num_rows="dynamic",
        use_container_width=True,
        key="tracker_editor",
    )
    st.session_state["tracker"] = edited

    st.download_button(
        "Download tracker CSV",
        edited.to_csv(index=False),
        "tracker.csv",
        "text/csv",
    )
    st.caption("Your tracker is not stored on the server. Download the CSV before you leave.")

# ---------- Footer ----------
st.divider()
st.caption("Built with Streamlit, Jooble API and Gemini API. Check every job and AI output yourself before applying.")
