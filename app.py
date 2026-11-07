import re
import streamlit as st
import requests
import pandas as pd

st.title("Visa Sponsorship Job Finder")

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


def clean_text(text):
    return re.sub(r"<[^>]+>", "", text or "")

def mentions_visa(job):
    text = (job.get("title", "") + " " + clean_text(job.get("snippet", ""))).lower()
    return any(word in text for word in VISA_WORDS)
def sponsor_routes(job, sponsors):
    return sponsors.get(normalize(job.get("company", "")))

def normalize(name):
    name = (name or "").lower()
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    words = [w for w in name.split() if w not in ("ltd", "limited", "plc", "llp", "inc", "llc")]
    return " ".join(words)


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

GEMINI_MODEL = "gemini-3.5-flash-lite"
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
    
country = st.selectbox("Select country", countries)

keyword = st.selectbox(
    "Select role keyword",
    ["HR", "Recruiter", "Talent Acquisition", "People Operations", "Payroll", "Onboarding", "HR Manager"]
)

city = st.text_input("City (optional, e.g. Amsterdam, Edinburgh, Warsaw)", "")

only_visa = st.checkbox("Show only jobs mentioning visa / relocation")
only_sponsor = st.checkbox("Show only licensed sponsors (UK only)")

cv_text = st.text_area(
    "Paste your CV text here (optional, used for match score later)",
    height=200,
)

if cv_text:
    st.caption(f"CV loaded: {len(cv_text.split())} words")
    
if st.button("Search jobs"):
    location = city if city else country
    status, jobs = fetch_jobs(st.secrets["JOOBLE_API_KEY"], keyword, location)

    if status != 200:
        st.error(f"Error {status}. Check your key in Secrets.")
        st.stop()

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

if "jobs" in st.session_state:
    jobs = st.session_state["jobs"]
    sponsors = load_uk_sponsors() if st.session_state["searched_country"] == "United Kingdom" else {}

    st.write(f"Found {len(jobs)} jobs")

    for i, job in enumerate(jobs):
        st.subheader(job.get("title", "No title"))

        if mentions_visa(job):
            st.success("Visa / relocation mentioned ✅")

        routes = sponsor_routes(job, sponsors)
        if routes:
            st.success(f"Licensed UK sponsor ✅ {routes}")

        st.write(job.get("company", ""), "-", job.get("location", ""))
        st.write(clean_text(job.get("snippet", ""))[:300])
        st.link_button("Open job", job.get("link", ""))

        if st.button("Match score", key=f"match_{i}"):
            if not cv_text:
                st.warning("Paste your CV text above first.")
            else:
                with st.spinner("Asking Gemini..."):
                    st.session_state["scores"][i] = ask_gemini(make_prompt(cv_text, job))

        if i in st.session_state["scores"]:
            st.info(st.session_state["scores"][i])

        st.divider()
