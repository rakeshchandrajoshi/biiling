from __future__ import annotations

import base64
import json
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from pdf_engine import default_boq, default_materials, generate_quote_pdf

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "solar_quotes.db"

st.set_page_config(
    page_title="Solar Rays Quotation System",
    page_icon="☀️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.35rem; padding-bottom: 2rem; max-width: 1500px;}
    h1, h2, h3 {color: #0f172a;}
    .sr-hero {
        border: 1px solid #e2e8f0; border-radius: 18px; padding: 20px 24px;
        background: linear-gradient(135deg, #fff7d6 0%, #ffffff 50%, #f0fdf4 100%);
        margin-bottom: 14px;
    }
    .sr-hero h1 {margin: 0 0 4px 0; font-size: 2rem;}
    .sr-hero p {margin: 0; color: #475569;}
    .sr-card {border:1px solid #e2e8f0; border-radius:14px; padding:14px 16px; background:#ffffff;}
    div[data-testid="stMetric"] {border:1px solid #e2e8f0; border-radius:14px; padding:12px 14px; background:#fff;}
    .small-note {font-size: 0.86rem; color: #64748b;}
    </style>
    """,
    unsafe_allow_html=True,
)


DEFAULT_SETTINGS: Dict[str, Any] = {
    "company_name": "SOLAR RAYS ENERGY SOLUTIONS LLP",
    "tagline": "Clean solar. Smarter savings.",
    "website": "https://solarraysenergy.com/",
    "phone1": "99365 33017",
    "phone2": "90050 93327",
    "email": "",
    "gstin": "",
    "registered_address": "",
    "office_address": "",
    "bank_account_name": "SOLAR RAYS ENERGY SOLUTIONS LLP",
    "bank_name": "",
    "bank_account": "",
    "ifsc": "",
    "bank_branch": "",
    "intro_text": (
        "Solar Rays Energy Solutions LLP designs, deploys and maintains high-performance rooftop solar systems "
        "focused on long-term savings, reliable engineering and energy independence."
    ),
    "logo_b64": "",
}


# -------------------------
# Database helpers
# -------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id=1),
                json_data TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_ref TEXT UNIQUE NOT NULL,
                quote_date TEXT NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT,
                capacity_kw REAL,
                system_type TEXT,
                grand_total REAL,
                status TEXT DEFAULT 'Draft',
                json_data TEXT NOT NULL,
                pdf_blob BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        row = conn.execute("SELECT id FROM settings WHERE id=1").fetchone()
        if not row:
            conn.execute("INSERT INTO settings(id, json_data) VALUES(1, ?)", (json.dumps(DEFAULT_SETTINGS),))
        conn.commit()


def load_settings() -> Dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute("SELECT json_data FROM settings WHERE id=1").fetchone()
    data = json.loads(row["json_data"]) if row else {}
    merged = DEFAULT_SETTINGS.copy()
    merged.update(data)
    return merged


def save_settings(settings: Dict[str, Any]):
    with get_conn() as conn:
        conn.execute("UPDATE settings SET json_data=? WHERE id=1", (json.dumps(settings),))
        conn.commit()


def save_quote(snapshot: Dict[str, Any], pdf_bytes: bytes):
    customer = snapshot["customer"]
    project = snapshot["project"]
    commercial = snapshot["commercial"]
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO quotations(
                quote_ref, quote_date, customer_name, phone, capacity_kw, system_type,
                grand_total, status, json_data, pdf_blob, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["quote_ref"],
                snapshot["quote_date"],
                customer.get("name", ""),
                customer.get("phone", ""),
                float(project.get("capacity_kw", 0) or 0),
                project.get("system_type", ""),
                float(commercial.get("grand_total", 0) or 0),
                "Draft",
                json.dumps(snapshot),
                sqlite3.Binary(pdf_bytes),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def list_quotes() -> pd.DataFrame:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, quote_ref, quote_date, customer_name, phone, capacity_kw,
                   system_type, grand_total, status, created_at
            FROM quotations ORDER BY id DESC
            """
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def get_quote_pdf(quote_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT quote_ref, pdf_blob FROM quotations WHERE id=?", (quote_id,)).fetchone()
    if not row:
        return None, None
    return row["quote_ref"], bytes(row["pdf_blob"])


def update_status(quote_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE quotations SET status=? WHERE id=?", (status, quote_id))
        conn.commit()


def delete_quote(quote_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM quotations WHERE id=?", (quote_id,))
        conn.commit()


def fy_label(d: date) -> str:
    if d.month >= 4:
        start = d.year
        end = (d.year + 1) % 100
    else:
        start = d.year - 1
        end = d.year % 100
    return f"{start}-{end:02d}"


def next_quote_ref(d: date, system_type: str) -> str:
    code = {"On-Grid": "ON", "Off-Grid": "OFF", "Hybrid": "HYB"}.get(system_type, "SOL")
    fy = fy_label(d)
    prefix = f"SRES/{fy}/{code}/"
    with get_conn() as conn:
        rows = conn.execute("SELECT quote_ref FROM quotations WHERE quote_ref LIKE ?", (prefix + "%",)).fetchall()
    nums = []
    for r in rows:
        try:
            nums.append(int(str(r["quote_ref"]).rsplit("/", 1)[-1]))
        except Exception:
            pass
    return prefix + f"{(max(nums) + 1) if nums else 1:04d}"


def df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    clean = df.fillna("")
    return clean.to_dict(orient="records")


def fmt_money(v: float) -> str:
    return f"₹{float(v):,.0f}"


init_db()
settings = load_settings()

st.markdown(
    f"""
    <div class="sr-hero">
      <h1>☀️ {settings['company_name'].title()}</h1>
      <p>Quotation Management System · Create, save and download professional solar proposals.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

create_tab, history_tab, settings_tab = st.tabs(["➕ New Quotation", "📚 Quotation History", "⚙️ Company Settings"])

# -------------------------
# New Quotation
# -------------------------
with create_tab:
    st.subheader("Customer & Project Details")

    c1, c2, c3 = st.columns([1.2, 1, 1])
    with c1:
        customer_name = st.text_input("Customer name *", placeholder="e.g. Yas Srivastava")
        customer_address = st.text_area("Installation / billing address", height=90, placeholder="Full address")
    with c2:
        customer_phone = st.text_input("Mobile number", placeholder="98XXXXXXXX")
        customer_email = st.text_input("Email")
        customer_gstin = st.text_input("Customer GSTIN (optional)")
    with c3:
        quote_date = st.date_input("Quotation date", value=date.today())
        system_type = st.selectbox("System type", ["On-Grid", "Hybrid", "Off-Grid"])
        capacity_kw = st.number_input("Plant capacity (kW)", min_value=0.5, max_value=1000.0, value=5.0, step=0.5)

    st.divider()
    st.subheader("Technical Configuration")

    p1, p2, p3, p4 = st.columns(4)
    panel_brand = p1.selectbox("Solar module make", ["Waaree", "Adani Solar", "Vikram Solar", "RenewSys", "Tata Power Solar", "Other"])
    panel_wattage = p2.number_input("Module wattage (Wp)", min_value=300, max_value=800, value=580, step=5)
    phase = p3.selectbox("Phase", ["Single Phase", "Three Phase"])
    inverter_brand = p4.selectbox("Inverter make", ["Luminous", "Solis", "Sungrow", "Growatt", "GoodWe", "Fronius", "Other"])

    q1, q2, q3 = st.columns(3)
    inverter_capacity_kw = q1.number_input("Inverter capacity (kW)", min_value=0.5, max_value=1000.0, value=float(capacity_kw), step=0.5)
    structure_make = q2.selectbox("Mounting structure", ["GI / HDG", "Pre-GI", "Aluminium", "As per site design"])
    net_metering_included = q3.selectbox("Net-metering scope", ["Included / assisted", "Customer scope", "Not applicable"])

    panel_count = int(math.ceil(capacity_kw * 1000 / panel_wattage))
    st.info(f"Suggested module quantity: **{panel_count} panels** × {panel_wattage} Wp = {panel_count * panel_wattage / 1000:.2f} kWp DC installed capacity.")

    project = {
        "system_type": system_type,
        "capacity_kw": capacity_kw,
        "phase": phase,
        "panel_brand": panel_brand,
        "panel_wattage": panel_wattage,
        "panel_count": panel_count,
        "inverter_brand": inverter_brand,
        "inverter_capacity_kw": inverter_capacity_kw,
        "structure_make": structure_make,
    }

    sig = json.dumps(project, sort_keys=True)
    if st.session_state.get("project_sig") != sig:
        st.session_state.project_sig = sig
        st.session_state.boq_df = pd.DataFrame(default_boq(project))
        st.session_state.material_df = pd.DataFrame(default_materials(project))
        st.session_state.editor_version = st.session_state.get("editor_version", 0) + 1

    st.divider()
    st.subheader("Bill of Quantities")
    st.caption("The system pre-fills a standard BOQ. You can edit any description, make, unit or quantity before generating the PDF.")
    edited_boq = st.data_editor(
        st.session_state.boq_df,
        num_rows="dynamic",
        use_container_width=True,
        key=f"boq_editor_{st.session_state.editor_version}",
    )
    st.session_state.boq_df = edited_boq

    with st.expander("Detailed material specification", expanded=False):
        edited_material = st.data_editor(
            st.session_state.material_df,
            num_rows="dynamic",
            use_container_width=True,
            key=f"material_editor_{st.session_state.editor_version}",
        )
        st.session_state.material_df = edited_material

    st.divider()
    st.subheader("Commercials")
    a1, a2, a3, a4 = st.columns(4)
    pricing_mode = a1.selectbox("Pricing mode", ["Lump sum", "Rate per kW"])
    if pricing_mode == "Rate per kW":
        rate_per_kw = a2.number_input("Rate per kW (₹)", min_value=0.0, value=50000.0, step=1000.0)
        basic_amount = float(capacity_kw) * float(rate_per_kw)
        a2.caption(f"Basic amount: {fmt_money(basic_amount)}")
    else:
        rate_per_kw = 0.0
        basic_amount = a2.number_input("Basic amount (₹)", min_value=0.0, value=250000.0, step=5000.0)

    discount = a3.number_input("Discount (₹)", min_value=0.0, value=0.0, step=1000.0)
    gst_rate = a4.number_input("GST (%)", min_value=0.0, max_value=28.0, value=5.0, step=0.5)

    b1, b2, b3 = st.columns(3)
    other_charges = b1.number_input("Other charges (₹)", min_value=0.0, value=0.0, step=500.0)
    central_subsidy = b2.number_input("Central subsidy - indicative (₹)", min_value=0.0, value=0.0, step=1000.0)
    state_subsidy = b3.number_input("State subsidy - indicative (₹)", min_value=0.0, value=0.0, step=1000.0)

    taxable_value = max(float(basic_amount) - float(discount), 0.0)
    gst_amount = taxable_value * float(gst_rate) / 100.0
    grand_total = taxable_value + gst_amount + float(other_charges)
    total_subsidy = float(central_subsidy) + float(state_subsidy)
    effective_price = max(grand_total - total_subsidy, 0.0)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Taxable value", fmt_money(taxable_value))
    m2.metric("GST", fmt_money(gst_amount))
    m3.metric("Grand total", fmt_money(grand_total))
    m4.metric("Effective cost", fmt_money(effective_price), delta=f"Subsidy {fmt_money(total_subsidy)}" if total_subsidy else None, delta_color="off")

    subsidy_note = st.text_area(
        "Subsidy note",
        value="Subsidy is indicative and subject to scheme eligibility, prevailing government rules, portal approval and successful completion of the required process.",
        height=75,
    )

    st.divider()
    st.subheader("Terms & Conditions")
    t1, t2 = st.columns(2)
    validity_days = t1.number_input("Quotation validity (days)", min_value=1, max_value=90, value=10)
    payment_terms = t1.text_input("Payment terms", value="100% advance, or as mutually agreed in the final purchase order.")
    delivery_timeline = t2.text_input("Delivery / commissioning timeline", value="Within 1-2 weeks from confirmed order and advance, subject to site readiness.")
    warranty = t2.text_input("Warranty", value="As per OEM warranty and final order terms.")
    material_note = st.text_area(
        "Material note",
        value="Final makes, models and quantities are subject to approved design, site survey, availability and the mutually accepted purchase order. Any deviation requested by the customer may affect price and delivery.",
        height=80,
    )

    suggested_ref = next_quote_ref(quote_date, system_type)
    quote_ref = st.text_input("Quotation reference", value=suggested_ref, help="You may edit the automatically generated reference number.")

    missing_company = []
    if not settings.get("gstin"):
        missing_company.append("GSTIN")
    if not (settings.get("registered_address") or settings.get("office_address")):
        missing_company.append("company address")
    if missing_company:
        st.warning("Before sending a final quotation, please complete the Company Settings for: " + ", ".join(missing_company) + ".")

    build_col, clear_col = st.columns([1, 4])
    build = build_col.button("📄 Build Quotation PDF", type="primary", use_container_width=True)
    if clear_col.button("Reset BOQ to defaults"):
        st.session_state.boq_df = pd.DataFrame(default_boq(project))
        st.session_state.material_df = pd.DataFrame(default_materials(project))
        st.session_state.editor_version += 1
        st.rerun()

    if build:
        if not customer_name.strip():
            st.error("Please enter the customer name.")
        elif not quote_ref.strip():
            st.error("Please enter a quotation reference.")
        else:
            snapshot = {
                "quote_ref": quote_ref.strip(),
                "quote_date": quote_date.strftime("%d/%m/%Y"),
                "settings": settings,
                "customer": {
                    "name": customer_name.strip(),
                    "phone": customer_phone.strip(),
                    "email": customer_email.strip(),
                    "address": customer_address.strip(),
                    "gstin": customer_gstin.strip(),
                },
                "project": project,
                "boq": df_to_records(st.session_state.boq_df),
                "materials": df_to_records(st.session_state.material_df),
                "commercial": {
                    "pricing_mode": pricing_mode,
                    "rate_per_kw": rate_per_kw,
                    "basic_amount": basic_amount,
                    "discount": discount,
                    "taxable_value": taxable_value,
                    "gst_rate": gst_rate,
                    "gst_amount": gst_amount,
                    "other_charges": other_charges,
                    "grand_total": grand_total,
                    "central_subsidy": central_subsidy,
                    "state_subsidy": state_subsidy,
                    "total_subsidy": total_subsidy,
                    "effective_price": effective_price,
                    "subsidy_note": subsidy_note,
                },
                "terms": {
                    "validity_days": int(validity_days),
                    "payment_terms": payment_terms,
                    "delivery_timeline": delivery_timeline,
                    "net_metering": net_metering_included,
                    "warranty": warranty,
                    "material_note": material_note,
                },
            }
            try:
                pdf_bytes = generate_quote_pdf(snapshot)
                st.session_state.generated_quote = {"snapshot": snapshot, "pdf": pdf_bytes}
                st.success("Quotation PDF generated successfully.")
            except Exception as exc:
                st.exception(exc)

    generated = st.session_state.get("generated_quote")
    if generated:
        snapshot = generated["snapshot"]
        pdf_bytes = generated["pdf"]
        st.divider()
        st.subheader("Generated Quotation")
        x1, x2, x3 = st.columns([1, 1, 2])
        filename = snapshot["quote_ref"].replace("/", "-") + ".pdf"
        x1.download_button(
            "⬇️ Download PDF",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True,
        )
        if x2.button("💾 Save to History", use_container_width=True):
            try:
                save_quote(snapshot, pdf_bytes)
                st.success("Quotation saved to history.")
            except sqlite3.IntegrityError:
                st.error("This quotation reference already exists. Change the reference number or use the existing saved quotation.")
        x3.caption("The saved PDF is stored inside the local SQLite database. For production hosting, migrate the database to PostgreSQL/Supabase for durable multi-user storage.")

# -------------------------
# Quotation history
# -------------------------
with history_tab:
    st.subheader("Saved Quotations")
    hist = list_quotes()
    if hist.empty:
        st.info("No quotations saved yet.")
    else:
        search = st.text_input("Search customer / quotation / phone", key="history_search")
        filtered = hist.copy()
        if search.strip():
            term = search.strip().lower()
            mask = (
                filtered["quote_ref"].astype(str).str.lower().str.contains(term)
                | filtered["customer_name"].astype(str).str.lower().str.contains(term)
                | filtered["phone"].astype(str).str.lower().str.contains(term)
            )
            filtered = filtered[mask]

        show = filtered[["id", "quote_ref", "quote_date", "customer_name", "phone", "capacity_kw", "system_type", "grand_total", "status"]].copy()
        show["grand_total"] = show["grand_total"].map(lambda x: f"₹{float(x):,.0f}")
        st.dataframe(show, use_container_width=True, hide_index=True)

        ids = filtered["id"].tolist()
        if ids:
            selected_id = st.selectbox(
                "Select a quotation",
                ids,
                format_func=lambda qid: f"#{qid} · {filtered.loc[filtered['id'] == qid, 'quote_ref'].iloc[0]} · {filtered.loc[filtered['id'] == qid, 'customer_name'].iloc[0]}",
            )
            row = filtered[filtered["id"] == selected_id].iloc[0]
            h1, h2, h3, h4 = st.columns([1, 1, 1, 1])
            ref, saved_pdf = get_quote_pdf(int(selected_id))
            if saved_pdf:
                h1.download_button(
                    "⬇️ Download",
                    data=saved_pdf,
                    file_name=ref.replace("/", "-") + ".pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            new_status = h2.selectbox("Status", ["Draft", "Sent", "Accepted", "Rejected", "Expired"], index=["Draft", "Sent", "Accepted", "Rejected", "Expired"].index(row["status"]) if row["status"] in ["Draft", "Sent", "Accepted", "Rejected", "Expired"] else 0, label_visibility="collapsed")
            if h3.button("Update Status", use_container_width=True):
                update_status(int(selected_id), new_status)
                st.success("Status updated.")
                st.rerun()
            if h4.button("Delete", use_container_width=True):
                delete_quote(int(selected_id))
                st.warning("Quotation deleted.")
                st.rerun()

# -------------------------
# Company settings
# -------------------------
with settings_tab:
    st.subheader("Company Settings")
    st.caption("These details are printed on every quotation. The defaults below use only public details available on the company website; fill in your legal, tax and banking details before production use.")

    with st.form("settings_form"):
        s1, s2 = st.columns(2)
        company_name = s1.text_input("Company name", value=settings.get("company_name", ""))
        tagline = s1.text_input("Tagline", value=settings.get("tagline", ""))
        website = s1.text_input("Website", value=settings.get("website", ""))
        email = s1.text_input("Email", value=settings.get("email", ""))
        phone1 = s2.text_input("Phone 1", value=settings.get("phone1", ""))
        phone2 = s2.text_input("Phone 2", value=settings.get("phone2", ""))
        gstin = s2.text_input("GSTIN", value=settings.get("gstin", ""))
        registered_address = s2.text_area("Registered / office address", value=settings.get("registered_address", ""), height=90)

        st.markdown("#### Banking details")
        b1, b2 = st.columns(2)
        bank_account_name = b1.text_input("Account name", value=settings.get("bank_account_name", company_name))
        bank_name = b1.text_input("Bank name", value=settings.get("bank_name", ""))
        bank_account = b2.text_input("Account number", value=settings.get("bank_account", ""))
        ifsc = b2.text_input("IFSC", value=settings.get("ifsc", ""))
        bank_branch = b2.text_input("Branch", value=settings.get("bank_branch", ""))

        intro_text = st.text_area("Company introduction for page 1", value=settings.get("intro_text", ""), height=110)
        logo = st.file_uploader("Company logo (PNG/JPG)", type=["png", "jpg", "jpeg"], help="Optional. If omitted, a simple SR placeholder is shown in the PDF.")
        keep_logo = st.checkbox("Keep existing uploaded logo", value=True)

        submitted = st.form_submit_button("Save Company Settings", type="primary")
        if submitted:
            logo_b64 = settings.get("logo_b64", "") if keep_logo else ""
            if logo is not None:
                logo_b64 = base64.b64encode(logo.getvalue()).decode("ascii")
            updated = {
                "company_name": company_name.strip(),
                "tagline": tagline.strip(),
                "website": website.strip(),
                "phone1": phone1.strip(),
                "phone2": phone2.strip(),
                "email": email.strip(),
                "gstin": gstin.strip(),
                "registered_address": registered_address.strip(),
                "office_address": registered_address.strip(),
                "bank_account_name": bank_account_name.strip(),
                "bank_name": bank_name.strip(),
                "bank_account": bank_account.strip(),
                "ifsc": ifsc.strip(),
                "bank_branch": bank_branch.strip(),
                "intro_text": intro_text.strip(),
                "logo_b64": logo_b64,
            }
            save_settings(updated)
            st.success("Settings saved. Reloading with the new company details.")
            st.rerun()

    st.markdown("---")
    st.markdown(
        "<span class='small-note'>Prototype storage: local SQLite. For multi-user production use, connect PostgreSQL/Supabase and add authentication.</span>",
        unsafe_allow_html=True,
    )
