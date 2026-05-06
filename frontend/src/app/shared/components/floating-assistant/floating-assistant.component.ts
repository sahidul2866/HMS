import { CommonModule } from '@angular/common';
import { Component, HostListener, Input, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { SessionService } from '../../../core/services/session.service';
import { StaffBotContext, StaffBotResponse, StaffBotService, StaffBotSettings } from '../../../core/services/staff-bot.service';

type AssistantSender = 'bot' | 'user';

@Component({
  selector: 'app-floating-assistant',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './floating-assistant.component.html',
  styleUrls: ['./floating-assistant.component.scss'],
})
export class FloatingAssistantComponent {
  private readonly botService = inject(StaffBotService);
  private readonly router = inject(Router);
  private readonly sessionService = inject(SessionService);

  @Input() title = 'Staff Assistant';
  @Input() context: StaffBotContext | string | null = null;
  @Input() quickActions: string[] = [];
  @Input() placeholder = 'Ask about billing, appointments, lab, pharmacy…';

  open = false;
  fullscreen = false;
  loading = false;
  conversationId: string | null = null;
  input = '';
  messages: Array<{ sender: AssistantSender; text: string; createdAt: number; response?: StaffBotResponse }> = [];
  error = '';
  settings: StaffBotSettings | null = null;
  currentPath = this.router.url.split('?')[0].split('#')[0] || '/dashboard';

  constructor() {
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe((event) => {
      this.currentPath = event.urlAfterRedirects.split('?')[0].split('#')[0] || '/dashboard';
      if (this.open && this.messages.length) {
        this.messages = [
          ...this.messages,
          {
            sender: 'bot' as AssistantSender,
            text: `Context updated: ${this.pageTitle}.`,
            createdAt: Date.now(),
          },
        ].slice(-12);
      }
    });
  }

  toggle(): void {
    this.open = !this.open;
    if (this.open && !this.messages.length) {
      this.bootstrap();
    }
  }

  close(): void {
    this.open = false;
    this.fullscreen = false;
  }

  toggleFullscreen(): void {
    this.fullscreen = !this.fullscreen;
  }

  bootstrap(): void {
    this.loading = true;
    this.error = '';
    this.botService.settings().subscribe({
      next: (settings) => {
        this.settings = settings;
        const greeting = settings?.greeting_message || 'Hi! How can I help you today?';
        this.messages = [{ sender: 'bot', text: greeting, createdAt: Date.now() }];
        this.loading = false;
      },
      error: () => {
        this.messages = [{ sender: 'bot', text: 'Hi! Ask me anything about your daily tasks.', createdAt: Date.now() }];
        this.loading = false;
      },
    });
  }

  send(message?: string): void {
    const text = (message ?? this.input).trim();
    if (!text || this.loading) return;

    if (text.toLowerCase() === 'start over') {
      this.reset();
      return;
    }

    this.messages = [...this.messages, { sender: 'user', text, createdAt: Date.now() }];
    this.input = '';
    this.loading = true;
    this.error = '';

    this.botService.sendMessage({ message: text, conversation_id: this.conversationId, context: this.resolvedContext }).subscribe({
      next: (response) => {
        this.conversationId = response.conversation_id || this.conversationId;
        this.messages = [...this.messages, { sender: 'bot', text: response.message || 'Okay.', createdAt: Date.now(), response }];
        this.loading = false;
      },
      error: (error) => {
        const detail = error?.error?.message || error?.error?.detail;
        const status = error?.status ? `HTTP ${error.status}` : '';
        this.error = [status, detail].filter(Boolean).join(' - ') || 'Assistant is temporarily unavailable.';
        this.messages = [
          ...this.messages,
          { sender: 'bot', text: 'I could not reach the assistant service. Please try again later.', createdAt: Date.now() },
        ];
        this.loading = false;
      },
    });
  }

  reset(): void {
    this.loading = true;
    this.error = '';
    this.botService.reset({ context: this.resolvedContext }).subscribe({
      next: (response) => {
        this.conversationId = response.conversation_id || null;
        this.messages = [{ sender: 'bot', text: response.message || 'Let’s start over. What do you need?', createdAt: Date.now(), response }];
        this.loading = false;
      },
      error: () => {
        this.conversationId = null;
        this.messages = [{ sender: 'bot', text: 'Let’s start over. What do you need?', createdAt: Date.now() }];
        this.loading = false;
      },
    });
  }

  useQuick(text: string): void {
    this.input = text;
    this.send(text);
  }

  get visibleQuickActions(): string[] {
    const pageSpecific = this.pageSpecificSuggestions();
    const dynamic = this.messages[this.messages.length - 1]?.response?.context_suggestions || this.settings?.quick_actions || [];
    return [...new Set([...(this.quickActions || []), ...pageSpecific, ...dynamic])].slice(0, 5);
  }

  get resolvedContext(): StaffBotContext {
    if (this.context && typeof this.context !== 'string') {
      return {
        ...this.context,
        path: this.context.path || this.currentPath,
        module: this.context.module || this.moduleName,
        page: this.context.page || this.pageTitle,
      };
    }
    return {
      module: this.context || this.moduleName,
      page: this.pageTitle,
      path: this.currentPath,
      filters: this.routeFilters(),
    };
  }

  get moduleName(): string {
    const segment = this.currentPath.split('/').filter(Boolean)[0] || 'dashboard';
    if (segment === 'diagnostics') return 'laboratory';
    if (segment === 'accounting') return 'billing';
    return segment;
  }

  get pageTitle(): string {
    return this.currentPath
      .split('/')
      .filter(Boolean)
      .map((part) => part.replace(/-/g, ' '))
      .join(' / ') || 'dashboard';
  }

  get contextLabel(): string {
    return `${this.moduleName.toUpperCase()} · ${this.pageTitle}`;
  }

  copyResponse(text: string): void {
    void navigator.clipboard?.writeText(text);
  }

  private canAny(...permissions: string[]): boolean {
    return this.sessionService.hasAnyPermission(permissions);
  }

  private pageSpecificSuggestions(): string[] {
    const path = this.currentPath;
    const suggestions: Array<[string, string[]]> = path.startsWith('/opd')
      ? [
          ['Summarize today’s OPD visits', ['opd.view']],
          ['List pending orders', ['diagnostics.view', 'opd.view']],
          ['Help draft prescription notes', ['opd.prescribe']],
          ['Compare previous visit', ['patient.view', 'opd.view']],
        ]
      : path.startsWith('/billing')
        ? [
            ['Explain this bill', ['billing.view']],
            ['Show pending payments', ['billing.view']],
            ['Check refund eligibility', ['billing.payment.refund']],
            ['Find billing discrepancies', ['billing.view']],
          ]
        : path.startsWith('/pharmacy')
          ? [
              ['Check medicine stock', ['pharmacy.view']],
              ['Show low-stock medicines', ['pharmacy.view']],
              ['Explain dispense status', ['pharmacy.dispense']],
              ['Review return eligibility', ['pharmacy.return']],
            ]
          : path.startsWith('/laboratory') || path.startsWith('/diagnostics')
            ? [
                ['Show pending lab tests', ['laboratory.view']],
                ['Highlight abnormal results', ['laboratory.view']],
                ['Review verification checklist', ['laboratory.verify_result']],
              ]
            : path.startsWith('/radiology')
              ? [
                  ['Summarize imaging order status', ['radiology.view']],
                  ['Check pending PACS uploads', ['radiology.view']],
                  ['Review verification checklist', ['radiology.verify_result']],
                ]
              : path.startsWith('/ipd')
                ? [
                    ['Show IPD occupancy', ['ipd.view']],
                    ['Draft discharge summary', ['ipd.discharge']],
                    ['Check transfer readiness', ['ipd.transfer']],
                    ['Explain interim bill', ['billing.view']],
                  ]
                : path.startsWith('/hr')
                  ? [
                      ['Summarize employee attendance', ['hr.attendance.manage']],
                      ['Check leave balance', ['hr.leave.manage']],
                      ['Review payroll exceptions', ['payroll.view']],
                    ]
                  : path.startsWith('/inventory')
                    ? [
                        ['Find low-stock items', ['inventory.view']],
                        ['Review purchase requests', ['inventory.purchase']],
                        ['Summarize stock movements', ['inventory.view']],
                      ]
                    : [
                        ['Show today’s hospital summary', ['dashboard.view']],
                        ['Show operational alerts', ['dashboard.view']],
                        ['Show pending payments', ['billing.view']],
                        ['Show low-stock medicines', ['pharmacy.view']],
                      ];
    return suggestions.filter(([, permissions]) => this.canAny(...permissions)).map(([label]) => label);
  }

  private routeFilters(): Record<string, unknown> {
    const queryIndex = this.router.url.indexOf('?');
    if (queryIndex === -1) return {};
    const params = new URLSearchParams(this.router.url.slice(queryIndex + 1));
    const filters: Record<string, unknown> = {};
    params.forEach((value, key) => {
      filters[key] = value;
    });
    return filters;
  }

  trackByIndex(index: number): number {
    return index;
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) this.close();
  }
}
