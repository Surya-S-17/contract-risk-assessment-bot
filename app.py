import streamlit as st
import pdfplumber
from docx import Document
import requests
import json
import re

st.set_page_config(page_title="Contract Risk Analyzer", layout="centered")
st.title("📄 Contract Risk Analyzer (LLM-powered)")

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

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

def chunk_text(text, size=3000):
    return [text[i:i+size] for i in range(0, len(text), size)]

def extract_json(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("LLM did not return JSON")
    return json.loads(m.group())

def call_openai(prompt):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a legal risk analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1
    }

    resp = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)

    if resp.status_code != 200:
        raise RuntimeError(resp.text)

    content = resp.json()["choices"][0]["message"]["content"]
    return extract_json(content)

# ---------------- LLM ANALYSIS ---------------- #

def analyze_chunk(chunk):
    prompt = f"""
Analyze the contract text below.

For each clause:
- Decide if present
- Assign risk: Low / Medium / High
- Give short reason

Clauses:
Termination, Liability, Indemnity, Jurisdiction, Confidentiality, Payment & Fees, Risk Allocation

Return ONLY valid JSON:

{{
  "Termination": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Liability": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Indemnity": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Jurisdiction": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Confidentiality": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Payment & Fees": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Risk Allocation": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }}
}}

Text:
\"\"\"{chunk}\"\"\"
"""
    return call_openai(prompt)

# ---------------- MAIN ---------------- #

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
            chunks = chunk_text(text)
            final = {}

            for c in chunks:
                data = analyze_chunk(c)
                for k, v in data.items():
                    if not v["present"]:
                        continue
                    if k not in final or RISK_ORDER[v["risk"]] > RISK_ORDER[final[k]["risk"]]:
                        final[k] = v

        if not final:
            final["General Contract Risk"] = {
                "risk": "Medium",
                "reason": "Complex legal contract detected; manual review recommended"
            }

        st.success("Analysis Complete")

        for clause, info in final.items():
            st.subheader(clause)
            st.write("🔴 Risk Level:", info["risk"])
            st.write("📝 Reason:", info["reason"])
