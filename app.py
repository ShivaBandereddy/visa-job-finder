import streamlit as st
import requests
import pandas as pd

st.title("Visa Sponsorship Job Finder")

keyword = st.text_input("Keyword", "recruiter")

if st.button("Search jobs"):
    url = "https://www.arbeitnow.com/api/job-board-api"
    response = requests.get(url, timeout=20)
    jobs = response.json().get("data", [])

    rows = []
    for job in jobs:
        title = job.get("title", "")
        if keyword.lower() in title.lower():
            rows.append({
                "Title": title,
                "Company": job.get("company_name", ""),
                "Location": job.get("location", ""),
                "Link": job.get("url", ""),
            })

    if rows:
        st.dataframe(pd.DataFrame(rows))
    else:
        st.write("No jobs found. Try another keyword.")
