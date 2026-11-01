import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ClientRecord, DashboardStats, MessageItem, InboxSettingsResponse } from '../models/onboarding.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private readonly isDev = typeof window !== 'undefined' && window.location.hostname === 'localhost' && window.location.port === '4200';
  private readonly baseUrl = this.isDev ? 'http://localhost:5000/api' : '/api';
  readonly uploadBaseUrl = this.isDev ? 'http://localhost:5000/uploads' : '/uploads';

  constructor(private http: HttpClient) {}

  getClients(): Observable<ClientRecord[]> {
    return this.http.get<ClientRecord[]>(`${this.baseUrl}/clients`);
  }

  getClientById(id: string): Observable<ClientRecord> {
    return this.http.get<ClientRecord>(`${this.baseUrl}/clients/${id}`);
  }

  getStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>(`${this.baseUrl}/stats`);
  }

  ingestEmails(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/ingest`, {});
  }

  resetData(): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/reset`, {});
  }

  updateClientStatus(clientId: string, status: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/clients/${clientId}/status`, { status });
  }

  updateChecklistItem(checklistId: string, received: number, reason: string = ''): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/checklist/${checklistId}`, { received, reason });
  }

  approveMessage(messageId: string, approver: string = 'Staff CA'): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/messages/${messageId}/approve`, { approver });
  }

  sendMessage(messageId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/messages/${messageId}/send`, {});
  }

  rejectMessage(messageId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/messages/${messageId}/reject`, {});
  }

  editMessage(messageId: string, subject: string, body: string): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/messages/${messageId}`, { subject, body });
  }

  // Live Production Email Inbox APIs
  getInboxSettings(): Observable<InboxSettingsResponse> {
    return this.http.get<InboxSettingsResponse>(`${this.baseUrl}/inbox/settings`);
  }

  saveInboxSettings(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/inbox/settings`, data);
  }

  testInboxConnection(data: any): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/inbox/test`, data);
  }

  syncLiveInbox(limit: number = 10, markSeen: boolean = false): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/inbox/sync`, { limit, mark_seen: markSeen });
  }
}
