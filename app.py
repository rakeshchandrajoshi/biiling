#!/usr/bin/env python3
"""Apply all Solar Rays branding, legal identity and specification updates.

Place this script and LOGO_SOLARNEW.jpg at the root of the `biiling` GitHub
repository (beside app.py and pdf_engine.py), then run:
    python apply_solar_rays_update.py

The updater checks the current code against the original repository layout,
backs up changed source files, and avoids duplicate modifications when rerun.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import ast
import shutil
import sys

ROOT = Path(__file__).resolve().parent
VERSION = "solarnew-2026-10"
CORPORATE_VERSION = "legal-identity-2026-10-24"


def replace_once(source: str, old: str, new: str, description: str) -> str:
    if new in source:
        return source
    occurrences = source.count(old)
    if occurrences != 1:
        raise ValueError(f"{description}: expected one source match, found {occurrences}. No files were changed.")
    return source.replace(old, new, 1)


def change_app(source: str) -> str:
    source = replace_once(
        source,
        'DB_PATH = APP_DIR / "solar_quotes.db"\n',
        'DB_PATH = APP_DIR / "solar_quotes.db"\n'
        'DEFAULT_LOGO_PATH = APP_DIR / "LOGO_SOLARNEW.jpg"\n'
        f'LOGO_ASSET_VERSION = "{VERSION}"\n',
        "register bundled Solar Rays logo",
    )
    source = replace_once(
        source,
        '    merged.update(data)\n    return merged\n',
        '    merged.update(data)\n'
        '    # Migrate older stored logos once so the newly supplied corporate logo\n'
        '    # becomes the default. Later explicit uploads remain supported.\n'
        '    if data.get("_logo_asset_version") != LOGO_ASSET_VERSION:\n'
        '        merged["logo_b64"] = ""\n'
        '        merged["_logo_asset_version"] = LOGO_ASSET_VERSION\n'
        '        save_settings(merged)\n'
        '    return merged\n',
        "migrate previously saved logo",
    )
    old_header = '''st.markdown(
    f"""
    <div class="sr-hero">
      <h1>☀️ {settings['company_name'].title()}</h1>
      <p>Quotation Management System · Create, save and download professional solar proposals.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
'''
    new_header = '''header_logo, header_details = st.columns([1, 7], vertical_alignment="center")
with header_logo:
    if DEFAULT_LOGO_PATH.is_file():
        st.image(str(DEFAULT_LOGO_PATH), width=125)
with header_details:
    st.markdown(
        f"""
        <div class="sr-hero">
          <h1>{settings['company_name'].title()}</h1>
          <p>Quotation Management System · Create, save and download professional solar proposals.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
'''
    source = replace_once(source, old_header, new_header, "show brand logo in Streamlit header")
    source = replace_once(
        source,
        '    panel_brand = p1.selectbox("Solar module make", ["Waaree", "Adani Solar", "Vikram Solar", "RenewSys", "Tata Power Solar", "Other"])\n',
        '    panel_brand_choice = p1.selectbox("Solar module make", ["Waaree", "Adani Solar", "Vikram Solar", "RenewSys", "Tata Power Solar", "Other"])\n'
        '    if panel_brand_choice == "Other":\n'
        '        panel_brand = p1.text_input("Enter solar module make *", placeholder="e.g. LONGi Solar", key="custom_panel_brand").strip()\n'
        '    else:\n'
        '        panel_brand = panel_brand_choice\n',
        "allow manually entered solar module make",
    )
    source = replace_once(
        source,
        '        elif not quote_ref.strip():\n            st.error("Please enter a quotation reference.")\n        else:\n',
        '        elif not quote_ref.strip():\n            st.error("Please enter a quotation reference.")\n'
        '        elif panel_brand_choice == "Other" and not panel_brand:\n'
        '            st.error("Please enter the solar module make when Other is selected.")\n'
        '        else:\n',
        "validate custom solar module make",
    )
    source = replace_once(
        source,
        '        logo = st.file_uploader("Company logo (PNG/JPG)", type=["png", "jpg", "jpeg"], help="Optional. If omitted, a simple SR placeholder is shown in the PDF.")\n'
        '        keep_logo = st.checkbox("Keep existing uploaded logo", value=True)\n',
        '        st.caption("The supplied Solar Rays logo is used in the app and all newly generated PDFs. An uploaded custom logo can override it.")\n'
        '        if DEFAULT_LOGO_PATH.is_file():\n'
        '            st.image(str(DEFAULT_LOGO_PATH), width=125)\n'
        '        logo = st.file_uploader("Upload a different company logo (optional, PNG/JPG)", type=["png", "jpg", "jpeg"], help="Leave blank to use the bundled Solar Rays logo.")\n'
        '        keep_logo = st.checkbox("Keep existing custom logo (uncheck to restore the bundled logo)", value=True)\n',
        "explain default logo in company settings",
    )
    source = replace_once(
        source,
        '                "logo_b64": logo_b64,\n            }\n            save_settings(updated)\n',
        '                "logo_b64": logo_b64,\n'
        '                "_logo_asset_version": LOGO_ASSET_VERSION,\n'
        '            }\n            save_settings(updated)\n',
        "retain logo migration marker when saving settings",
    )
    return source


def change_pdf(source: str) -> str:
    source = replace_once(
        source,
        'import math\nfrom typing import Any, Dict, Iterable, List\n',
        'import math\nfrom pathlib import Path\nfrom typing import Any, Dict, Iterable, List\n',
        "import pathlib for bundled logo",
    )
    source = replace_once(
        source,
        'from reportlab.lib.units import mm\n',
        'from reportlab.lib.units import mm\nfrom reportlab.lib.utils import ImageReader\n',
        "import ImageReader for PDF page logo",
    )
    source = replace_once(
        source,
        'WHITE = colors.white\n',
        'WHITE = colors.white\nDEFAULT_LOGO_PATH = Path(__file__).resolve().parent / "LOGO_SOLARNEW.jpg"\n',
        "set default PDF brand image path",
    )
    old_logo = '''def _logo_flowable(settings: Dict[str, Any], width: float = 24 * mm, height: float = 24 * mm):
    logo_b64 = settings.get("logo_b64")
    if logo_b64:
        try:
            raw = base64.b64decode(logo_b64)
            return Image(BytesIO(raw), width=width, height=height, kind="proportional")
        except Exception:
            pass
    # Text fallback: deliberately generic; user can upload the real logo in Settings.
'''
    new_logo = '''def _logo_source(settings: Dict[str, Any]):
    """Return explicit custom logo or bundled Solar Rays image for ReportLab."""
    logo_b64 = settings.get("logo_b64")
    if logo_b64:
        try:
            return BytesIO(base64.b64decode(logo_b64, validate=True))
        except (ValueError, base64.binascii.Error):
            pass
    if DEFAULT_LOGO_PATH.is_file():
        return str(DEFAULT_LOGO_PATH)
    return None


def _logo_flowable(settings: Dict[str, Any], width: float = 24 * mm, height: float = 24 * mm):
    source = _logo_source(settings)
    if source is not None:
        try:
            return Image(source, width=width, height=height, kind="proportional")
        except Exception:
            pass
    # Last-resort fallback if neither bundled nor custom image exists.
'''
    source = replace_once(source, old_logo, new_logo, "embed branded PDF logo on page one")
    source = replace_once(
        source,
        '    canvas.setFillColor(NAVY)\n    canvas.setFont("Helvetica-Bold", 7.5)\n    canvas.drawString(15 * mm, PAGE_H - 6 * mm, settings.get("company_name", "Solar Rays Energy Solutions LLP"))\n',
        '    canvas.setFillColor(NAVY)\n'
        '    company_x = 15 * mm\n'
        '    logo_source = _logo_source(settings)\n'
        '    if logo_source is not None:\n'
        '        try:\n'
        '            canvas.drawImage(ImageReader(logo_source), 15 * mm, PAGE_H - 8.5 * mm,\n'
        '                             width=7.5 * mm, height=7.5 * mm,\n'
        '                             preserveAspectRatio=True, mask="auto")\n'
        '            company_x = 25 * mm\n'
        '        except Exception:\n'
        '            pass\n'
        '    canvas.setFont("Helvetica-Bold", 7.5)\n'
        '    canvas.drawString(company_x, PAGE_H - 6 * mm, settings.get("company_name", "Solar Rays Energy Solutions LLP"))\n',
        "include Solar Rays logo on every PDF page",
    )
    return source


def change_app_corporate(source: str) -> str:
    """Put verified statutory particulars on the app and expose each generic specification."""
    if 'CORPORATE_DETAILS_VERSION = ' in source:
        return source  # This complete update was already installed.

    source = replace_once(
        source,
        'LOGO_ASSET_VERSION = "solarnew-2026-10"\n',
        'LOGO_ASSET_VERSION = "solarnew-2026-10"\n'
        f'CORPORATE_DETAILS_VERSION = "{CORPORATE_VERSION}"\n'
        'LEGAL_ADDRESS = "12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow, Uttar Pradesh, 226029"\n'
        'LEGAL_GSTIN = "09AFUFS6953D1ZA"\n'
        'LEGAL_STATE_CODE = "09"\n'
        'LEGAL_STATE = "Uttar Pradesh"\n',
        "define the legal identity",
    )

    source = replace_once(
        source,
        '    "gstin": "",\n    "registered_address": "",\n    "office_address": "",\n',
        '    "gstin": LEGAL_GSTIN,\n'
        '    "state_code": LEGAL_STATE_CODE,\n'
        '    "state": LEGAL_STATE,\n'
        '    "registered_address": LEGAL_ADDRESS,\n'
        '    "office_address": LEGAL_ADDRESS,\n',
        "prefill statutory details on fresh installs",
    )

    source = replace_once(
        source,
        '    return merged\n\n\ndef save_settings(settings: Dict[str, Any]):\n',
        '''    # One-time migration for installations with an existing SQLite settings row.
    # The statutory identity supplied by the company supersedes old blank fields.
    # After this migration, saved edits to Company Settings remain available.
    if merged.get("_corporate_details_version") != CORPORATE_DETAILS_VERSION:
        merged.update({
            "company_name": "SOLAR RAYS ENERGY SOLUTIONS LLP",
            "gstin": LEGAL_GSTIN,
            "registered_address": LEGAL_ADDRESS,
            "office_address": LEGAL_ADDRESS,
            "state_code": LEGAL_STATE_CODE,
            "state": LEGAL_STATE,
            "_corporate_details_version": CORPORATE_DETAILS_VERSION,
        })
        save_settings(merged)
    merged["company_name"] = str(merged.get("company_name") or "SOLAR RAYS ENERGY SOLUTIONS LLP").upper()
    return merged


def save_settings(settings: Dict[str, Any]):
''',
        "migrate previous installations' legal details",
    )

    if "settings['company_name'].title()" not in source:
        raise ValueError("Expected Streamlit title-case heading is absent.")
    source = source.replace("settings['company_name'].title()", "settings['company_name'].upper()")

    source = replace_once(
        source,
        'create_tab, history_tab, settings_tab = st.tabs(["➕ New Quotation", "📚 Quotation History", "⚙️ Company Settings"])\n',
        '''st.markdown(
    f"**Registered Company:** {settings['company_name'].upper()}  \\n"
    f"**Registered Address:** {settings.get('registered_address', LEGAL_ADDRESS)}  \\n"
    f"**GSTIN:** {settings.get('gstin', LEGAL_GSTIN)}  |  "
    f"**State Code:** {settings.get('state_code', LEGAL_STATE_CODE)}  |  "
    f"**State:** {settings.get('state', LEGAL_STATE)}"
)

create_tab, history_tab, settings_tab = st.tabs(["➕ New Quotation", "📚 Quotation History", "⚙️ Company Settings"])
''',
        "display registered details on the webpage",
    )

    # Generic design/make fields work in tandem with both pre-existing editable
    # tables. A row is modified only when its particular text input changes.
    generic_controls = '''    st.caption(
        "All BOQ and material cells remain editable. Open the section below to enter "
        "specific makes, manufacturers or quantities wherever a generic value "
        "such as 'As per approved design' or 'Standard approved make' appears."
    )

    def apply_manual_specification(table_key, serial_no, column, default_value, field_key):
        frame = st.session_state[table_key].copy()
        matches = frame.index[frame["S.No."] == serial_no].tolist()
        if matches:
            typed = str(st.session_state.get(field_key, "")).strip()
            frame.at[matches[0], column] = typed if typed else default_value
            st.session_state[table_key] = frame
            st.session_state.editor_version += 1

    with st.expander("✍️ Enter specific makes / design details", expanded=False):
        st.caption("Each field updates the corresponding BOQ or material row and is included in the PDF.")
        generic_defaults = {
            "Make": {"As per approved design", "Standard approved make", "As per site design", "As selected"},
            "Quantity": {"As per system", "As per module layout"},
        }
        for section, table_key, reference_rows, label_col in (
            ("BOQ", "boq_df", default_boq(project), "Description"),
            ("Materials", "material_df", default_materials(project), "Component"),
        ):
            st.markdown(f"**{section} — custom entries**")
            for reference in reference_rows:
                serial_no = reference["S.No."]
                for column, placeholders in generic_defaults.items():
                    existing_default = str(reference.get(column, ""))
                    if existing_default not in placeholders:
                        continue
                    field_key = f"manual_design_{section.lower()}_{serial_no}_{column.lower()}"
                    st.text_input(
                        f"{reference[label_col]} — {column}",
                        key=field_key,
                        placeholder=f"Enter details instead of '{existing_default}'",
                        on_change=apply_manual_specification,
                        args=(table_key, serial_no, column, existing_default, field_key),
                    )

'''
    source = replace_once(
        source,
        '    st.subheader("Bill of Quantities")\n',
        '    st.subheader("Bill of Quantities")\n' + generic_controls,
        "add per-component manual make and quantity entry fields",
    )

    source = replace_once(
        source,
        '        st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1\n\n    st.divider()\n    st.subheader("Bill of Quantities")',
        '''        st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1
        # A new technical configuration starts with a clean set of manual fields.
        for widget_key in list(st.session_state.keys()):
            if str(widget_key).startswith("manual_design_"):
                del st.session_state[widget_key]

    st.divider()
    st.subheader("Bill of Quantities")''',
        "reset specification controls with a new project configuration",
    )

    source = replace_once(
        source,
        '    st.caption("These details are printed on every quotation. The defaults below use only public details available on the company website; fill in your legal, tax and banking details before production use.")',
        '    st.caption("The legal name, registered address, GSTIN, state code and state are prefilled on the webpage and every new quotation PDF. Verify the details before issuing quotations.")',
        "update company settings instructions",
    )
    source = replace_once(
        source,
        '        registered_address = s2.text_area("Registered / office address", value=settings.get("registered_address", ""), height=90)\n',
        '        registered_address = s2.text_area("Registered / office address", value=settings.get("registered_address", LEGAL_ADDRESS), height=90)\n'
        '        state_code = s2.text_input("State Code", value=settings.get("state_code", LEGAL_STATE_CODE))\n'
        '        state = s2.text_input("State", value=settings.get("state", LEGAL_STATE))\n',
        "provide state and state-code fields in company settings",
    )
    source = replace_once(
        source,
        '                "company_name": company_name.strip(),\n',
        '                "company_name": company_name.strip().upper(),\n',
        "preserve LLP uppercase when saving company settings",
    )
    source = replace_once(
        source,
        '                "gstin": gstin.strip(),\n',
        '                "gstin": gstin.strip().upper(),\n'
        '                "state_code": state_code.strip(),\n'
        '                "state": state.strip(),\n',
        "save state and state code",
    )
    source = replace_once(
        source,
        '                "_logo_asset_version": LOGO_ASSET_VERSION,\n',
        '                "_logo_asset_version": LOGO_ASSET_VERSION,\n'
        '                "_corporate_details_version": CORPORATE_DETAILS_VERSION,\n',
        "prevent legal migration repeating after saving user edits",
    )
    return source


def change_pdf_corporate(source: str) -> str:
    """Put registered company particulars on quotation pages 1 and 3."""
    if 'PDF_LEGAL_ADDRESS = ' in source:
        return source  # Already installed.

    source = replace_once(
        source,
        'DEFAULT_LOGO_PATH = Path(__file__).resolve().parent / "LOGO_SOLARNEW.jpg"\n',
        'DEFAULT_LOGO_PATH = Path(__file__).resolve().parent / "LOGO_SOLARNEW.jpg"\n'
        'PDF_LEGAL_ADDRESS = "12A/220, VRINDAVAN COLONY Utrahtia Railway Station Lucknow, Lucknow, Uttar Pradesh, 226029"\n'
        'PDF_LEGAL_GSTIN = "09AFUFS6953D1ZA"\n',
        "register corporate PDF default details",
    )
    source = replace_once(
        source,
        '''            f"<b>{settings.get('company_name', 'Solar Rays Energy Solutions LLP')}</b><br/>"''',
        '''            f"<b>{str(settings.get('company_name', 'SOLAR RAYS ENERGY SOLUTIONS LLP')).upper()}</b><br/>"''',
        "keep PDF company header uppercase",
    )
    source = replace_once(
        source,
        '    story += [Spacer(1, 6 * mm), brand, Spacer(1, 11 * mm)]\n',
        '''    office_address = settings.get("registered_address") or settings.get("office_address") or PDF_LEGAL_ADDRESS
    story += [
        Spacer(1, 3 * mm), brand, Spacer(1, 3 * mm),
        _para(f"Registered Office: {office_address}", styles["small"]),
        _para(
            f"GSTIN: {settings.get('gstin') or PDF_LEGAL_GSTIN}   |   "
            f"State Code: {settings.get('state_code') or '09'}   |   "
            f"State: {settings.get('state') or 'Uttar Pradesh'}",
            styles["small"],
        ),
        Spacer(1, 6 * mm),
    ]
''',
        "print the statutory identity next to PDF cover logo",
    )
    source = replace_once(
        source,
        '        ("Company", settings.get("company_name", "Solar Rays Energy Solutions LLP")),\n        ("GSTIN", settings.get("gstin", "")),\n',
        '        ("Company", str(settings.get("company_name", "SOLAR RAYS ENERGY SOLUTIONS LLP")).upper()),\n'
        '        ("GSTIN", settings.get("gstin") or PDF_LEGAL_GSTIN),\n'
        '        ("State Code", settings.get("state_code") or "09"),\n'
        '        ("State", settings.get("state") or "Uttar Pradesh"),\n',
        "include state and state code in PDF company details",
    )
    source = replace_once(
        source,
        '    registered = settings.get("registered_address") or settings.get("office_address") or ""\n',
        '    registered = settings.get("registered_address") or settings.get("office_address") or PDF_LEGAL_ADDRESS\n',
        "default PDF address",
    )
    source = replace_once(
        source,
        '''    story.append(_para(f"For {settings.get('company_name', 'Solar Rays Energy Solutions LLP')}", styles["small_bold"]))''',
        '''    story.append(_para(f"For {str(settings.get('company_name', 'SOLAR RAYS ENERGY SOLUTIONS LLP')).upper()}", styles["small_bold"]))''',
        "keep PDF signatory heading uppercase",
    )
    source = replace_once(
        source,
        '    canvas.drawString(company_x, PAGE_H - 6 * mm, settings.get("company_name", "Solar Rays Energy Solutions LLP"))\n',
        '    canvas.drawString(company_x, PAGE_H - 6 * mm, str(settings.get("company_name", "SOLAR RAYS ENERGY SOLUTIONS LLP")).upper())\n',
        "uppercase PDF page header company name",
    )
    return source


def main() -> int:
    app_path, pdf_path, logo_path = (ROOT / x for x in ("app.py", "pdf_engine.py", "LOGO_SOLARNEW.jpg"))
    if not app_path.is_file() or not pdf_path.is_file():
        print("ERROR: Copy this script and LOGO_SOLARNEW.jpg next to app.py and pdf_engine.py.", file=sys.stderr)
        return 1
    if not logo_path.is_file():
        print("ERROR: LOGO_SOLARNEW.jpg is missing.", file=sys.stderr)
        return 1

    originals = {app_path: app_path.read_text(encoding="utf-8"), pdf_path: pdf_path.read_text(encoding="utf-8")}
    try:
        # Supports both the original GitHub repository and repositories on
        # which the earlier Solar Rays logo/module-make patch was installed.
        logo_app = originals[app_path] if 'LOGO_ASSET_VERSION = ' in originals[app_path] else change_app(originals[app_path])
        logo_pdf = originals[pdf_path] if 'def _logo_source(settings:' in originals[pdf_path] else change_pdf(originals[pdf_path])
        changed = {
            app_path: change_app_corporate(logo_app),
            pdf_path: change_pdf_corporate(logo_pdf),
        }
        # Validate the complete new Python source before changing either file.
        for path, content in changed.items():
            ast.parse(content, filename=str(path))
    except (ValueError, SyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path, content in changed.items():
        if content == originals[path]:
            print(f"Unchanged: {path.name} (already updated)")
        else:
            backup = path.with_name(path.name + f".bak_{timestamp}")
            shutil.copy2(path, backup)
            path.write_text(content, encoding="utf-8")
            print(f"Updated: {path.name}; backup: {backup.name}")
    print("SUCCESS: Corporate identity, logo, manual module/design makes and PDF content are configured.")
    print("Review changes with git diff, then commit and push them along with LOGO_SOLARNEW.jpg.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
