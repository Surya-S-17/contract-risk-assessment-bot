import streamlit as st
import pdfplumber
from docx import Document
import re

st.set_page_config(page_title="Contract Risk Analyzer", layout="centered")
st.title("📄 Contract Risk Analyzer")

# ---------------- UTILS ---------------- #

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text.lower()

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs).lower()

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8").lower()

    return ""

# ---------------- RISK ENGINE ---------------- #

def detect_risks(text):
    results = {}

    # TERMINATION
    if re.search(r"terminate|termination|suspend|discontinue", text):
        risk = "Medium"
        reason = "Termination-related provisions detected"
        if re.search(r"without notice|sole discretion|immediate termination", text):
            risk = "High"
            reason = "Unilateral or immediate termination rights detected"
        results["Termination"] = {"risk": risk, "reason": reason}

    # LIABILITY
    if re.search(r"liable|liability|responsible for|at own expense", text):
        risk = "Medium"
        reason = "Liability obligations present"
        if re.search(r"unlimited|without limitation|indemnify|hold harmless", text):
            risk = "High"
            reason = "Broad or unlimited liability / indemnity detected"
        results["Liability"] = {"risk": risk, "reason": reason}

    # INDEMNITY
    if re.search(r"indemnify|hold harmless", text):
        results["Indemnity"] = {
            "risk": "High",
            "reason": "Indemnification obligations detected"
        }

    # JURISDICTION
    if re.search(r"jurisdiction|governing law|laws of", text):
        risk = "Low"
        reason = "Jurisdiction clause detected"
        if re.search(r"foreign|exclusive jurisdiction", text):
            risk = "Medium"
            reason = "Restrictive or foreign jurisdiction detected"
        results["Jurisdiction"] = {"risk": risk, "reason": reason}

    # CONFIDENTIALITY
    if re.search(r"confidential|non-disclosure", text):
        risk = "Medium"
        reason = "Confidentiality obligations present"
        if re.search(r"perpetual|indefinite", text):
            risk = "High"
            reason = "Indefinite confidentiality obligation detected"
        results["Confidentiality"] = {"risk": risk, "reason": reason}

    # PAYMENT & FEES
    if re.search(r"payment|fees|compensation|invoice", text):
        results["Payment & Fees"] = {
            "risk": "Medium",
            "reason": "Payment and fee-related terms detected"
        }

    if not results:
        results["General Contract Risk"] = {
            "risk": "Medium",
            "reason": "Complex legal contract detected; manual review recommended"
        }

    return results

# ---------------- UI HELPERS ---------------- #

def risk_badge(risk):
    if risk == "High":
        return "🔴 High Risk"
    if risk == "Medium":
        return "🟠 Medium Risk"
    return "🟢 Low Risk"

def overall_risk(risks):
    if any(v["risk"] == "High" for v in risks.values()):
        return "🔴 HIGH"
    if any(v["risk"] == "Medium" for v in risks.values()):
        return "🟠 MEDIUM"
    return "🟢 LOW"

# ---------------- UI ---------------- #

uploaded = st.file_uploader(
    "Upload Contract (PDF / DOCX / TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded:
    text = extract_text(uploaded)

    if len(text.strip()) < 200:
        st.error("❌ No readable text found (likely scanned PDF).")
    else:
        with st.spinner("Analyzing contract..."):
            risks = detect_risks(text)

        # 🔥 OVERALL SUMMARY
        st.markdown("## 📊 Overall Contract Risk")
        st.markdown(f"### {overall_risk(risks)}")

        st.divider()

        # 📌 CLAUSE DETAILS
        st.markdown("## 📑 Clause-wise Risk Analysis")

        for clause, info in risks.items():
            with st.expander(f"{clause} — {risk_badge(info['risk'])}", expanded=False):
                st.write("**Risk Level:**", info["risk"])
                st.write("**Reason:**", info["reason"])
