import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';

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
  private readonly router = inject(Router);

  errorMessage = '';
  loading = false;

  readonly form = this.fb.nonNullable.group({
    username_or_email: ['superadmin', [Validators.required]],
    password: ['Admin123!', [Validators.required, Validators.minLength(8)]],
  });

  submit(): void {
    if (this.form.invalid || this.loading) {
      return;
    }

    this.errorMessage = '';
    this.loading = true;
    this.authService.login(this.form.getRawValue().username_or_email, this.form.getRawValue().password).subscribe({
      next: (user) => {
        this.loading = false;
        this.notificationService.success('Login successful.');
        void this.router.navigate([this.authService.getLandingRoute(user)]);
      },
      error: (error) => {
        this.loading = false;
        this.errorMessage = error.message ?? 'Unable to login';
      },
    });
  }
}
