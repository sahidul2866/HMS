import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, effect, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ConnectionStateService } from '../../../core/services/connection-state.service';
import { AuthService } from '../../../core/services/auth.service';
import { SessionService } from '../../../core/services/session.service';
import { NotificationService } from '../../../core/services/notification.service';

@Component({
  selector: 'app-state', standalone: true, imports: [CommonModule, FormsModule],
  template: `
    @if (state.offline() || state.cachedAt() || state.lightMode()) {
      <aside class="connection-banner" role="status">
        <strong>{{ state.offline() ? 'You’re offline.' : state.lightMode() ? 'Lighter view is on.' : 'Showing previously loaded information.' }}</strong>
        @if (state.offline()) {
          <span>You can review loaded records and keep editing open forms. Saving, payments, and new searches need a connection.</span>
        }
        @if (state.lightMode()) {
          <span>Loading animations are reduced and previously loaded records are used when available to reduce network requests.</span>
          <button type="button" (click)="state.lightMode.set(false)">Use live data</button>
        }
        @if (state.cachedAt(); as at) { <span>Cached copy from {{ at | date:'short' }}; it may be out of date.</span> }
        @if (!state.offline()) { <span>Use the page’s refresh or search action to retrieve current information before making changes.</span> }
      </aside>
    }
    <section class="feedback-stack" aria-label="Action feedback" aria-live="polite">
      @for (item of notifications.items(); track item.id) {
        <article [attr.role]="item.level === 'error' ? 'alert' : 'status'" [class]="'feedback ' + item.level">
          <div><strong>{{ item.level === 'success' ? 'Completed' : item.level === 'error' ? 'Action needed' : item.level === 'warning' ? 'Please check' : 'Update' }}</strong><p>{{ item.message }}</p></div>
          <button type="button" (click)="notifications.dismiss(item.id)" aria-label="Dismiss message">×</button>
        </article>
      }
    </section>
    <dialog #signIn aria-labelledby="session-title" (cancel)="$event.preventDefault()">
      @if (state.sessionExpired()) {
        <form (ngSubmit)="resume()">
          <h2 id="session-title">Your session has expired</h2>
          <p>Your open forms are still here. Sign in with the same account, then review and submit your work again. The failed action has not been retried.</p>
          <label>Account <input name="account" [value]="session.snapshot.user?.username" readonly autocomplete="username"></label>
          <label>Password <input #passwordInput name="password" type="password" [(ngModel)]="password" required autocomplete="current-password" [disabled]="busy"></label>
          @if (error) { <p role="alert">{{ error }}</p> }
          <button type="submit" [disabled]="busy || !password || state.offline()">{{ busy ? 'Signing in…' : 'Sign in and resume' }}</button>
          <button type="button" (click)="signOut()" [disabled]="busy">Discard open work and sign out</button>
        </form>
      }
    </dialog>
  `,
  styles: [`
    .feedback-stack { position: fixed; top: 1rem; right: 1rem; z-index: 2800; width: min(400px, calc(100vw - 2rem)); display: grid; gap: .6rem; max-height: 70vh; overflow: auto; pointer-events: none; }
    .feedback { pointer-events: auto; display: flex; gap: 1rem; align-items: start; padding: 1rem; background: var(--surface); color: var(--text); border: 1px solid var(--border); border-left: 4px solid var(--primary); border-radius: 10px; box-shadow: 0 8px 30px #0f172a22; }
    .feedback.error { border-left-color: #dc2626; } .feedback.success { border-left-color: #16a34a; } .feedback.warning { border-left-color: #d97706; }
    .feedback p { margin-top: .3rem; font-size: .9rem; } .feedback button { margin-left: auto; }
    .connection-banner { position: sticky; top: 0; z-index: 1700; display: flex; flex-wrap: wrap; gap: .4rem 1rem; padding: .75rem 1.25rem; color: var(--text); background: var(--surface); border-bottom: 2px solid #d97706; font-size: .9rem; }
    dialog { width: min(440px, calc(100vw - 2rem)); border: 1px solid var(--border); border-radius: 16px; padding: 1.5rem; background: var(--surface); color: var(--text); }
    dialog::backdrop { background: rgba(15,23,42,.7); backdrop-filter: blur(8px); }
    form, label { display: grid; gap: .65rem; } form { gap: 1rem; } h2, p { margin: 0; } p { line-height: 1.5; }
    input, button { padding: .7rem; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); color: var(--text); }
    button[type=submit] { background: var(--primary); color: white; } button:disabled { opacity: .6; }
  `],
})
export class AppStateComponent {
  readonly state = inject(ConnectionStateService);
  readonly session = inject(SessionService);
  private readonly auth = inject(AuthService);
  readonly notifications = inject(NotificationService);
  @ViewChild('signIn', { static: true }) dialog!: ElementRef<HTMLDialogElement>;
  password = '';
  busy = false;
  error = '';

  constructor() {
    effect(() => {
      if (this.state.sessionExpired()) {
        this.dialog.nativeElement.showModal();
        setTimeout(() => this.dialog.nativeElement.querySelector<HTMLInputElement>('input[type=password]')?.focus());
      } else {
        this.dialog.nativeElement.close();
        this.password = '';
        this.error = '';
      }
    });
  }

  resume(): void {
    if (this.busy || !this.password || this.state.offline()) return;
    this.busy = true;
    this.error = '';
    this.auth.login(this.session.snapshot.user!.username, this.password, this.session.snapshot.user!.id).subscribe({
      next: () => {
        this.busy = false;
        this.password = '';
        this.notifications.success('Signed in. Review your open form and submit again when ready.', '');
      },
      error: (error) => {
        this.busy = false;
        this.password = '';
        this.error = error?.status === 401 ? 'The password was not accepted. Check it and try again.' : error?.message || 'Unable to sign in. Check your connection and try again.';
      },
    });
  }

  signOut(): void {
    if (window.confirm('Discard your open work and sign out?')) this.auth.logout().subscribe();
  }
}
