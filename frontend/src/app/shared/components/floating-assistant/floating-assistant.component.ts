import { CommonModule } from '@angular/common';
import { Component, HostListener, Input, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { StaffBotResponse, StaffBotService, StaffBotSettings } from '../../../core/services/staff-bot.service';

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

  @Input() title = 'Staff Assistant';
  @Input() context: 'staff-dashboard' | string = 'staff-dashboard';

  open = false;
  loading = false;
  conversationId: string | null = null;
  input = '';
  messages: Array<{ sender: AssistantSender; text: string; createdAt: number; response?: StaffBotResponse }> = [];
  error = '';
  settings: StaffBotSettings | null = null;

  toggle(): void {
    this.open = !this.open;
    if (this.open && !this.messages.length) {
      this.bootstrap();
    }
  }

  close(): void {
    this.open = false;
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

    this.botService.sendMessage({ message: text, conversation_id: this.conversationId, context: this.context }).subscribe({
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
    this.botService.reset({ context: this.context }).subscribe({
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

  trackByIndex(index: number): number {
    return index;
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open) this.close();
  }
}
