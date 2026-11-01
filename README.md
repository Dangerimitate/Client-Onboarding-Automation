# CA Onboard – Enterprise Client Onboarding & Compliance Automation

An enterprise-grade client onboarding automation platform for Chartered Accountant (CA) firms built with an **Angular Frontend** and a **Flask MVC (Model-View-Controller) Backend**.

The system automates the complete onboarding lifecycle: ingesting incoming client emails, extracting data from identity and financial documents (PAN, Aadhaar, GSTIN, Bank Statements), generating service-specific document checklists, auto-drafting follow-up communications, and enforcing **strict human-in-the-loop staff approval safeguards** before any client message is dispatched.

---

## ⚡ Quick Start

### 1. Backend (Flask MVC)
```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r ../requirements.txt

# Start the Flask MVC Backend server (Port 5000)
python run.py
```

### 2. Frontend (Angular 17+)
```bash
# Option A: View the compiled Angular SPA directly served by Flask
# Open your browser at:
# → http://localhost:5000

# Option B: Run the Angular Live Development Server (Port 4200)
cd frontend
npm install
npm start
# Open your browser at:
# → http://localhost:4200
```

Click **"Ingest Sample Emails"** on the top header to parse test emails, run automated document OCR, detect duplicates, and generate checklists.

---

## 🏗️ Industrial MVC System Architecture

```
                          ┌───────────────────────────┐
                          │   Angular 17+ Frontend    │
                          │  (Standalone Components,  │
                          │   Services & State)       │
                          └─────────────┬─────────────┘
                                        │ REST API (JSON)
                                        ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│                         FLASK MVC BACKEND LAYER                                │
│                                                                                │
│  [CONTROLLER LAYER]                                                            │
│   ├── ClientController       (Client state, filtering, status transitions)     │
│   ├── MessageController      (Approval workflow: approve, reject, send)        │
│   ├── IngestionController    (Email batch parser, reset, document serving)     │
│   └── StatsController        (Aggregated dashboard metrics)                    │
│                                       │                                        │
│  [SERVICE LAYER (Business Logic)]     │                                        │
│   ├── OCRService             (Document type detection, confidence, validation) │
│   ├── ChecklistService       (Service requirements: ITR, GST, Audit)           │
│   ├── NotificationService    (Auto-drafting Email/WhatsApp follow-ups)         │
│   └── IngestionService       (Email intake pipeline, duplicate deduplication)  │
│                                       │                                        │
│  [MODEL LAYER (Data & Schema)]        │                                        │
│   ├── ClientModel            (Client entity CRUD & duplicate search)           │
│   ├── DocumentModel          (Extracted metadata & OCR quality flags)          │
│   ├── ChecklistModel         (Per-service verification items)                  │
│   ├── MessageModel           (Communication drafts & approval state)           │
│   └── ActivityModel          (Immutable audit log trail)                       │
└───────────────────────────────────────┬────────────────────────────────────────┘
                                        ▼
                          ┌───────────────────────────┐
                          │    SQLite Database (WAL)  │
                          │      (onboarding.db)      │
                          └───────────────────────────┘
```

---

## 📁 Project Structure

```
d:\solution\
├── backend/                              # Industrial Flask MVC Backend
│   ├── run.py                            # Server entrypoint
│   └── app/
│       ├── __init__.py                   # Application Factory (create_app + SPA serving)
│       ├── config.py                     # Environment configurations (Dev, Prod)
│       ├── extensions.py                 # SQLite WAL connection manager & CORS
│       ├── controllers/                  # CONTROLLERS (HTTP endpoints & serialization)
│       │   ├── client_controller.py
│       │   ├── message_controller.py
│       │   ├── ingestion_controller.py
│       │   └── stats_controller.py
│       ├── services/                     # SERVICES (Pure business & domain logic)
│       │   ├── ocr_service.py            # OCR parsing, regex extraction & confidence checks
│       │   ├── checklist_service.py      # Service checklist rules (ITR, GST, Audit)
│       │   ├── notification_service.py   # Follow-up drafting & reminder scheduler
│       │   └── ingestion_service.py      # Email parsing & deduplication orchestrator
│       ├── models/                       # MODELS (Entity definitions & repository queries)
│       │   ├── client_model.py
│       │   ├── document_model.py
│       │   ├── checklist_model.py
│       │   ├── message_model.py
│       │   └── activity_model.py
│       └── utils/
│           ├── __init__.py               # UID and timestamp utilities
│           └── validators.py             # Regex validators for PAN, Aadhaar, GSTIN, Phone
│
├── frontend/                             # Enterprise Angular 17+ Frontend
│   ├── angular.json                      # Angular workspace configuration
│   ├── package.json                      # NPM dependencies & scripts
│   ├── src/
│   │   ├── index.html                    # Root HTML with Google Fonts & FontAwesome
│   │   ├── styles.css                    # Design system tokens, variables & dark theme
│   │   └── app/
│   │       ├── app.config.ts             # App config with provideHttpClient(withFetch())
│   │       ├── app.component.ts          # Core component logic & state handling
│   │       ├── app.component.html        # Modern tabbed dashboard template
│   │       ├── app.component.css         # Glassmorphism & responsive stylesheet
│   │       ├── models/
│   │       │   └── onboarding.model.ts   # Strict TypeScript interfaces
│   │       └── services/
│   │           └── api.service.ts        # Typed HTTP client service
│
├── Adams_sample_pack/                    # Test dataset
│   ├── sample_emails.txt                 # 5 incoming sample emails
│   ├── sample_pan_rohan.png              # Standard valid PAN Card
│   ├── sample_aadhaar_rohan.png          # Standard valid Aadhaar Card
│   ├── sample_gst_sunita.png             # Valid GST Registration Certificate
│   ├── sample_pan_amit_invalid.png       # Edge case: Invalid PAN format (4 digits, expected 4 digits + letter)
│   ├── sample_pan_rohan_blurry.png       # Edge case: Blurry scan (confidence < 60%)
│   ├── sample_wrong_document_electricity_bill.png # Edge case: Rejected document type
│   └── sample_bank_statement_sunita.pdf  # Bank statement PDF
│
├── uploads/                              # Processed client attachments
├── onboarding.db                         # SQLite persistent database
└── requirements.txt                      # Python dependencies
```

---

## 🛡️ Key Features & Edge Case Handling

| Requirement | Implementation Detail |
|---|---|
| **1. Email Intake** | Ingests from sample files or connects directly to live IMAP server. Automatically filters for GST, ITR, and Audit. |
| **2. Duplicate Detection** | Matches incoming sender email or PAN against existing records. Merges attachments without creating duplicate clients (e.g., Email #4). |
| **3. Document Extraction & OCR** | Extracts PAN, Aadhaar, GSTIN, Bank account, Form 16, and Investment Proofs with PyPDF2 and OCR validation. Flags low-confidence scans (<60%) rather than guessing. |
| **4. Checklists by Service** | Dynamic checklists: 5 items for ITR, 5 for GST, 6 for Audit. Allows CA staff to manually mark items as Correct or Wrong to override OCR. |
| **5. Follow-Up Auto-Drafting** | Drafts customized follow-ups for Email and WhatsApp, plus a scheduled 3-day reminder for missing documents. |
| **6. Human-in-the-Loop Approval** | **Strict Safeguard**: Message dispatch API returns HTTP 400 if not approved. Staff must review, edit if desired, and click "Approve" before sending. |
| **7. Anomaly & Mismatch Detection** | Flags PAN mismatch between email body and document text, invalid PAN formats, and non-onboarding documents (e.g., electricity bills). |
| **8. Audit & Activity Trail** | Immutable log tracking all system events, OCR decisions, status updates, and staff manual overrides. |
| **9. Strict Status Flow** | Follows a clean stage-by-stage progression (`New` → `Docs Pending` → `Ready for Review` → `Onboarded`), unlocking the "Complete Onboarding" button only once all documents are verified. |

---

## 🎬 Verification & Demo Walkthrough

The Angular frontend and Flask MVC backend were tested with an autonomous browser subagent walkthrough:
- Recording Artifact: `angular_mvc_demo_1793439635610.webp`
- Test flows executed:
  1. Full email intake & OCR extraction
  2. Client card expansion with checklist review
  3. Approval Center workflow (review, approve draft, dispatch)
  4. Document OCR intelligence & anomaly verification
  5. System audit activity log inspection
