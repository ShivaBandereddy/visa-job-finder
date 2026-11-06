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

if st.button("Search jobs"):
    location = city if city else country
    status, jobs = fetch_jobs(st.secrets["JOOBLE_API_KEY"], keyword, location)

    if status != 200:
        st.error(f"Error {status}. Check your key in Secrets.")
    else:
        rows = []
        for job in jobs:
            rows.append({
                "Title": job.get("title", ""),
                "Company": job.get("company", ""),
                "Location": job.get("location", ""),
                "Salary": job.get("salary", ""),
                "Link": job.get("link", ""),
            })

        if rows:
            st.write(f"{len(rows)} jobs found")
            st.dataframe(pd.DataFrame(rows))
        else:
            st.write("No jobs found. Try another keyword or city.")
