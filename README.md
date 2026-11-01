# 🏢 CA Onboard – Enterprise Client Onboarding & Compliance Automation OS

An enterprise-grade client onboarding automation platform designed for Chartered Accountant (CA) firms, built with an **Angular 17+ Frontend** and a **Python Flask MVC (Model-View-Controller) Backend**.

The system automates the end-to-end client intake lifecycle: ingesting client emails (sample pack or live IMAP sync), extracting identity and tax data from documents (PAN, Aadhaar, GSTIN, Bank Statements, Form 16, Investment Proofs), enforcing dynamic service-specific checklists, auto-drafting follow-up communications, and providing **strict human-in-the-loop approval safeguards** before any client message is dispatched.

---

## 📑 Table of Contents
1. [⚡ Setup & Installation](#-setup--installation)
2. [🎯 Handling Failure Cases & Edge Cases (Rubric Requirements)](#-handling-failure-cases--edge-cases)
   - [Case 1: Blurry Scan / Low OCR Confidence](#1-blurry-scan--low-ocr-confidence-scan_rohan_blurrypng)
   - [Case 2: Duplicate Client Detection & Attachment Merge](#2-duplicate-client-detection--attachment-merge-email-4)
   - [Case 3: Wrong / Irrelevant Document Submission](#3-wrong--irrelevant-document-submission-electricity-bill)
   - [Case 4: Invalid Document Format & Data Mismatch](#4-invalid-document-format--data-mismatch)
   - [Case 5: Staff Manual Override (OCR Judgement Correction)](#5-staff-manual-override-ocr-judgement-correction)
3. [🏗️ Design Choices & Architecture](#️-design-choices--architecture)
4. [⚠️ System Limitations & Future Roadmap](#️-system-limitations--future-roadmap)
5. [🎬 2-3 Minute Video Recording Storyboard & Script](#-2-3-minute-video-recording-storyboard--script)

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

## 🎬 2-3 Minute Video Recording Storyboard & Script

Use this exact walkthrough for your video submission:

### Part 1: Introduction & Architecture (0:00 - 0:35)
- **What to show:** Open dashboard at `http://localhost:4200` (or your EC2 URL).
- **What to say:**
  > *"Welcome to CA Onboard, an automated client onboarding platform for Chartered Accountant firms. The system is built with an Angular 17 frontend and a Python Flask MVC backend. It automates email intake, document OCR, checklist verification, and follow-up communication, all while maintaining strict human-in-the-loop approval safeguards."*

### Part 2: Ingestion & Handling Failure Cases (0:35 - 1:40)
- **What to show:**
  1. Click **"Ingest Sample Emails"** (or Live Email Sync).
  2. Point out the dashboard metrics updating in real time.
  3. Click on **Rohan Mehta** (or edge-case client):
     - Highlight **Blurry Scan Handling**: Show the blurry PAN flag with low confidence score (<60%) and explain how it prevents auto-approval.
     - Highlight **Wrong Document Handling**: Show the electricity bill rejected with *"Not an accepted onboarding document"*.
     - Highlight **Duplicate Merging**: Point out how follow-up emails merge attachments without creating duplicate client cards.
     - Highlight **Staff Manual Override**: Demonstrate clicking **"Mark Correct"** on a checklist item to show staff control over OCR mistakes.
- **What to say:**
  > *"Notice how the system handles failure cases: When a blurry scan or an invalid document like an electricity bill is uploaded, the system flags the issue, lowers the confidence score, and halts progression rather than blindly proceeding. For duplicate submissions, it merges attachments cleanly into the existing client. Furthermore, CA staff can manually override any OCR judgement using the 'Mark Correct' or 'Mark Wrong' controls."*

### Part 3: Approval Center & Human-in-the-Loop (1:40 - 2:15)
- **What to show:**
  1. Switch to the **Approval Center** tab.
  2. Show the auto-drafted follow-up emails requesting the missing/blurry documents.
  3. Click **"Approve & Send"**. Show the status transition from `Draft` to `Approved / Sent`.
- **What to say:**
  > *"A critical requirement is human-in-the-loop approval. Outgoing client messages are generated as drafts and cannot be sent automatically. Staff can inspect the message, review the missing document list, and approve the dispatch with one click."*

### Part 4: Final Onboarding & Audit Log (2:15 - 2:45)
- **What to show:**
  1. Return to the Clients tab.
  2. For a fully verified client (e.g. Rahul Epili), show the **"Complete Onboarding"** button appearing conditionally.
  3. Click **"Complete Onboarding"** → Status turns green: `Onboarded`.
  4. Scroll down to the **Audit Activity Trail** to show the immutable log of every action.
- **What to say:**
  > *"Once all required documents are validated, the 'Complete Onboarding' button unlocks. Clicking it finalizes the client. Every single event—from email intake and OCR parsing to staff overrides and message approvals—is permanently recorded in the immutable audit trail."*

---

## 📄 License
MIT License. Built for Chartered Accountant & Corporate Advisory Firms.
