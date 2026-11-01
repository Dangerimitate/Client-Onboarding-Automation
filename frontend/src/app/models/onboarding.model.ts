export interface DocumentExtractedFields {
  name?: string;
  father_name?: string;
  dob?: string;
  pan?: string;
  aadhaar?: string;
  legal_name?: string;
  gstin?: string;
  state?: string;
  account_holder?: string;
  account_no?: string;
  ifsc?: string;
  period?: string;
  [key: string]: any;
}

export interface DocumentFlag {
  field?: string;
  issue?: string;
  type?: string;
  message?: string;
}

export interface ClientDocument {
  id: string;
  client_id: string;
  doc_type: string;
  filename: string;
  filepath: string;
  extracted: DocumentExtractedFields;
  confidence: number;
  flags: DocumentFlag[];
  uploaded_at: string;
}

export interface ChecklistItem {
  id: string;
  client_id: string;
  doc_type: string;
  required: number;
  received: number;
  doc_id?: string | null;
}

export interface MessageItem {
  id: string;
  client_id: string;
  channel: 'email' | 'whatsapp';
  subject: string;
  body: string;
  status: 'draft' | 'approved' | 'sent' | 'rejected' | 'scheduled';
  scheduled_at?: string | null;
  approved_by?: string | null;
  approved_at?: string | null;
  sent_at?: string | null;
  created_at: string;
}

export interface ActivityLogItem {
  id: string;
  client_id: string;
  action: string;
  detail: string;
  created_at: string;
}

export interface ClientRecord {
  id: string;
  name: string;
  email: string;
  phone: string;
  pan: string;
  aadhaar: string;
  gstin: string;
  service: 'ITR' | 'GST' | 'Audit' | string;
  status: 'new' | 'docs_pending' | 'ready_for_review' | 'onboarded' | 'needs_review' | string;
  flags: DocumentFlag[];
  created_at: string;
  updated_at: string;
  documents?: ClientDocument[];
  checklist?: ChecklistItem[];
  messages?: MessageItem[];
  activity?: ActivityLogItem[];
}

export interface DashboardStats {
  total_clients: number;
  by_status: {
    new?: number;
    docs_pending?: number;
    ready_for_review?: number;
    onboarded?: number;
    needs_review?: number;
    [key: string]: number | undefined;
  };
  total_documents: number;
  flagged_documents: number;
  pending_messages: number;
}

export interface InboxSettings {
  configured: boolean;
  provider: 'gmail' | 'outlook' | 'zoho' | 'custom' | string;
  host: string;
  port: number;
  username: string;
  password?: string;
  password_set: boolean;
  use_ssl: boolean;
  folder: string;
  last_synced?: string | null;
}

export interface InboxPreset {
  name: string;
  host: string;
  port: number;
  use_ssl: boolean;
  folder: string;
  note: string;
}

export interface InboxSettingsResponse {
  settings: InboxSettings;
  presets: Record<string, InboxPreset>;
}
