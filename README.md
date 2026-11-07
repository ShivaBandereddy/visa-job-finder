
# Visa Sponsorship Job Finder

A free web app that helps HR and recruitment professionals find jobs in Europe from employers that mention visa sponsorship or relocation, check whether a UK employer is a licensed sponsor, and track applications in one place.

**Live app:** https://visa-job-finder-shiva.streamlit.app

## The problem

Moving abroad for an HR or recruitment role means searching many job boards, reading each job ad to see whether the employer sponsors visas, checking official lists by hand, and then writing a different cover letter for every application. This app puts those steps in one place.

## What it does

- **Search jobs** by country, role keyword (HR, Recruiter, Talent Acquisition, People Operations, Payroll, Onboarding, HR Manager) and optional city.
- **Visa / relocation filter:** flags jobs whose title or description mentions visa sponsorship, relocation, work permit or blue card.
- **UK licensed sponsor check:** matches the employer name against the official UK Register of Licensed Sponsors (Workers) and shows the visa routes.
- **CV match score:** paste your CV text and get a 0-100 score with reasons and gaps, written by the Gemini API.
- **Tailored cover letter:** generates an editable draft of up to 250 words, using only facts from your CV.
- **Application tracker:** save jobs, set status (Saved, Applied, Interview, Offer, Rejected), then download or reload your tracker as a CSV file.

## How it works

1. The app sends your keyword and location to the Jooble job search API.
2. Results are filtered in Python (visa words, sponsor list) and stored in `st.session_state`, so buttons do not wipe the list.
3. For the match score and cover letter, the app sends your CV text and the job text to the Gemini API with a structured prompt.
4. The tracker is a table in the browser session. You download it as CSV and upload it next time.

## Tech stack (all free)

| Purpose | Tool |
|---|---|
| App framework | Streamlit |
| Hosting | Streamlit Community Cloud |
| Code | GitHub (edited in the browser) |
| Job data | Jooble API (free key, about 500 requests) |
| AI | Google Gemini API (free tier) |
| Sponsor data | UK Register of Licensed Sponsors (Workers), gov.uk |
| Language | Python (pandas, requests) |

## Run it yourself

1. Fork this repository.
2. Download the licensed sponsors CSV from gov.uk and save it as `uk_sponsors.csv` in the repo root.
3. Deploy on Streamlit Community Cloud.
4. In the app settings, open Secrets and add your own keys:

```toml
JOOBLE_API_KEY = "your-jooble-key"
GEMINI_API_KEY = "your-gemini-key"
```

Never commit API keys to GitHub.

## Privacy

- Your CV text is only pasted into the browser and is not stored by the app.
- The Gemini free tier may use inputs to improve Google products, so remove your phone number, address and email before pasting.
- The tracker lives in your browser session and in the CSV you download.

## Limitations

- The sponsor check covers the UK only. Company names are matched after simple cleaning, so some employers with different legal names are missed.
- Jooble returns a short job snippet, so the visa filter and match score can miss details found only in the full job ad.
- Free API limits apply. Prolonged use may return rate limit errors.
- AI output can be wrong. Always read the match score reasons and cover letter before using them.

## Roadmap

- Netherlands IND recognised sponsor list check
- A second free job source
- Hiring Bias + EU AI Act Checker (Project 2)
- Case study of my recruitment portal (Project 3)

## Screenshots

ADD-SCREENSHOTS-HERE

## About me

HR manager from India moving into HR-tech and recruitment operations roles in Europe, learning to build practical tools in Python. ADD-YOUR-LINKEDIN-LINK-HERE
