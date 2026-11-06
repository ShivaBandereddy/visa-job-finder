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

country = st.selectbox("Select country", countries)

keyword = st.selectbox(
    "Select role keyword",
    ["HR", "Recruiter", "Talent Acquisition", "People Operations", "Payroll", "Onboarding", "HR Manager"]
)

city = st.text_input("City (optional, e.g. Amsterdam, Edinburgh, Warsaw)", "")

if st.button("Search jobs"):
    api_key = st.secrets["JOOBLE_API_KEY"]
    url = f"https://jooble.org/api/{api_key}"

    location = city if city else country
    payload = {"keywords": keyword, "location": location}

    response = requests.post(url, json=payload, timeout=20)

    if response.status_code != 200:
        st.error(f"Error {response.status_code}. Check your key in Secrets.")
    else:
        jobs = response.json().get("jobs", [])
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
