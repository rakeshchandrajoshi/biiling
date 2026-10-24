#!/usr/bin/env python3
"""Repair Solar Rays repository where app.py was overwritten with the updater.

Run from the checkout directory after placing this script, the bundled
apply_solar_rays_update.py, and LOGO_SOLARNEW.jpg beside app_old.py.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
OLD_APP = ROOT / "app_old.py"
PDF = ROOT / "pdf_engine.py"
UPDATER = ROOT / "apply_solar_rays_update.py"
LOGO = ROOT / "LOGO_SOLARNEW.jpg"


def is_streamlit_application(contents: str) -> bool:
    return "import streamlit as st" in contents and "st.set_page_config(" in contents


def is_updater(contents: str) -> bool:
    return "def change_app(" in contents and "apply_solar_rays_update.py" in contents


def main() -> int:
    if not PDF.is_file() or not UPDATER.is_file() or not LOGO.is_file():
        print("ERROR: pdf_engine.py, apply_solar_rays_update.py and LOGO_SOLARNEW.jpg must be in this folder.", file=sys.stderr)
        return 1

    current = APP.read_text(encoding="utf-8") if APP.is_file() else ""
    restored = False
    backup = None
    if not is_streamlit_application(current):
        if not OLD_APP.is_file() or not is_streamlit_application(OLD_APP.read_text(encoding="utf-8")):
            print("ERROR: Cannot find the intact Streamlit application in app_old.py; nothing has been replaced.", file=sys.stderr)
            return 1
        if APP.is_file() and not is_updater(current):
            print("ERROR: app.py is neither the Streamlit app nor the known updater; leaving it unchanged.", file=sys.stderr)
            return 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if APP.is_file():
            backup = APP.with_name(f"app.py.wrong_entrypoint_{timestamp}.bak")
            shutil.copy2(APP, backup)
        shutil.copy2(OLD_APP, APP)
        restored = True
        print("Restored the actual Streamlit application from app_old.py.")
    else:
        print("app.py is already a Streamlit application.")

    # A corporate updater is copied alongside this repair script. It checks
    # expected patterns and validates syntax before writing source files.
    result = subprocess.run([sys.executable, str(UPDATER)], cwd=ROOT, check=False)
    if result.returncode:
        if restored:
            print("The Streamlit entry point was restored, but the optional update failed.", file=sys.stderr)
            print("Check the reported replacement error above. No repository commit was made.", file=sys.stderr)
        return result.returncode

    app_content = APP.read_text(encoding="utf-8")
    pdf_content = PDF.read_text(encoding="utf-8")
    for filename, content in (("app.py", app_content), ("pdf_engine.py", pdf_content)):
        ast.parse(content, filename=filename)
    checks = {
        "Streamlit entry point restored": is_streamlit_application(app_content),
        "Company identity": "09AFUFS6953D1ZA" in app_content,
        "Uppercase company name": "settings['company_name'].upper()" in app_content,
        "Custom solar-module make": "panel_brand_choice" in app_content,
        "Manual design specifications": "apply_manual_specification" in app_content,
        "Logo embedded in PDF": "_logo_source(settings)" in pdf_content,
        "State code in PDF": '"State Code"' in pdf_content,
    }
    for name, ok in checks.items():
        print(f"{'OK' if ok else 'MISSING'}: {name}")
    if not all(checks.values()):
        print("ERROR: One or more verification checks failed.", file=sys.stderr)
        return 2
    print("SUCCESS: app.py is now the real Streamlit app, with the requested updates.")
    print("Next: git add app.py pdf_engine.py LOGO_SOLARNEW.jpg && git commit -m 'Repair Streamlit startup and corporate quotation' && git push origin main")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
