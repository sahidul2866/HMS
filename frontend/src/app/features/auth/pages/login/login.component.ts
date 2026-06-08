import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly sessionService = inject(SessionService);
  private readonly router = inject(Router);

  errorMessage = '';
  loading = false;
  showPassword = false;
  resetRequired = false;
  resetLoading = false;
  resetMessage = '';

  readonly form = this.fb.nonNullable.group({
    username_or_email: ['superadmin', [Validators.required]],
    password: ['Admin123!', [Validators.required, Validators.minLength(8)]],
  });

  readonly resetForm = this.fb.nonNullable.group({
    current_password: ['', [Validators.required, Validators.minLength(8)]],
    new_password: ['', [Validators.required, Validators.minLength(8)]],
  });

  constructor() {
    this.sessionService.state$
      .pipe(filter((state) => state.initialized && state.authenticated))
      .subscribe(() => {
        void this.redirectFromLogin(this.sessionService.getLandingRoute());
      });

    if (this.sessionService.snapshot.authenticated) {
      void this.redirectFromLogin(this.sessionService.getLandingRoute());
    }
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  submit(): void {
    if (this.form.invalid || this.loading) {
      return;
    }

    this.errorMessage = '';
    this.loading = true;
    this.authService.login(this.form.getRawValue().username_or_email, this.form.getRawValue().password).subscribe({
      next: (user) => {
        this.loading = false;
        if (user.must_reset_password) {
          this.resetRequired = true;
          this.resetForm.patchValue({ current_password: this.form.getRawValue().password, new_password: '' });
          this.notificationService.warning('Reset your temporary password before continuing.');
          return;
        }
        this.notificationService.success('Login successful.');
        void this.redirectFromLogin(this.authService.getLandingRoute(user));
      },
      error: (error) => {
        this.loading = false;
        this.errorMessage = error.message ?? 'Unable to login';
      },
    });
  }

  submitReset(): void {
    if (this.resetForm.invalid || this.resetLoading) {
      return;
    }
    this.resetLoading = true;
    this.resetMessage = '';
    this.authService.resetPassword(this.resetForm.getRawValue()).subscribe({
      next: () => {
        this.resetLoading = false;
        this.notificationService.success('Password updated.');
        void this.redirectFromLogin(this.sessionService.getLandingRoute());
      },
      error: (error) => {
        this.resetLoading = false;
        this.resetMessage = error.message ?? 'Unable to update password';
      },
    });
  }

  private async redirectFromLogin(route: string): Promise<void> {
    if (!route || !this.router.url.startsWith('/auth/login')) {
      return;
    }
    const navigated = await this.router.navigateByUrl(route);
    if (navigated) {
      return;
    }
    window.location.hash = `#${route.startsWith('/') ? route : `/${route}`}`;
  }
}
