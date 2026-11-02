import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Subject, firstValueFrom, takeUntil, timeout } from 'rxjs';
import { QueueToken } from '../../features/queue/models/queue.models';
import { runtimeConfig } from '../config/runtime-config';
import { SKIP_ERROR_NOTIFICATION, SKIP_GLOBAL_LOADER } from '../http/http-context.tokens';

type Announcement = { text: string; language: string; scope: string; createdAt: number };

/** Runs on the display computer connected to the PA; Azure keys remain on the server. */
@Injectable({ providedIn: 'root' })
export class QueueAnnouncementService {
  private readonly http = inject(HttpClient);
  readonly enabled = signal(false);
  readonly message = signal('PA audio is off. Enable it on the computer connected to the PA speakers.');
  readonly engine = signal('Azure neural voice preferred');
  readonly supported = typeof window !== 'undefined' && typeof Audio !== 'undefined';
  language = 'en-US';
  queueScope = 'opd';
  private readonly seen = new Map<string, string>();
  private readonly stopped = new Subject<void>();
  private tasks: Announcement[] = [];
  private generation = 0;
  private draining: number | null = null;
  private neuralReady: Promise<boolean> = Promise.resolve(false);
  private cancelPlayback: (() => void) | null = null;

  enable(tokens: QueueToken[]): void {
    if (!this.supported) {
      this.message.set('Audio is unavailable in this browser. Call the displayed serial manually.');
      return;
    }
    this.disable();
    const generation = this.generation;
    this.seen.clear();
    for (const token of tokens) if (token.called_at) this.seen.set(token.id, token.called_at);
    this.enabled.set(true);
    this.engine.set('Checking Azure neural voice…');
    this.neuralReady = this.loadConfiguration(generation);
    this.enqueue(this.language.startsWith('bn') ? 'ঘোষণা চালু হয়েছে। অনুগ্রহ করে পিএ স্পিকারের শব্দ পরীক্ষা করুন।' : 'Queue announcements enabled. Please check the PA speaker volume.');
  }

  disable(): void {
    this.enabled.set(false);
    this.generation += 1;
    this.tasks = [];
    this.stopped.next();
    this.cancelPlayback?.();
    this.cancelPlayback = null;
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
    this.message.set('PA audio is off. Serial calls still appear on the display.');
  }

  consume(tokens: QueueToken[], destination: (token: QueueToken) => string): void {
    if (!this.enabled()) return;
    for (const token of [...tokens].sort((a, b) => (a.called_at || '').localeCompare(b.called_at || ''))) {
      if (!token.called_at || !['called', 'recalled'].includes(token.status) || this.seen.get(token.id) === token.called_at) continue;
      this.seen.set(token.id, token.called_at);
      if (Date.now() - new Date(token.called_at).getTime() > 120000) continue;
      this.enqueue(this.language.startsWith('bn')
        ? `সিরিয়াল ${token.token_sequence}। অনুগ্রহ করে ${destination(token)} এর কাছে যান।`
        : `Serial ${token.token_sequence}. Please proceed to ${destination(token)}.`);
    }
    if (this.seen.size > 1000) this.seen.delete(this.seen.keys().next().value!);
  }

  test(): void {
    if (this.enabled()) this.enqueue(this.language.startsWith('bn')
      ? 'পিএ শব্দ পরীক্ষা। অপেক্ষার স্থানে এই ঘোষণা শোনা যাচ্ছে কিনা নিশ্চিত করুন।'
      : 'PA sound check. Please confirm this announcement can be heard in the waiting area.');
  }

  private context(): HttpContext {
    return new HttpContext().set(SKIP_GLOBAL_LOADER, true).set(SKIP_ERROR_NOTIFICATION, true);
  }

  private async loadConfiguration(generation: number): Promise<boolean> {
    try {
      const config = await firstValueFrom(this.http.get<{ available: boolean }>(`${runtimeConfig.apiBaseUrl}/queue/speech/config`, { context: this.context() }).pipe(timeout({ first: 3000 }), takeUntil(this.stopped)));
      if (generation === this.generation) this.engine.set(config.available ? 'Azure neural voice' : 'Device voice · Azure credentials not configured');
      return config.available;
    } catch {
      if (generation === this.generation) this.engine.set('Device voice · neural service unavailable');
      return false;
    }
  }

  private enqueue(text: string): void {
    if (this.tasks.length >= 32) {
      this.message.set('Too many pending announcements. Review the display and call the next serial again when the PA is clear.');
      return;
    }
    this.tasks.push({ text, language: this.language, scope: this.queueScope, createdAt: Date.now() });
    void this.drain();
  }

  private async drain(): Promise<void> {
    const generation = this.generation;
    if (this.draining === generation) return;
    this.draining = generation;
    const neural = await this.neuralReady;
    while (this.enabled() && generation === this.generation && this.tasks.length) {
      const task = this.tasks.shift()!;
      if (Date.now() - task.createdAt > 120000) continue;
      let audio: Blob | null = null;
      if (neural) {
        try {
          this.engine.set('Azure neural voice');
          this.message.set('Preparing neural PA announcement…');
          audio = await firstValueFrom(this.http.post(`${runtimeConfig.apiBaseUrl}/queue/speech`, { text: task.text, language: task.language, queue_scope: task.scope }, { responseType: 'blob', context: this.context() }).pipe(timeout({ first: 10000 }), takeUntil(this.stopped)));
          if (!audio.size || !audio.type.startsWith('audio/')) throw new Error('Invalid audio');
        } catch {
          if (generation === this.generation) this.engine.set('Device voice · neural request failed');
          audio = null;
        }
      }
      if (!this.enabled() || generation !== this.generation) break;
      if (audio) await this.playAudio(audio);
      else await this.playDeviceVoice(task);
    }
    if (this.draining === generation) this.draining = null;
  }

  private playAudio(blob: Blob): Promise<void> {
    return new Promise(resolve => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      let finished = false;
      const finish = (message?: string) => {
        if (finished) return;
        finished = true;
        audio.onended = null;
        audio.onerror = null;
        audio.pause();
        audio.removeAttribute('src');
        URL.revokeObjectURL(url);
        this.cancelPlayback = null;
        if (message) this.message.set(message);
        resolve();
      };
      this.cancelPlayback = () => finish();
      audio.onended = () => finish('Neural announcement played. Confirm audibility at the PA speakers.');
      audio.onerror = () => finish('Neural audio could not play. Check browser sound permissions and the PA output, then use Test PA.');
      this.message.set('Playing Azure neural PA announcement…');
      audio.play().catch(() => finish('Audio playback was blocked. Enable browser sound and use Test PA.'));
    });
  }

  private playDeviceVoice(task: Announcement): Promise<void> {
    return new Promise(resolve => {
      if (!('speechSynthesis' in window) || typeof SpeechSynthesisUtterance === 'undefined') {
        this.message.set('Neural speech is unavailable and this device has no fallback voice. Call the serial manually.');
        resolve();
        return;
      }
      const utterance = new SpeechSynthesisUtterance(task.text);
      utterance.lang = task.language;
      const voice = window.speechSynthesis.getVoices().find(item => item.lang.toLowerCase() === task.language.toLowerCase());
      if (voice) utterance.voice = voice;
      utterance.rate = .9;
      let finished = false;
      const finish = (message?: string) => {
        if (finished) return;
        finished = true;
        this.cancelPlayback = null;
        if (message) this.message.set(message);
        resolve();
      };
      this.cancelPlayback = () => finish();
      utterance.onend = () => finish('Device-voice fallback played. Neural voice was unavailable for this announcement.');
      utterance.onerror = () => finish('Device audio could not play. Check browser sound permissions and the PA output.');
      this.message.set('Playing device-voice fallback…');
      try {
        window.speechSynthesis.speak(utterance);
      } catch {
        finish('Device audio could not play. Check browser sound permissions and the PA output.');
      }
    });
  }
}
