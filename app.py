import streamlit as st
import pdfplumber
from docx import Document
import google.generativeai as genai
import json
import re

# ================== CONFIG ================== #

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

# ================== UTILS ================== #

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        return text

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return "\n".join(p.text for p in doc.paragraphs)

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8")

    return ""

def chunk_text(text, max_chars=3000):
    # GUARANTEED chunking (no empty chunks)
    text = re.sub(r"\n+", "\n", text)
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def extract_json(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON returned by Gemini")
    return json.loads(match.group())

# ================== PASS 1: PRESENCE ================== #

def detect_clauses(chunk):
    prompt = f"""
You are a legal document classifier.

Task:
ONLY detect whether each clause type is PRESENT.

Rules:
- If obligations, responsibilities, rights, costs, or restrictions exist → PRESENT = true
- Be conservative: when unsure, mark true
- DO NOT assess risk

Return ONLY JSON:

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
    return extract_json(resp.text)

# ================== PASS 2: RISK ================== #

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
- Procedural termination
- Shared responsibility
- Conditional payments

LOW:
- Explicit caps
- Mutual protections

Rules:
- Be conservative
- If unsure → MEDIUM

Return ONLY JSON:

{{
  "risk": "Low/Medium/High",
  "reason": "Short justification"
}}

Text:
\"\"\"{chunk}\"\"\"
"""
    resp = model.generate_content(prompt)
    return extract_json(resp.text)

# ================== MAIN ANALYSIS ================== #

def analyze_document(text):
    chunks = chunk_text(text)
    st.write("DEBUG: Total chunks =", len(chunks))

    clause_risk = {}

    for idx, chunk in enumerate(chunks):
        st.write(f"DEBUG: Analyzing chunk {idx+1}")
        try:
            presence = detect_clauses(chunk)
            st.write("DEBUG: Presence =", presence)

            for clause, present in presence.items():
                if present:
                    risk_data = assess_risk(clause, chunk)

                    if clause not in clause_risk:
                        clause_risk[clause] = risk_data
                    else:
                        if RISK_ORDER[risk_data["risk"]] > RISK_ORDER[clause_risk[clause]["risk"]]:
                            clause_risk[clause] = risk_data

        except Exception as e:
            st.error(f"LLM error on chunk {idx+1}: {e}")

    # ================== GUARDRAILS ================== #

    lower = text.lower()

    if "indemnify" in lower or "hold harmless" in lower:
        clause_risk["Indemnity"] = {
            "risk": "High",
            "reason": "Indemnification obligations detected"
        }

    if "liability" in lower and "limit" not in lower:
        clause_risk["Liability"] = {
            "risk": "High",
            "reason": "Liability obligations without explicit limitation"
        }

    if not clause_risk:
        clause_risk["General Contract Risk"] = {
            "risk": "Medium",
            "reason": "Complex legal contract detected; manual review recommended"
        }

    return clause_risk

# ================== UI ================== #

uploaded_file = st.file_uploader(
    "Upload Contract (PDF / DOCX / TXT)",
    type=["pdf", "docx", "txt"]
)

if uploaded_file:
    with st.spinner("Analyzing contract using Gemini Pro..."):
        text = extract_text(uploaded_file)
        results = analyze_document(text)

    st.success("Analysis Complete")

    for clause, info in results.items():
        st.subheader(clause)
        st.write("🔴 Risk Level:", info["risk"])
        st.write("📝 Reason:", info["reason"])
