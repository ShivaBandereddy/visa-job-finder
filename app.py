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


country = st.selectbox("Select country", countries)

keyword = st.selectbox(
    "Select role keyword",
    ["HR", "Recruiter", "Talent Acquisition", "People Operations", "Payroll", "Onboarding", "HR Manager"]
)

city = st.text_input("City (optional, e.g. Amsterdam, Edinburgh, Warsaw)", "")

only_visa = st.checkbox("Show only jobs mentioning visa / relocation")
only_sponsor = st.checkbox("Show only licensed sponsors (UK only)")

if st.button("Search jobs"):
    location = city if city else country
    status, jobs = fetch_jobs(st.secrets["JOOBLE_API_KEY"], keyword, location)

    if status != 200:
        st.error(f"Error {status}. Check your key in Secrets.")
        st.stop()

    st.write(f"Found {len(jobs)} jobs")

    for job in jobs:
        st.subheader(job.get("title", "No title"))
        st.write(job.get("company", ""), "-", job.get("location", ""))
        st.write(clean_text(job.get("snippet", ""))[:300])
        st.link_button("Open job", job.get("link", ""))
        st.divider()
