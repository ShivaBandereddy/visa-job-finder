import re
from urllib.parse import quote_plus, quote
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
    "United Kingdom", "Scotland", "Ireland", "Netherlands", "Luxembourg", "Belgium",
    "Austria", "Switzerland", "Czech Republic", "Poland", "Portugal", "Malta",
    "Sweden", "Norway", "Finland", "Estonia", "Latvia",
    "Canada", "New Zealand", "Australia", "Singapore",
]

UK_COUNTRIES = ["United Kingdom", "Scotland"]

VISA_WORDS = ["visa sponsor", "sponsorship", "sponsor", "relocation", "relocate", "work permit", "blue card"]

STATUSES = ["Saved", "Applied", "Interview", "Offer", "Rejected"]

GEMINI_MODEL = "gemini-3.5-flash-lite"


def clean_text(text):
    return re.sub(r"<[^>]+>", "", text or "")


def normalize(name):
    name = (name or "").lower()
    name = re.sub(r"\b([bn])\.?\s?v\b\.?", r"\1v", name)
    name = re.sub(r"[^a-z0-9 ]", " ", name)
    words = [w for w in name.split() if w not in ("ltd", "limited", "plc", "llp", "inc", "llc", "bv", "nv")]
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


@st.cache_data
def load_nl_sponsors():
    df = pd.read_csv("nl_sponsors.csv", encoding="utf-8-sig")
    keys = df["Organisation Name"].apply(normalize)
    return {key: "IND recognised" for key in keys if key}


def get_sponsor_list(country):
    if country in UK_COUNTRIES:
        return load_uk_sponsors(), "UK"
    if country == "Netherlands":
        return load_nl_sponsors(), "NL"
    return None, ""


@st.cache_data(ttl=3600)
def fetch_jobs(api_key, keyword, location):
    url = f"https://jooble.org/api/{api_key}"
    payload = {"keywords": keyword, "location": location}
    response = requests.post(url, json=payload, timeout=20)
    if response.status_code != 200:
        return response.status_code, []
    return 200, response.json().get("jobs", [])

def make_job(title, company, location, snippet, link):
    return {
        "title": title or "",
        "company": company or "",
        "location": location or "",
        "snippet": (snippet or "")[:2000],
        "link": link or "",
    }


@st.cache_data(ttl=3600)
def fetch_sweden(keyword, city):
    query = f"{keyword} {city}".strip()
    try:
        response = requests.get(
            "https://jobsearch.api.jobtechdev.se/search",
            params={"q": query, "limit": 50},
            headers={"accept": "application/json"},
            timeout=20,
        )
    except requests.RequestException:
        return 0, []
    if response.status_code != 200:
        return response.status_code, []
    jobs = []
    for hit in response.json().get("hits", []):
        address = hit.get("workplace_address") or {}
        description = hit.get("description") or {}
        link = hit.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{hit.get('id', '')}"
        jobs.append(make_job(
            hit.get("headline"),
            (hit.get("employer") or {}).get("name"),
            address.get("municipality") or address.get("city") or address.get("region"),
            description.get("text"),
            link,
        ))
    return 200, jobs


@st.cache_data(ttl=3600)
def fetch_singapore(keyword):
    try:
        response = requests.get(
            "https://api.mycareersfuture.gov.sg/v2/jobs",
            params={"search": keyword, "limit": 50, "page": 0},
            headers={"accept": "application/json", "User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
    except requests.RequestException:
        return 0, []
    if response.status_code != 200:
        return response.status_code, []
    jobs = []
    for item in response.json().get("results", []):
        salary = item.get("salary") or {}
        low, high = salary.get("minimum"), salary.get("maximum")
        salary_text = ""
        if low and high:
            salary_text = f"Salary: S${int(low):,} to S${int(high):,} per month. "
        link = (item.get("metadata") or {}).get("jobDetailsUrl") or f"https://www.mycareersfuture.gov.sg/job/{item.get('uuid', '')}"
        jobs.append(make_job(
            item.get("title"),
            (item.get("postedCompany") or {}).get("name"),
            "Singapore",
            salary_text + clean_text(item.get("description")),
            link,
        ))
    return 200, jobs


@st.cache_data(ttl=3600)
def fetch_reed(api_key, keyword, location):
    try:
        response = requests.get(
            "https://www.reed.co.uk/api/1.0/search",
            params={"keywords": keyword, "locationName": location, "resultsToTake": 50},
            auth=(api_key, ""),
            timeout=20,
        )
    except requests.RequestException:
        return 0, []
    if response.status_code != 200:
        return response.status_code, []
    jobs = []
    for item in response.json().get("results", []):
        low, high = item.get("minimumSalary"), item.get("maximumSalary")
        salary_text = ""
        if low and high:
            salary_text = f"Salary: £{int(low):,} to £{int(high):,} per year. "
        jobs.append(make_job(
            item.get("jobTitle"),
            item.get("employerName"),
            item.get("locationName"),
            salary_text + clean_text(item.get("jobDescription")),
            item.get("jobUrl"),
        ))
    return 200, jobs


def fetch_jobs_for_country(country, keyword, city):
    if country == "Sweden":
        status, jobs = fetch_sweden(keyword, city)
        if status == 200:
            return status, jobs, "Platsbanken (official)"
    elif country == "Singapore":
        status, jobs = fetch_singapore(keyword)
        if status == 200:
            return status, jobs, "MyCareersFuture (official)"
    elif country in UK_COUNTRIES and "REED_API_KEY" in st.secrets:
        place = city if city else ("Scotland" if country == "Scotland" else "")
        status, jobs = fetch_reed(st.secrets["REED_API_KEY"], keyword, place)
        if status == 200:
            return status, jobs, "Reed API"
    location = city if city else country
    status, jobs = fetch_jobs(st.secrets["JOOBLE_API_KEY"], keyword, location)
    return status, jobs, "Jooble"

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
LOCAL_BOARDS = {
    "United Kingdom": [
        ("Reed", "https://www.reed.co.uk/jobs?keywords={kw_plus}&location={place_plus}"),
        ("Indeed UK", "https://uk.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Scotland": [
        ("s1jobs", "https://www.s1jobs.com/jobs{city_path}/?Keywords={kw_plus}"),
        ("Reed", "https://www.reed.co.uk/jobs?keywords={kw_plus}&location={place_plus}"),
        ("Indeed UK", "https://uk.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Ireland": [
        ("IrishJobs", "https://www.irishjobs.ie/jobs/{kw_slug}"),
        ("Indeed IE", "https://ie.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Netherlands": [
        ("Nationale Vacaturebank", "https://www.nationalevacaturebank.nl/vacatures?query={kw_plus}"),
        ("Indeed NL", "https://nl.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Luxembourg": [
        ("Indeed LU", "https://lu.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
        ("Moovijob (site)", "https://www.moovijob.com/"),
        ("EURES (site)", "https://eures.europa.eu/"),
    ],
    "Belgium": [
        ("VDAB", "https://www.vdab.be/vindeenjob/vacatures?trefwoord={kw_plus}"),
        ("Indeed BE", "https://be.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
        ("Jobat (site)", "https://www.jobat.be/"),
    ],
    "Austria": [
        ("karriere.at", "https://www.karriere.at/jobs?keywords={kw_plus}&locations={place_plus}"),
        ("Indeed AT", "https://at.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Switzerland": [
        ("Jobs.ch", "https://www.jobs.ch/en/vacancies/?term={kw_plus}&location={place_plus}"),
        ("Indeed CH", "https://ch.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Czech Republic": [
        ("Jobs.cz", "https://www.jobs.cz/prace{city_path}/?q%5B%5D={kw_plus}"),
        ("Prace.cz", "https://www.prace.cz/nabidky/?q={kw_plus}"),
    ],
    "Poland": [
        ("Pracuj.pl", "https://www.pracuj.pl/praca/{kw_path}"),
        ("Indeed PL", "https://pl.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Portugal": [
        ("Net-Empregos", "https://www.net-empregos.com/pesquisa-empregos.asp?chaves={kw_plus}&cidade={city_slug}"),
        ("Indeed PT", "https://pt.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Malta": [
        ("KeepMePosted (site)", "https://keepmeposted.com.mt/"),
        ("Konnekt (site)", "https://www.konnekt.com/"),
        ("EURES (site)", "https://eures.europa.eu/"),
    ],
    "Sweden": [("Platsbanken (site)", "https://arbetsformedlingen.se/platsbanken/")],
    "Norway": [("Finn.no", "https://www.finn.no/job/search?q={kw_plus}")],
    "Finland": [("Duunitori (site)", "https://duunitori.fi/")],
    "Estonia": [
        ("CV Keskus (site)", "https://www.cvkeskus.ee/"),
        ("CV.ee (site)", "https://www.cv.ee/"),
        ("Tootukassa (site)", "https://www.tootukassa.ee/toopakkumised"),
    ],
    "Latvia": [
        ("CV.lv (site)", "https://www.cv.lv/lv"),
        ("CVmarket (site)", "https://www.cvmarket.lv"),
        ("NVA (site)", "https://cvvp.nva.gov.lv/#/pub/"),
    ],
    "Canada": [
        ("Job Bank", "https://www.jobbank.gc.ca/jobsearch/jobsearch?searchstring={kw_plus}&locationstring={place_plus}"),
        ("Indeed CA", "https://ca.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "New Zealand": [
        ("Seek NZ", "https://www.seek.co.nz/jobs?keywords={kw_plus}&where={place_plus}"),
        ("INZ employer check (site)", "https://immigration.govt.nz/work/requirements-for-work-visas/approved-employers/accredited-employer-list"),
    ],
    "Australia": [
        ("Seek", "https://www.seek.com.au/jobs?keywords={kw_plus}&where={place_plus}"),
        ("Indeed AU", "https://au.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
    "Singapore": [
        ("JobStreet", "https://sg.jobstreet.com/{kw_slug}-jobs"),
        ("Indeed SG", "https://sg.indeed.com/jobs?q={kw_plus}&l={place_plus}"),
    ],
}


def local_board_links(country, keyword, city):
    place = city if city else ("Scotland" if country == "Scotland" else "")
    city_slug = re.sub(r"[^a-z0-9]+", "-", city.lower()).strip("-")
    values = {
        "kw_plus": quote_plus(keyword),
        "kw_path": quote(keyword),
        "kw_slug": re.sub(r"[^a-z0-9]+", "-", keyword.lower()).strip("-"),
        "place_plus": quote_plus(place),
        "city_slug": city_slug,
        "city_path": f"/{city_slug}" if city_slug else "",
    }
    return [(label, template.format(**values)) for label, template in LOCAL_BOARDS.get(country, [])]

# ---------- Sidebar: search filters ----------
st.sidebar.header("🔎 Search filters")

country = st.sidebar.selectbox("Country", countries)

keyword_options = [
    "HR", "Recruiter", "Talent Acquisition", "People Operations", "Payroll", "Onboarding", "HR Manager",
    "People Analytics", "HR Analytics", "HR Technology", "HRIS",
    "AI Recruiter", "Talent Intelligence", "AI Trainer", "Prompt Engineer", "AI Operations",
]
keyword_choice = st.sidebar.selectbox("Role keyword", keyword_options)
custom_keyword = st.sidebar.text_input(
    "Or type your own keyword (optional)", "", placeholder="e.g. HR AI specialist"
)
keyword = custom_keyword.strip() if custom_keyword.strip() else keyword_choice

city = st.sidebar.text_input("City (optional)", "", placeholder="e.g. Amsterdam, Edinburgh")

only_visa = st.sidebar.checkbox("Only visa / relocation jobs")
only_sponsor = st.sidebar.checkbox("Only recognised sponsors (UK, Scotland, Netherlands)")

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
        status, jobs, source = fetch_jobs_for_country(country, keyword, city)

        if status != 200:
            st.error(f"Error {status}. Check your key in Secrets.")
        else:
            if only_sponsor:
                sponsors_now, _ = get_sponsor_list(country)
                if sponsors_now is None:
                    st.info("Sponsor check works for UK, Scotland and Netherlands only.")
                else:
                    jobs = [job for job in jobs if sponsor_routes(job, sponsors_now)]

            if only_visa:
                jobs = [job for job in jobs if mentions_visa(job)]

            st.session_state["jobs"] = jobs
            st.session_state["searched_country"] = country
            st.session_state["searched_keyword"] = keyword
            st.session_state["searched_city"] = city
            st.session_state["source"] = source
            st.session_state["scores"] = {}
            st.session_state["letters"] = {}

    # ----- Results -----
    if "jobs" not in st.session_state:
        st.info("👈 Choose a country and role in the sidebar, then click **Search jobs**.")
    elif len(st.session_state["jobs"]) == 0:
        st.warning("No jobs matched. Try another city, or turn off the filters.")
    else:
        jobs = st.session_state["jobs"]
        sponsors, sponsor_label = get_sponsor_list(st.session_state["searched_country"])
        sponsors = sponsors or {}

        st.subheader(f"{len(jobs)} jobs found")
        st.caption(f"Source: {st.session_state.get('source', 'Jooble')}")
        board_links = local_board_links(
        st.session_state["searched_country"],
        st.session_state.get("searched_keyword", ""),
        st.session_state.get("searched_city", ""),
        )
        if board_links:
            st.caption("🌐 Local job sites for this country (opens in a new tab)")
            board_cols = st.columns(len(board_links))
            for board_col, (label, url) in zip(board_cols, board_links):
                board_col.link_button(label, url, use_container_width=True)
        for i, job in enumerate(jobs):
            routes = sponsor_routes(job, sponsors)

            with st.container(border=True):
                st.markdown(f"#### {job.get('title', 'No title')}")
                st.caption(f"🏢 {job.get('company', '')}  ·  📍 {job.get('location', '')}")

                badges = []
                if mentions_visa(job):
                    badges.append(":green-badge[✅ Visa / relocation]")
                if routes:
                    badges.append(f":blue-badge[🛂 {sponsor_label} sponsor: {routes}]")
                if badges:
                    st.markdown(" ".join(badges))

                st.write(clean_text(job.get("snippet", ""))[:300])

                google_url = "https://www.google.com/search?q=" + quote_plus(
                    f"{job.get('title', '')} {job.get('company', '')} apply"
                )

                linkedin_url = (
                    "https://www.linkedin.com/jobs/search/?keywords="
                    + quote_plus(f"{job.get('title', '')} {job.get('company', '')}")
                    + "&location="
                    + quote_plus(job.get("location", "") or "")
                )

                col1, col2, col3, col4, col5, col6 = st.columns(6)
                col1.link_button("Open job", job.get("link", ""), use_container_width=True)
                col2.link_button("🔍 Google", google_url, use_container_width=True)
                col3.link_button("💼 LinkedIn", linkedin_url, use_container_width=True)
                match_clicked = col4.button("Match score", key=f"match_{i}", use_container_width=True)
                letter_clicked = col5.button("Cover letter", key=f"letter_{i}", use_container_width=True)
                save_clicked = col6.button("Save job", key=f"save_{i}", use_container_width=True)

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
