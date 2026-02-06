import streamlit as st
import pdfplumber
from docx import Document
import google.generativeai as genai
import json
import re

# ---------------- CONFIG ---------------- #

st.set_page_config(page_title="LLM Contract Risk Analyzer", layout="centered")
st.title("📄 LLM-Powered Contract Risk Analyzer")

# Load Gemini API key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-pro")

# ---------------- HELPERS ---------------- #

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

def chunk_text(text, max_chars=3500):
    paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 200]
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

def analyze_chunk(chunk):
    prompt = f"""
You are a legal risk analyst.

Analyze the contract section below and assess legal risks.

Clauses to analyze:
- Termination
- Liability
- Indemnity
- Jurisdiction
- Confidentiality
- Payment & Fees
- Risk Allocation

Risk rules:
HIGH:
- Unlimited or broad liability
- Sole responsibility
- Broad indemnity
- Unilateral termination

MEDIUM:
- Liability exists but procedural or shared
- Termination with notice
- Payment obligations with conditions

LOW:
- Explicit limitations
- Balanced obligations
- Clear jurisdiction

Return ONLY valid JSON in this exact format:

{{
  "Termination": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Liability": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Indemnity": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Jurisdiction": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Confidentiality": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Payment & Fees": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }},
  "Risk Allocation": {{ "present": true/false, "risk": "Low/Medium/High", "reason": "..." }}
}}

Contract Section:
\"\"\"{chunk}\"\"\"
"""

    response = model.generate_content(prompt)
    clean = re.sub(r"```json|```", "", response.text).strip()
    return json.loads(clean)

def merge_results(all_results):
    final = {}

    for res in all_results:
        for clause, data in res.items():
            if not data["present"]:
                continue

            if clause not in final:
                final[clause] = data
            else:
                # escalate risk if needed
                levels = ["Low", "Medium", "High"]
                if levels.index(data["risk"]) > levels.index(final[clause]["risk"]):
                    final[clause] = data

    return final

# ---------------- UI ---------------- #

uploaded_file = st.file_uploader("Upload Contract (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])

if uploaded_file:
    with st.spinner("Analyzing contract with Gemini Pro..."):
        text = extract_text(uploaded_file)
        chunks = chunk_text(text)

        chunk_results = []
        for c in chunks[:5]:  # limit for safety
            chunk_results.append(analyze_chunk(c))

        final_results = merge_results(chunk_results)

    st.success("Analysis Complete")

    if final_results:
        for clause, info in final_results.items():
            st.subheader(clause)
            st.write("🔴 Risk Level:", info["risk"])
            st.write("📝 Reason:", info["reason"])
    else:
        st.info("No significant risks detected.")
