# 🏢 CA Onboard – Enterprise Client Onboarding & Compliance Automation OS

An enterprise-grade client onboarding automation platform designed for Chartered Accountant (CA) firms, built with an **Angular 17+ Frontend** and a **Python Flask MVC (Model-View-Controller) Backend**.

The system automates the end-to-end client intake lifecycle: ingesting client emails (sample pack or live IMAP sync), extracting identity and tax data from documents (PAN, Aadhaar, GSTIN, Bank Statements, Form 16, Investment Proofs), enforcing dynamic service-specific checklists, auto-drafting follow-up communications, and providing **strict human-in-the-loop approval safeguards** before any client message is dispatched.

---

## 📑 Table of Contents
1. [🎥 2-3 Minute Working Video Demonstration](#-2-3-minute-working-video-demonstration)
2. [⚡ Setup & Installation](#-setup--installation)
3. [🎯 Handling Failure Cases & Edge Cases (Rubric Requirements)](#-handling-failure-cases--edge-cases)
   - [Case 1: Blurry Scan / Low OCR Confidence](#1-blurry-scan--low-ocr-confidence-scan_rohan_blurrypng)
   - [Case 2: Duplicate Client Detection & Attachment Merge](#2-duplicate-client-detection--attachment-merge-email-4)
   - [Case 3: Wrong / Irrelevant Document Submission](#3-wrong--irrelevant-document-submission-electricity-bill)
   - [Case 4: Invalid Document Format & Data Mismatch](#4-invalid-document-format--data-mismatch)
   - [Case 5: Staff Manual Override (OCR Judgement Correction)](#5-staff-manual-override-ocr-judgement-correction)
4. [🏗️ Design Choices & Architecture](#️-design-choices--architecture)
5. [⚠️ System Limitations & Future Roadmap](#️-system-limitations--future-roadmap)
6. [🎬 Video Recording Storyboard & Script](#-video-recording-storyboard--script)

---

## 🎥 2-3 Minute Working Video Demonstration

> 📺 **Video Walkthrough:** Demonstrating the end-to-end client onboarding lifecycle, live email sync, document OCR extraction, and comprehensive handling of all failure cases (blurry scans, duplicate client merge, wrong document rejection, and CA staff manual overrides).

[![Watch the CA Onboard Demo Video](https://img.shields.io/badge/▶%EF%B8%8F_Watch_Demo_Video-2--3_Min_Walkthrough-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](YOUR_VIDEO_URL_HERE)

- 🔗 **Direct Video Link:** [Click here to watch the full demo](YOUR_VIDEO_URL_HERE)
- 📌 **Video Flow Covered:**
  1. **Live Email Ingestion & Dashboard:** Real-time metrics and dynamic intake.
  2. **Failure Case 1 (Blurry Scan):** Low-confidence OCR detection (<60%) triggering automated client re-upload requests.
  3. **Failure Case 2 (Duplicate Client):** Merging follow-up attachments into an existing profile without duplicate records.
  4. **Failure Case 3 (Wrong Document):** Electricity bill rejection with statutory compliance flags.
  5. **Failure Case 4 (Staff Override):** "Mark Correct" / "Mark Wrong" actions overriding OCR misjudgements.
  6. **Human-in-the-Loop Safeguard:** Reviewing and approving auto-drafted communications before dispatch.
  7. **Single-Action Flow & Audit Trail:** Transitioning client to `Onboarded` and inspecting the immutable event log.

---

## ⚡ Setup & Installation

### Prerequisites
- **Python 3.10+**
- **Node.js 18+ or 20+** and **npm**
- **Tesseract OCR Engine**:
  - *Ubuntu / Debian:* `sudo apt install -y tesseract-ocr`
  - *macOS:* `brew install tesseract`
  - *Windows:* Download installer from UB-Mannheim Tesseract OCR GitHub and add to PATH.

---

### Local Development Setup

#### 1. Backend (Flask MVC)
```bash
# Clone the repository
git clone https://github.com/Dangerimitate/Client-Onboarding-Automation.git
cd Client-Onboarding-Automation

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Run backend development server (starts on http://127.0.0.1:5000)
python backend/run.py
```

#### 2. Frontend (Angular 17+)
```bash
# In a new terminal window
cd frontend

# Install Node dependencies
npm install

# Start Angular development server (starts on http://localhost:4200)
npm start
```
Open **`http://localhost:4200`** in your browser.

---

## 🎯 Handling Failure Cases & Edge Cases

The system was architected with a **defense-in-depth validation strategy** to protect CA staff from incorrect filings, fraudulent submissions, and unreadable scans:

### 1. Blurry Scan / Low OCR Confidence (`sample_pan_rohan_blurry.png`)
- **Detection:** `OCRService.process_document()` evaluates image DPI, text sharpness, and character recognition certainty.
- **System Action:**
  - If overall OCR confidence is **< 60%**, the system marks the document as flagged (`low_confidence`).
  - Sets the client status to `needs_review`.
  - **Does NOT** automatically mark the checklist item as fulfilled.
  - Automatically drafts a polite, client-facing follow-up: *"Your PAN card scan was blurry or unreadable. Please reply with a clear, flat photo or PDF."*

### 2. Duplicate Client Detection & Attachment Merge (Email #4)
- **Detection:** `ClientModel.find_duplicate()` checks incoming emails and extracted PAN numbers against existing client records.
- **System Action:**
  - When an existing client sends follow-up documents, the system **prevents duplicate client records**.
  - Merges new attachments directly into the existing client's document repository.
  - Logs a `duplicate_merged` event in the audit trail.
  - Skips already-ingested files to prevent duplicate OCR overhead.
  - **Status Preservation:** If the client was already marked `onboarded`, the system **safeguards their status** and does not demote them back.

### 3. Wrong / Irrelevant Document Submission (`electricity_bill.png`)
- **Detection:** Keyword classification in `OCRService.detect_doc_type()` and content filtering.
- **System Action:**
  - Categorizes the document as `"Electricity Bill"` / `"Unknown"`.
  - Attaches a critical flag: *"Not an accepted onboarding document for ITR/GST/Audit service"*.
  - Refuses to fulfill any required checklist item with this file.
  - Logs an anomaly warning in the Activity Audit Trail.

### 4. Invalid Document Format & Data Mismatch
- **PAN Format Validation:** `validate_pan()` verifies statutory regex `^[A-Z]{5}[0-9]{4}[A-Z]$`. If a client submits a malformed PAN (e.g., 4 digits instead of 4 digits + letter as in `sample_pan_amit_invalid.png`), a critical formatting error is raised.
- **Cross-Field Reconciliation:** The system reconciles the PAN extracted from the document against the PAN declared in the email body. A mismatch flag is triggered if they do not match.

### 5. Staff Manual Override (OCR Judgement Correction)
- **The Problem:** Even state-of-the-art OCR can misread low-contrast stamps or unusual layouts.
- **The Solution:** CA staff can click **"Mark Correct"** or **"Mark Wrong"** on any checklist item in the UI.
  - Manually approving an item satisfies the checklist requirement.
  - The action is recorded with a timestamp and user in the immutable audit log (`activity_log`).
  - Once all checklist items are verified and no blocking flags remain, the **"Complete Onboarding"** action unlocks.

---

## 🏗️ Design Choices & Architecture

| Design Choice | Rationale | Alternatives Considered |
|---|---|---|
| **Flask MVC Architecture** | Modular separation of concerns into Controllers (HTTP/REST), Services (Domain & OCR logic), and Models (SQLite repositories). Clean, testable, and maintainable. | Fast-API (good, but Flask provides simpler unified static SPA serving and minimal overhead for this scope). |
| **Angular 17+ Standalone Components** | Modern Angular architecture with zero NgModules, fast Vite/ESBuild bundling, type-safe models, and reactive RxJS state management. | React (Angular provides stronger out-of-the-box opinionated structure and enterprise form controls). |
| **Local OCR (PyMuPDF + Tesseract) vs Cloud APIs** | Complete **client data privacy** and confidentiality for financial documents. Zero cloud API cost, runs fully offline or in private VPC without uploading sensitive PAN/Aadhaar cards to 3rd-party services. | AWS Textract / Google Document AI (higher recurring cost and data residency compliance questions for CA firms). |
| **Strict Human-in-the-Loop Safeguards** | The outgoing messaging controller strictly forbids automatic dispatch. All outgoing emails/WhatsApp messages are generated as drafts and require explicit CA staff approval before HTTP dispatch. | Autonomous auto-sending (high liability risk if OCR misinterprets an amount or tax notice). |
| **SQLite with WAL Mode** | Zero-configuration, serverless, atomic file database with Write-Ahead Logging (WAL) for high concurrency and easy backup on single-node deployments. | PostgreSQL / MySQL (unnecessary operational complexity for single-node CA firm deployments; easy to migrate later via repository pattern). |
| **Conditional Flow Action Buttons** | Reduces cognitive overload for CA staff. Buttons dynamically display only the next valid action based on stage: `New` → `Docs Pending` → `Ready for Review` → `Onboarded`. | Showing all buttons simultaneously (leads to accidental out-of-order state transitions). |

---

## ⚠️ System Limitations & Future Roadmap

1. **Multi-Page Financial Statement Table Extraction:**
   - *Current State:* Basic text parsing and statement presence detection.
   - *Limitation:* Complex tabular parsing across multi-page bank statements with varying bank layouts requires dedicated layout models.
   - *Roadmap:* Integrate tabular extraction pipelines (e.g. `pdfplumber` / table transformer models).
2. **Database Write Concurrency at Massive Scale:**
   - *Current State:* SQLite WAL mode supports dozens of simultaneous reads with sequential writes.
   - *Limitation:* Not suitable for distributed multi-region horizontal scaling.
   - *Roadmap:* Abstract database connections via SQLAlchemy to support PostgreSQL when scaling across multiple offices.
3. **IMAP Polling vs Real-Time Webhooks:**
   - *Current State:* Live IMAP synchronization via user-triggered button or scheduled cron interval.
   - *Limitation:* Polling creates minor sync intervals compared to push webhooks.
   - *Roadmap:* Add Gmail API / Microsoft Graph Webhook listeners for sub-second event-driven triggers.

---
