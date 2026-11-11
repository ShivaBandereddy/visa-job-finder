# Visa Sponsorship Job Finder

A free web app for HR and recruitment professionals (and people moving into HR-tech and AI roles) who want to work abroad. It searches jobs in 21 countries, flags employers that mention visa sponsorship or relocation, checks employer names against official sponsor lists (UK, Scotland and Netherlands), matches your CV to each job, drafts a cover letter and tracks your applications in one place.

**Live app:** https://visa-job-finder-shiva.streamlit.app/

**Built by:** [Your Name](YOUR-LINKEDIN-URL)

## The problem

Moving abroad for an HR or recruitment role means searching many job boards in many countries, reading each job ad to see whether the employer sponsors visas, checking official lists by hand, looking up salary rules for each visa, and then writing a different cover letter for every application. This app puts those steps in one place.

## What it does

- **Search jobs in 21 countries:** United Kingdom, Scotland, Ireland, Netherlands, Luxembourg, Belgium, Austria, Switzerland, Czech Republic, Poland, Portugal, Malta, Sweden, Norway, Finland, Estonia, Latvia, Canada, New Zealand, Australia and Singapore.
- **HR and AI-related roles:** pick a role keyword (HR, Recruiter, Talent Acquisition, People Operations, Payroll, Onboarding, HR Manager, People Analytics, HR Analytics, HR Technology, HRIS, AI Recruiter, Talent Intelligence, AI Trainer, Prompt Engineer, AI Operations) or type your own keyword. An optional city narrows the search.
- **Visa / relocation filter:** flags jobs whose title or description mentions visa sponsorship, relocation, work permit or blue card.
- **Recognised sponsor check:** matches the employer name against the official UK Register of Licensed Sponsors (Workers) for the UK and Scotland, and the IND public register of recognised sponsors for the Netherlands. A badge shows the match.
- **Salary rules at a glance:** for countries with a clear visa salary rule (UK, Netherlands, Sweden, Norway, Singapore, Malta) the results show a short note with the current minimum. Each note says when it was checked.
- **Local job sites:** under the results, buttons open the main local job boards for that country with your keyword already filled in (for example Reed, IrishJobs, Jobs.ch, Pracuj.pl, Seek, Finn.no, karriere.at, VDAB, Jobs.cz, Net-Empregos, Job Bank).
- **CV match score:** paste your CV text and get a 0-100 score with reasons and gaps, written by the Gemini API.
- **Tailored cover letter:** generates an editable draft of up to 250 words, using only facts from your CV.
- **Find the original posting:** each job card has Google and LinkedIn search buttons, so you can reach the employer's own career page and apply there.
- **Application tracker:** save jobs, set status (Saved, Applied, Interview, Offer, Rejected), see a count per status, then download or reload your tracker as a CSV file.



## How it works

1. You choose a country, a role keyword and optionally a city.
2. The app picks the best job source for that country:
   - Sweden: Platsbanken (the official open JobTech API of the Swedish Public Employment Service)
   - Singapore: MyCareersFuture (the official government job portal), which shows the salary range
   - UK and Scotland: the Reed API when a Reed key is set
   - All other countries (and as a fallback): the Jooble job search API

   The result page shows which source was used.
3. Results are filtered in Python (visa words, sponsor list) and stored in `st.session_state`, so buttons do not wipe the list.
4. Each job is shown as a card with badges for visa mentions and recognised sponsors.
5. For the match score and cover letter, the app sends your CV text and the job text to the Gemini API with a structured prompt.
6. The tracker is a table in the browser session. You download it as CSV and upload it next time.

## Tech stack (all free)

| Purpose | Tool |
|---|---|
| App framework | Streamlit |
| Hosting | Streamlit Community Cloud |
| Code | GitHub (edited in the browser) |
| Job data | Jooble API, Platsbanken (JobTech API), MyCareersFuture API, Reed API |
| AI | Google Gemini API (free tier) |
| Sponsor data | UK Register of Licensed Sponsors (Workers) from gov.uk, IND public register of recognised sponsors (Netherlands) |
| Language | Python (pandas, requests) |

## Run it yourself

1. Fork this repository.
2. Download the UK Register of Licensed Sponsors (Workers) CSV from gov.uk and save it as `uk_sponsors.csv` in the repo root.
3. For the Netherlands, save the IND recognised sponsors list as `nl_sponsors.csv` in the repo root, with the columns `Organisation Name` and `KvK`.
4. Make sure `requirements.txt` contains `streamlit`, `requests` and `pandas`.
5. Deploy on Streamlit Community Cloud.
6. In the app settings, open Secrets and add your own keys in one box:

```toml
JOOBLE_API_KEY = "your-jooble-key"
GEMINI_API_KEY = "your-gemini-key"
REED_API_KEY = "your-reed-key"   # optional, enables the Reed API for UK and Scotland
```

Never commit API keys to GitHub. Sweden (Platsbanken) and Singapore (MyCareersFuture) need no key.

## Privacy

- Your CV text is only pasted into the browser and is not stored by the app.
- The Gemini free tier may use inputs to improve Google products, so remove your phone number, address and email before pasting.
- The tracker lives in your browser session and in the CSV you download.

## Limitations

- **Sponsor checks cover the UK, Scotland and the Netherlands only.** Company names are matched after simple cleaning, so some employers with different legal names are missed. The registers change often, so re-download them regularly.
- **No downloadable sponsor list exists for most countries.** For example, New Zealand's accredited employer list is only a search tool on the Immigration NZ website (the app links to it), and some employers choose not to be shown.
- Salary notes were checked in November 2026 against official and secondary sources. Visa rules change, so always confirm on the official immigration website before you decide.
- Jooble returns a short job snippet, so the visa filter and match score can miss details found only in the full job ad. Jooble results can also include jobs from other countries.
- The Jooble free API key has a limited number of requests. Heavy use may return errors, and results are cached for one hour to save requests.
- Some job sites block direct links (for example IrishJobs and Totaljobs showed "Access Denied" in tests, and Jooble links may not open from outside jooble.org). Each card has Google and LinkedIn search buttons as a backup. Buttons marked "(site)" open the site's home page only, because no working keyword search link could be confirmed.
- Many jobs in countries such as Sweden, Czech Republic, Austria, Switzerland and Finland are written in the local language, so keywords in that language give better results.
- AI output can be wrong. Always read the match score reasons and cover letter before using them.
- The tracker is not stored on the server. Download the CSV before you leave.

## Roadmap

- Norway: use the NAV job feed (needs a token and a different approach, because it is a feed and not a keyword search)
- A message when a country has no results, with the local job site buttons shown anyway
- New Zealand sponsor list from an official information request, if a fresh list can be obtained
- Ireland: employment permits issued per company (permit history, not a sponsor list)
- Hiring Bias + EU AI Act Checker (Project 2)
- Case study of my recruitment portal (Project 3)

## About me

HR manager from India moving into HR-tech, AI-in-HR and recruitment operations roles abroad, learning to build practical tools in Python with free tools only.
