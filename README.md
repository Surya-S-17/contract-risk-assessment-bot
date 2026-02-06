# Contract Risk Assessment Bot

A web-based application that analyzes legal contracts and highlights potentially risky clauses using an explainable, rule-based legal risk engine. The tool helps users quickly understand contract risks without reading the entire document.

Live Demo:
https://contract-risk-assessment-bot-surya.streamlit.app/

GitHub Repository:
https://github.com/Surya-S-17/contract-risk-assessment-bot.git


## Problem Statement

Legal contracts are often long, complex, and difficult for non-legal users to interpret. Identifying risky clauses such as termination, liability, or indemnity requires time and expertise.

This project aims to automatically detect key contract clauses, assess their risk level (Low, Medium, High), and provide clear explanations for each risk.


## Solution Overview

The Contract Risk Assessment Bot analyzes uploaded contracts and produces a clause-wise risk report along with an overall contract risk summary.

The system uses a rule-based legal risk engine inspired by common compliance and contract review practices. This ensures stable deployment, zero dependency on paid APIs, and fully explainable outputs.


## Key Features

- Upload contracts in PDF, DOCX, or TXT format
- Detects key legal clauses:
  - Termination
  - Liability
  - Indemnity
  - Jurisdiction
  - Confidentiality
  - Payment and Fees
- Risk classification as Low, Medium, or High
- Overall contract risk summary
- Clause-wise explanations using expandable sections
- Handles scanned PDFs gracefully with user feedback


## Tech Stack

- Frontend and Backend: Streamlit
- Programming Language: Python
- Document Parsing:
  - pdfplumber for PDF files
  - python-docx for DOCX files
- Risk Engine:
  - Rule-based pattern detection
  - Obligation and responsibility heuristics


## How It Works

1. The user uploads a contract document.
2. Text is extracted from the document.
3. Important legal clauses are detected using rule-based logic.
4. Each detected clause is assigned a risk level.
5. Results are displayed with an overall risk summary and clause-wise details.


## Example Output

Overall Contract Risk: Medium

Liability:
Risk Level: High
Reason: Broad or unlimited liability or indemnity detected

Termination:
Risk Level: Medium
Reason: Termination-related provisions detected


## Limitations

- This tool does not provide legal advice.
- Scanned or image-based PDFs require OCR, which is not included.
- Risk detection is heuristic-based and may not cover all legal edge cases.


## Future Improvements

- OCR support for scanned documents
- Clause confidence scores
- Highlighting risky text within documents
- Optional hybrid integration with LLMs
- Exportable risk reports


## Use Cases

- Quick pre-screening of contracts
- Helping non-legal users identify potential risks
- Educational tool for understanding contract structure
- Hackathon or academic demonstration


## Disclaimer

This application is intended for informational purposes only and does not constitute legal advice. Users should consult a qualified legal professional for formal contract review.


## Author

Surya S
GitHub: https://github.com/Surya-S-17
