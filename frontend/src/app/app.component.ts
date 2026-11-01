import { Component, OnInit, ViewChild, TemplateRef, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { ApiService } from './services/api.service';
import { ModalService } from './services/modal.service';
import { ClientRecord, DashboardStats, MessageItem, ClientDocument, ChecklistItem, InboxSettings, InboxPreset } from './models/onboarding.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit {
  title = 'CA Onboard';
  activeTab: 'pipeline' | 'approvals' | 'documents' | 'audit' = 'pipeline';

  clients: ClientRecord[] = [];
  stats: DashboardStats | null = null;
  loading: boolean = false;
  actionMessage: string = '';

  // Filters
  searchQuery: string = '';
  selectedStatusFilter: string = 'all';
  selectedServiceFilter: string = 'all';

  // Expanded client state
  expandedClientId: string | null = null;

  // Modals & Centered Templates via ModalService
  @ViewChild('docPreviewModal') docPreviewModal!: TemplateRef<any>;
  @ViewChild('editMessageModal') editMessageModal!: TemplateRef<any>;
  @ViewChild('inboxSetupModal') inboxSetupModal!: TemplateRef<any>;

  // Document Inspection Modal State
  previewDoc: ClientDocument | null = null;
  previewDocUrl: string = '';
  previewSafeDocUrl: SafeResourceUrl | null = null;

  // Active edit message modal
  editingMessage: MessageItem | null = null;
  editSubject: string = '';
  editBody: string = '';

  // Production Direct Email Inbox State
  inboxSettings: InboxSettings | null = null;
  inboxPresets: Record<string, InboxPreset> = {};
  
  // Settings Form fields
  formProvider: string = 'gmail';
  formHost: string = 'imap.gmail.com';
  formPort: number = 993;
  formUsername: string = '';
  formPassword: string = '';
  formUseSsl: boolean = true;
  formFolder: string = 'INBOX';
  formSyncLimit: number = 10;
  formSyncMarkSeen: boolean = false;

  // Connection test & sync state
  isTestingInbox: boolean = false;
  isSyncingInbox: boolean = false;
  testResult: { ok?: boolean; message?: string; error?: string } | null = null;

  constructor(
    public api: ApiService,
    public modalService: ModalService,
    private sanitizer: DomSanitizer
  ) {}

  ngOnInit(): void {
    this.refreshAll();
    this.loadInboxSettings();
  }

  refreshAll(): void {
    this.loading = true;
    this.api.getClients().subscribe({
      next: (data) => {
        this.clients = data || [];
        if (this.clients.length === 0) {
          this.expandedClientId = null;
        } else if (!this.expandedClientId || !this.clients.some(c => c.id === this.expandedClientId)) {
          this.expandedClientId = this.clients[0].id;
        }
        this.loading = false;
      },
      error: (err) => {
        console.error('Failed to load clients', err);
        this.loading = false;
      }
    });

    this.api.getStats().subscribe({
      next: (data) => {
        this.stats = data || {
          total_clients: 0,
          by_status: {},
          total_documents: 0,
          flagged_documents: 0,
          pending_messages: 0
        };
      },
      error: (err) => console.error('Failed to load stats', err)
    });
  }

  loadInboxSettings(): void {
    this.api.getInboxSettings().subscribe({
      next: (res) => {
        this.inboxSettings = res.settings;
        this.inboxPresets = res.presets || {};
        if (this.inboxSettings) {
          this.formProvider = this.inboxSettings.provider || 'gmail';
          this.formHost = this.inboxSettings.host || 'imap.gmail.com';
          this.formPort = this.inboxSettings.port || 993;
          this.formUsername = this.inboxSettings.username || '';
          this.formUseSsl = this.inboxSettings.use_ssl;
          this.formFolder = this.inboxSettings.folder || 'INBOX';
        }
      },
      error: (err) => console.error('Failed to load inbox settings', err)
    });
  }

  openInboxModal(): void {
    this.testResult = null;
    this.loadInboxSettings();
    this.modalService.open(this.inboxSetupModal, {}, { size: 'lg' });
  }

  closeInboxModal(): void {
    this.testResult = null;
    this.modalService.close();
  }

  onProviderChange(providerKey: string): void {
    this.formProvider = providerKey;
    const preset = this.inboxPresets[providerKey];
    if (preset) {
      this.formHost = preset.host;
      this.formPort = preset.port;
      this.formUseSsl = preset.use_ssl;
      this.formFolder = preset.folder;
    }
  }

  testInboxConnection(): void {
    this.isTestingInbox = true;
    this.testResult = null;
    this.api.testInboxConnection({
      host: this.formHost,
      port: this.formPort,
      username: this.formUsername,
      password: this.formPassword,
      use_ssl: this.formUseSsl,
      folder: this.formFolder
    }).subscribe({
      next: (res) => {
        this.testResult = res;
        this.isTestingInbox = false;
      },
      error: (err) => {
        this.testResult = {
          ok: false,
          error: err.error?.error || err.message || 'Connection failed. Check host, port, or app password.'
        };
        this.isTestingInbox = false;
      }
    });
  }

  saveInboxSettings(): void {
    this.loading = true;
    this.api.saveInboxSettings({
      provider: this.formProvider,
      host: this.formHost,
      port: this.formPort,
      username: this.formUsername,
      password: this.formPassword,
      use_ssl: this.formUseSsl,
      folder: this.formFolder
    }).subscribe({
      next: (res) => {
        this.inboxSettings = res.settings;
        this.showToast('Production email inbox configuration saved successfully.');
        this.loading = false;
        this.closeInboxModal();
      },
      error: (err) => {
        this.showToast('Failed to save settings: ' + (err.error?.error || err.message));
        this.loading = false;
      }
    });
  }

  syncLiveInbox(): void {
    if (!this.inboxSettings?.configured) {
      this.openInboxModal();
      this.showToast('Please configure your production email credentials first.');
      return;
    }

    this.isSyncingInbox = true;
    this.showToast(`Connecting to ${this.inboxSettings.host} to check for new client emails...`);
    
    this.api.syncLiveInbox(this.formSyncLimit, this.formSyncMarkSeen).subscribe({
      next: (res) => {
        this.isSyncingInbox = false;
        this.showToast(res.message || `Sync completed. Processed ${res.processed} emails.`);
        this.refreshAll();
        this.loadInboxSettings();
      },
      error: (err) => {
        this.isSyncingInbox = false;
        this.showToast('Live Email Sync Error: ' + (err.error?.error || err.message));
      }
    });
  }

  triggerIngestion(): void {
    this.loading = true;
    this.showToast('Ingesting incoming emails and attachments from sample pack...');
    this.api.ingestEmails().subscribe({
      next: (res) => {
        this.showToast(`Processed ${res.processed} emails with automated OCR and checklist generation!`);
        this.refreshAll();
      },
      error: (err) => {
        this.showToast('Ingestion failed: ' + (err.error?.error || err.message));
        this.loading = false;
      }
    });
  }

  triggerReset(): void {
    this.loading = true;
    this.showToast('Resetting database and attachments...');
    this.api.resetData().subscribe({
      next: () => {
        this.clients = [];
        this.expandedClientId = null;
        this.stats = {
          total_clients: 0,
          by_status: {},
          total_documents: 0,
          flagged_documents: 0,
          pending_messages: 0
        };
        this.showToast('Simulation database cleared. Ready for fresh intake.');
        this.refreshAll();
      },
      error: (err) => {
        this.showToast('Reset failed: ' + (err.error?.error || err.message));
        this.loading = false;
      }
    });
  }

  toggleExpand(clientId: string): void {
    this.expandedClientId = this.expandedClientId === clientId ? null : clientId;
  }

  updateClientStatus(clientId: string, newStatus: string): void {
    this.api.updateClientStatus(clientId, newStatus).subscribe({
      next: () => {
        this.showToast(`Status updated to ${this.formatStatus(newStatus)}`);
        this.refreshAll();
      },
      error: (err) => this.showToast('Status update failed: ' + err.message)
    });
  }

  markChecklistItem(item: ChecklistItem, received: number, client: ClientRecord, event?: Event): void {
    if (event) {
      event.stopPropagation();
    }
    if (client.status === 'onboarded') {
      return; // Cannot modify checklist of an already onboarded client
    }
    const actionLabel = received === 1 ? 'Verified (Correct)' : 'Wrong / Rejected';
    this.loading = true;
    this.api.updateChecklistItem(item.id, received, 'CA staff manual override').subscribe({
      next: (res) => {
        this.loading = false;
        item.received = received;
        this.showToast(`${item.doc_type} marked as ${actionLabel}.`);
        this.refreshAll();
      },
      error: (err) => {
        this.loading = false;
        this.showToast(`Failed to update checklist item: ${err.message}`);
      }
    });
  }

  approveMessage(msg: MessageItem): void {
    this.loading = true;
    this.api.approveMessage(msg.id, 'Senior Staff CA').subscribe({
      next: () => {
        this.loading = false;
        this.showToast(`Message approved for ${msg.channel.toUpperCase()}. Ready to dispatch.`);
        this.refreshAll();
      },
      error: (err) => {
        this.loading = false;
        const errorMsg = err.error?.error || err.error?.message || err.message;
        this.showToast('Approval error: ' + errorMsg);
        this.refreshAll();
      }
    });
  }

  sendMessage(msg: MessageItem): void {
    if (msg.status !== 'approved') {
      alert('Human Approval Safeguard: Message must be approved by staff before sending!');
      return;
    }
    this.loading = true;
    this.api.sendMessage(msg.id).subscribe({
      next: (res: any) => {
        this.loading = false;
        if (res.whatsapp_url) {
          window.open(res.whatsapp_url, '_blank');
        }
        const toastMsg = res.message || `Message dispatched to client via ${msg.channel.toUpperCase()}`;
        this.showToast(toastMsg);
        this.refreshAll();
      },
      error: (err) => {
        this.loading = false;
        const errorMsg = err.error?.error || err.error?.message || err.message;
        this.showToast('Send error: ' + errorMsg);
        alert('Failed to send email:\n\n' + errorMsg);
        this.refreshAll();
      }
    });
  }

  rejectMessage(msg: MessageItem): void {
    this.api.rejectMessage(msg.id).subscribe({
      next: () => {
        this.showToast(`Draft rejected.`);
        this.refreshAll();
      },
      error: (err) => this.showToast('Reject error: ' + err.message)
    });
  }

  getWhatsAppUrl(msg: MessageItem, client?: ClientRecord): string | null {
    if (msg.channel !== 'whatsapp') return null;
    const phone = client?.phone || '';
    let cleanPhone = phone.replace(/\D/g, '');
    if (!cleanPhone) return null;
    if (cleanPhone.length === 10) cleanPhone = '91' + cleanPhone;
    else if (cleanPhone.startsWith('0') && cleanPhone.length === 11) cleanPhone = '91' + cleanPhone.slice(1);
    return `https://wa.me/${cleanPhone}?text=${encodeURIComponent(msg.body)}`;
  }

  // Document Inspection Modal using ModalService
  openDocumentModal(doc: ClientDocument): void {
    this.previewDoc = doc;
    this.previewDocUrl = this.getDocumentUrl(doc);
    this.previewSafeDocUrl = this.sanitizer.bypassSecurityTrustResourceUrl(this.previewDocUrl);
    this.modalService.open(this.docPreviewModal, { doc }, { size: 'xl' });
  }

  isPdf(filename?: string): boolean {
    return !!filename && filename.toLowerCase().endsWith('.pdf');
  }

  startEditMessage(msg: MessageItem): void {
    this.editingMessage = msg;
    this.editSubject = msg.subject;
    this.editBody = msg.body;
    this.modalService.open(this.editMessageModal, msg, { size: 'md' });
  }

  saveEditMessage(): void {
    if (!this.editingMessage) return;
    this.api.editMessage(this.editingMessage.id, this.editSubject, this.editBody).subscribe({
      next: () => {
        this.showToast('Draft content saved successfully.');
        this.editingMessage = null;
        this.modalService.close();
        this.refreshAll();
      },
      error: (err) => this.showToast('Save error: ' + err.message)
    });
  }

  cancelEdit(): void {
    this.editingMessage = null;
    this.modalService.close();
  }

  closeActiveModal(): void {
    this.editingMessage = null;
    this.previewDoc = null;
    this.modalService.close();
  }

  onBackdropClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    if (target.classList.contains('modal-backdrop')) {
      this.closeActiveModal();
    }
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.modalService.isOpen) {
      this.closeActiveModal();
    }
  }

  showToast(msg: string): void {
    this.actionMessage = msg;
    setTimeout(() => {
      if (this.actionMessage === msg) {
        this.actionMessage = '';
      }
    }, 4500);
  }

  // Filtered clients computed list
  get filteredClients(): ClientRecord[] {
    return this.clients.filter(c => {
      const matchesSearch = !this.searchQuery || 
        c.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        c.email.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        c.pan.toLowerCase().includes(this.searchQuery.toLowerCase());
      
      const matchesStatus = this.selectedStatusFilter === 'all' || c.status === this.selectedStatusFilter;
      const matchesService = this.selectedServiceFilter === 'all' || c.service === this.selectedServiceFilter;

      return matchesSearch && matchesStatus && matchesService;
    });
  }

  // All messages flattened across clients for Approval Center
  get allMessages(): { client: ClientRecord; message: MessageItem }[] {
    const list: { client: ClientRecord; message: MessageItem }[] = [];
    for (const c of this.clients) {
      if (c.messages) {
        for (const m of c.messages) {
          list.push({ client: c, message: m });
        }
      }
    }
    return list.sort((a, b) => new Date(b.message.created_at).getTime() - new Date(a.message.created_at).getTime());
  }

  // All documents flattened across clients for Document Extraction Hub
  get allDocuments(): { client: ClientRecord; doc: ClientDocument }[] {
    const list: { client: ClientRecord; doc: ClientDocument }[] = [];
    for (const c of this.clients) {
      if (c.documents) {
        for (const d of c.documents) {
          list.push({ client: c, doc: d });
        }
      }
    }
    return list;
  }

  filterByStatus(status: string): void {
    this.activeTab = 'pipeline';
    if (status === 'all') {
      this.selectedStatusFilter = 'all';
    } else if (this.selectedStatusFilter === status) {
      this.selectedStatusFilter = 'all';
    } else {
      this.selectedStatusFilter = status;
    }
  }

  hasUploadedDoc(client: ClientRecord, docType: string): boolean {
    if (!client || !client.documents || client.documents.length === 0) {
      return false;
    }
    const target = docType.toLowerCase().trim();
    return client.documents.some(d => d.doc_type && d.doc_type.toLowerCase().trim() === target);
  }

  // Helper formatting methods
  formatFieldLabel(key: string): string {
    if (!key) return '';
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  formatStatus(status: string): string {
    switch (status) {
      case 'new': return 'New Intake';
      case 'docs_pending': return 'Docs Pending';
      case 'ready_for_review': return 'Ready for Review';
      case 'onboarded': return 'Onboarded';
      case 'needs_review': return 'Attention Required';
      default: return status;
    }
  }

  getCompletedChecklistCount(client: ClientRecord): number {
    return client.checklist?.filter(i => i.received === 1).length || 0;
  }

  getTotalChecklistCount(client: ClientRecord): number {
    return client.checklist?.length || 0;
  }

  getChecklistProgressPercent(client: ClientRecord): number {
    const total = this.getTotalChecklistCount(client);
    if (!total) return 0;
    return Math.round((this.getCompletedChecklistCount(client) / total) * 100);
  }

  getDocumentUrl(doc: ClientDocument): string {
    return `${this.api.uploadBaseUrl}/${doc.client_id}_${doc.filename}`;
  }
}
