import { Injectable, TemplateRef } from '@angular/core';

export interface ModalOptions {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  title?: string;
  closeOnBackdrop?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class ModalService {
  private _template: TemplateRef<any> | null = null;
  private _context: any = null;
  private _options: ModalOptions = { size: 'md', closeOnBackdrop: true };
  private _isOpen: boolean = false;

  get currentTemplate(): TemplateRef<any> | null {
    return this._template;
  }

  get context(): any {
    return this._context;
  }

  get options(): ModalOptions {
    return this._options;
  }

  get isOpen(): boolean {
    return this._isOpen;
  }

  /**
   * Opens a modal using an ng-template reference.
   * Modals are rendered in a centered viewport overlay.
   */
  open(template: TemplateRef<any>, context?: any, options?: ModalOptions): void {
    this._template = template;
    this._context = context || {};
    this._options = { size: 'md', closeOnBackdrop: true, ...options };
    this._isOpen = true;
    if (typeof document !== 'undefined') {
      document.body.style.overflow = 'hidden';
    }
  }

  /**
   * Closes the currently active modal.
   */
  close(): void {
    this._isOpen = false;
    this._template = null;
    this._context = null;
    if (typeof document !== 'undefined') {
      document.body.style.overflow = '';
    }
  }
}

