SOLAR RAYS QUOTATION APP - COMPANY DETAILS, BRANDING & MANUAL SPECS
===================================================================
Repository: https://github.com/rakeshchandrajoshi/biiling

The package includes:
  apply_solar_rays_update.py    Automated source updater (backs up originals)
  LOGO_SOLARNEW.jpg             Supplied Solar Rays company logo

OFFICIAL COMPANY INFORMATION PRE-FILLED
---------------------------------------
Name: SOLAR RAYS ENERGY SOLUTIONS LLP
Address: 12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow,
         Uttar Pradesh, 226029
GSTIN: 09AFUFS6953D1ZA
State Code: 09
State: Uttar Pradesh

WHAT IT CHANGES
---------------
- Shows the company name in FULL UPPERCASE on the webpage. No more 'Llp'.
- Shows the registered address, GSTIN, state code and state under the app header.
- Prefills and exposes these entries in Company Settings.
- One-time migration updates existing saved SQLite settings with official
  corporate details. Subsequent user edits are preserved.
- Prints legal details on the FIRST and THIRD pages of newly generated quote PDFs.
- Keeps logo on the Streamlit page, PDF cover and all PDF page headers.
- When 'Other' is selected as the solar module make, displays a required custom
  manufacturer field that flows to the BOQ, materials and PDF.
- Under 'Bill of Quantities', opens an optional expandable section with text
  fields for every default generic make / quantity entry, including:
    * 'As per approved design' (5 Make entries across BOQ and Materials)
    * 'Standard approved make' (5 material Make entries)
    * 'As per site design' (where selected)
    * 'As per system' / 'As per module layout' (material Quantity entries)
  Editing these fields updates the same BOQ or materials tables used for PDFs.
  BOQ and material tables remain directly editable for any other entry.

HOW TO APPLY
------------
1. Back up your existing local checkout/database.
2. Extract this ZIP file. Put the two files above into your cloned 'biiling'
   directory, the directory containing app.py and pdf_engine.py.
3. From that directory run:
       python apply_solar_rays_update.py
4. Restart the app:
       streamlit run app.py
5. Verify Company Settings and create a NEW quotation, testing the custom
   module make and at least one manually specified BOQ/material make.
6. Commit and push the resulting changed source files and logo:
       git add app.py pdf_engine.py LOGO_SOLARNEW.jpg
       git commit -m "Show registered company details and enable custom design specifications"
       git push origin main

NOTE ABOUT VERSIONS
-------------------
The updater works whether the earlier Solar Rays logo/custom module patch was
installed or not. It is safe to run repeatedly. Every changed source file is
backed up before writing. If the expected repository layout differs, the update
stops without changing the source files.

Previously stored quotation PDFs are held as immutable PDF blobs in the SQLite
database, so they do NOT change retroactively. Newly generated PDFs use the
updated identity and edited design specifications.

GitHub permission note: Direct pushing was not available through the connected
GitHub account when this package was prepared. Changes must be applied and
pushed using a local account with write access to the repository.
