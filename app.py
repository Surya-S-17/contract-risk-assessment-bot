import streamlit as st
import pdfplumber
from docx import Document
import google.generativeai as genai
import json
import re

# ================== CONFIG ================== #

st.set_page_config(page_title="LLM Contract Risk Analyzer", layout="centered")
st.title("📄 LLM-Powered Contract Risk Analyzer")

# Configure Gemini (UPDATED MODEL)
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("models/gemini-1.5-pro")

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

# ================== UTILS ================== #

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""

def chunk_text(text, max_chars=3000):
    # Guaranteed chunking (never returns empty if text exists)
    text = re.sub(r"\n+", "\n", text)
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in Gemini response")
    return json.loads(match.group())

# ================== PASS 1: CLAUSE PRESENCE ================== #

def detect_clauses(chunk):
    prompt = f"""
You are a legal document classifier.

Task:
ONLY determine whether each clause type is PRESENT.
DO NOT assess risk.

Rules:
- If obligations, responsibilities, rights, costs, or restrictions exist → PRESENT = true
- Be conservative: if unsure, mark true

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
    response = model.generate_content(prompt)
    return extract_json(response.text)

# ================== PASS 2: RISK ASSESSMENT ================== #

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
- Termination with procedure or notice
- Shared responsibility
- Conditional or milestone-based payments

LOW:
- Explicit liability caps
- Balanced obligations
- Mutual protections

Rules:
- Be conservative
- If unsure → choose MEDIUM

Return ONLY valid JSON:

{{
  "risk": "Low/Medium/High",
  "reason": "Short justification"
}}

Text:
\"\"\"{chunk}\"\"\"
"""
    response = model.generate_content(prompt)
    return extract_json(response.text)

# ================== MAIN ANALYSIS ================== #

def analyze_document(text):
    chunks = chunk_text(text)
    st.write("DEBUG: Total chunks =", len(chunks))

    clause_risk = {}

    for idx, chunk in enumerate(chunks):
        st.write(f"DEBUG: Analyzing chunk {idx+1}")

        try:
            presence = detect_clauses(chunk)
            st.write("DEBUG: Clause presence =", presence)

            for clause, is_present in presence.items():
                if is_present:
                    risk_data = assess_risk(clause, chunk)

                    if clause not in clause_risk:
                        clause_risk[clause] = risk_data
                    else:
                        if RISK_ORDER[risk_data["risk"]] > RISK_ORDER[clause_risk[clause]["risk"]]:
                            clause_risk[clause] = risk_data

        except Exception as e:
            st.error(f"LLM error on chunk {idx+1}: {e}")

    # ================== LEGAL GUARDRAILS ================== #

    lower_text = text.lower()

    if "indemnify" in lower_text or "hold harmless" in lower_text:
        clause_risk["Indemnity"] = {
            "risk": "High",
            "reason": "Indemnification or hold-harmless obligations detected"
        }

    if "liability" in lower_text and "limit" not in lower_text:
        clause_risk["Liability"] = {
            "risk": "High",
            "reason": "Liability obligations detected without explicit limitation"
        }

    if not clause_risk:
        clause_risk["General Contract Risk"] = {
            "risk": "Medium",
            "reason": "Complex legal contract detected; manual legal review recommended"
        }

    return clause_risk

# ================== UI ================== #

uploaded_file = st.file_uploader(
    "Upload Contract (PDF / DOCX / TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    text = extract_text(uploaded_file)

    # IMPORTANT: handle scanned PDFs safely
    if len(text.strip()) < 200:
        st.error("❌ No readable text found in this file.")
        st.info("This appears to be a scanned PDF. Please upload a text-based PDF or DOCX.")
    else:
        with st.spinner("Analyzing contract using Gemini 1.5 Pro..."):
            results = analyze_document(text)

        st.success("Analysis Complete")

        for clause, info in results.items():
            st.subheader(clause)
            st.write("🔴 Risk Level:", info["risk"])
            st.write("📝 Reason:", info["reason"])
