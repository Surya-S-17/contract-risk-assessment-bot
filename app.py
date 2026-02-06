import streamlit as st
import pdfplumber
from docx import Document
import nltk
from sentence_transformers import SentenceTransformer, util

nltk.download("punkt")

model = SentenceTransformer("all-MiniLM-L6-v2")

CLAUSES = {
    "Termination": ["termination", "terminate", "notice period", "breach"],
    "Liability": ["liability", "damages", "loss", "indemnify"],
    "Jurisdiction": ["jurisdiction", "governing law", "court"],
    "Confidentiality": ["confidential", "non-disclosure"]
}

def extract_text(file):
    if file.name.endswith(".pdf"):
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + " "
        return text.lower()

    elif file.name.endswith(".docx"):
        doc = Document(file)
        return " ".join(p.text for p in doc.paragraphs).lower()

    elif file.name.endswith(".txt"):
        return file.read().decode("utf-8").lower()

    return ""

def analyze_contract(text):
    sentences = nltk.sent_tokenize(text)
    sent_emb = model.encode(sentences, convert_to_tensor=True)

    results = []

    for clause, keywords in CLAUSES.items():
        key_emb = model.encode(keywords, convert_to_tensor=True)
        matches = []

        for i, s in enumerate(sent_emb):
            score = util.cos_sim(s, key_emb).max()
            if score > 0.6:
                matches.append(sentences[i])

        if matches:
            risk = "Medium"
            reason = "Clause present with standard terms"

            joined = " ".join(matches)
            if clause == "Liability" and "unlimited" in joined:
                risk = "High"
                reason = "Unlimited liability detected"
            if clause == "Termination" and "without notice" in joined:
                risk = "High"
                reason = "Termination without notice"
            if clause == "Jurisdiction" and "india" not in joined:
                risk = "Medium"
                reason = "Foreign jurisdiction detected"

            results.append({
                "Clause": clause,
                "Risk Level": risk,
                "Reason": reason
            })

    return results

# ---------------- UI ---------------- #

st.set_page_config(page_title="Contract Risk Assessment Bot", layout="centered")

st.title("📄 Contract Risk Assessment Bot")
st.write("Upload a contract to detect risky clauses using NLP.")

file = st.file_uploader("Upload Contract", type=["pdf", "docx", "txt"])

if file:
    with st.spinner("Analyzing contract..."):
        text = extract_text(file)
        output = analyze_contract(text)

    if output:
        st.success("Analysis Complete")
        for item in output:
            st.subheader(item["Clause"])
            st.write("🔴 Risk Level:", item["Risk Level"])
            st.write("📝 Reason:", item["Reason"])
    else:
        st.info("No major risk clauses detected.")
