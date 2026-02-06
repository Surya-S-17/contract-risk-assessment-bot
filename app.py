import streamlit as st
import pdfplumber
from docx import Document
import google.generativeai as genai
import json
import re

# ---------------- CONFIG ---------------- #

st.set_page_config(page_title="LLM Contract Risk Analyzer", layout="centered")
st.title("📄 LLM-Powered Contract Risk Analyzer")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

CLAUSES = [
    "Termination",
    "Liability",
    "Indemnity",
    "Jurisdiction",
    "Confidentiality",
    "Payment & Fees",
    "Risk Allocation"
]

RISK_ORDER = {"Low": 1, "Medium": 2, "High": 3}

# ---------------- UTILS ---------------- #

def clean_json(text):
    text = re.sub(r"```json|```", "", text)
    return text.strip()

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + "\n"
        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""

def chunk_text(text, max_chars=3000):
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 150]
    chunks, current = [], ""

    for p in paragraphs:
        if len(current) + len(p) < max_chars:
            current += p + "\n"
        else:
            chunks.append(current)
            current = p + "\n"

    if current:
        chunks.append(current)

    return chunks

# ---------------- PASS 1: CLAUSE PRESENCE ---------------- #

def detect_clauses(chunk):
    prompt = f"""
You are a legal document classifier.

Task:
Determine ONLY whether each clause type is PRESENT in the text.
Do NOT assess risk.

Rules:
- If obligations, responsibilities, rights, costs, or restrictions exist → PRESENT = true
- Be conservative: when in doubt, mark true

Return ONLY valid JSON:

{{
  "Termination": true/false,
  "Liability": true/false,
  "Indemnity": true/false,
  "Jurisdiction": true/false,
  "Confidentiality": true/false,
  "Payment & Fees": true/false,
  "Risk Allocation": true/false
}}

Text:
\"\"\"{chunk}\"\"\"
"""
    resp = model.generate_content(prompt)
    return json.loads(clean_json(resp.text))

# ---------------- PASS 2: RISK ASSESSMENT ---------------- #

def assess_risk(clause, chunk):
    prompt = f"""
You are a legal risk analyst.

Clause: {clause}

Risk rubric:

HIGH:
- Unlimited or broad liability
- Sole responsibility
- Broad indemnification
- Unilateral termination
- Costs borne without cap

MEDIUM:
- Liability or termination with procedures
- Shared responsibility
- Conditional payments

LOW:
- Explicit caps
- Balanced obligations
- Mutual protections

Rules:
- Be conservative
- When unsure → choose MEDIUM

Return ONLY valid JSON:

{{
  "risk": "Low/Medium/High",
  "reason": "Short justification"
}}

Text:
\"\"\"{chunk}\"\"\"
"""
    resp = model.generate_content(prompt)
    return json.loads(clean_json(resp.text))

# ---------------- AGGREGATION ---------------- #

def analyze_document(text):
    chunks = chunk_text(text)
    clause_present = {c: False for c in CLAUSES}
    clause_risk = {}

    for chunk in chunks:
        presence = detect_clauses(chunk)

        for clause, is_present in presence.items():
            if is_present:
                clause_present[clause] = True
                risk_data = assess_risk(clause, chunk)

                if clause not in clause_risk:
                    clause_risk[clause] = risk_data
                else:
                    if RISK_ORDER[risk_data["risk"]] > RISK_ORDER[clause_risk[clause]["risk"]]:
                        clause_risk[clause] = risk_data

    # ---------------- SANITY GUARDRAILS ---------------- #

    lower_text = text.lower()

    if "indemnify" in lower_text or "hold harmless" in lower_text:
        clause_risk["Indemnity"] = {
            "risk": "High",
            "reason": "Indemnification obligations detected"
        }

    if "liability" in lower_text and "limit" not in lower_text:
        clause_risk["Liability"] = {
            "risk": "High",
            "reason": "Liability obligations without explicit limitation"
        }

    return clause_risk

# ---------------- UI ---------------- #

uploaded_file = st.file_uploader(
    "Upload Contract (PDF / DOCX / TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    with st.spinner("Analyzing contract using Gemini Pro..."):
        text = extract_text(uploaded_file)
        results = analyze_document(text)

    st.success("Analysis Complete")

    if results:
        for clause, info in results.items():
            st.subheader(clause)
            st.write("🔴 Risk Level:", info["risk"])
            st.write("📝 Reason:", info["reason"])
    else:
        st.info("No significant legal risks detected.")
