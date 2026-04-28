import { AbstractControl, Validators } from '@angular/forms';

export class FormValidationUi {
  static isRequired(control: AbstractControl | null | undefined): boolean {
    return !!control?.hasValidator?.(Validators.required) || !!control?.hasValidator?.(Validators.requiredTrue);
  }

  static isInvalid(control: AbstractControl | null | undefined, submitted = false): boolean {
    return !!control && control.invalid && (control.touched || control.dirty || submitted);
  }

  static fieldStateLabel(control: AbstractControl | null | undefined): string {
    return this.isRequired(control) ? 'Mandatory' : 'Optional';
  }

  static errorMessage(control: AbstractControl | null | undefined, label: string): string {
    if (!control?.errors) {
      return '';
    }

    if (control.errors['required']) {
      return `${label} is required.`;
    }

    if (control.errors['email']) {
      return `Enter a valid ${label.toLowerCase()}.`;
    }

    if (control.errors['minlength']) {
      return `${label} must be at least ${control.errors['minlength'].requiredLength} characters.`;
    }

    if (control.errors['maxlength']) {
      return `${label} must be at most ${control.errors['maxlength'].requiredLength} characters.`;
    }

    if (control.errors['min']) {
      return `${label} must be at least ${control.errors['min'].min}.`;
    }

    if (control.errors['max']) {
      return `${label} must be at most ${control.errors['max'].max}.`;
    }

    return `${label} is invalid.`;
  }
}
