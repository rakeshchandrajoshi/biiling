# Solar Rays Quotation Management System

A Streamlit prototype for Solar Rays Energy Solutions LLP that creates professional 3-page solar quotation PDFs from user-entered customer, technical and commercial details.

## What is included

- Customer and project input form
- On-Grid / Hybrid / Off-Grid selections
- Automatic suggested panel quantity from plant capacity and panel wattage
- Editable BOQ
- Editable detailed material specification
- Lump-sum or per-kW pricing
- Automatic discount, GST, total, subsidy and effective-cost calculations
- Editable quotation terms
- Automatic quotation numbering by Indian financial year
- 3-page PDF generator using ReportLab
- Company settings, banking details and logo upload
- SQLite quotation history with status tracking and stored PDFs

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the app:

```bash
streamlit run app.py
```

5. Your browser will normally open at `http://localhost:8501`.

## First-time setup

Open **Company Settings** and enter your final:

- GSTIN
- office / registered address
- email
- bank account details
- real company logo

The app intentionally does not invent these values. The defaults contain only the public company name, website and contact numbers used for the initial prototype.

## Deployment

### Streamlit Community Cloud

Push these files to a GitHub repository and deploy `app.py` on Streamlit Community Cloud.

### Important production note

The prototype uses a local SQLite database (`solar_quotes.db`). This is ideal for local testing. On stateless cloud hosting, local files can be reset/replaced during redeploys or restarts. For a production multi-user system, migrate quotation storage to PostgreSQL/Supabase and add authentication.

## PDF structure

1. Proposal / customer introduction and project snapshot
2. Commercial quotation, BOQ, GST/subsidy summary, terms and payment details
3. Detailed material specification and company details

## Calculation rule

The program calculates GST mathematically from the taxable value and the GST percentage entered by the user. Subsidy is treated as an indicative deduction after the quotation total, with an editable eligibility disclaimer.
