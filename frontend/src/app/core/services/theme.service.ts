import { DOCUMENT } from '@angular/common';
import { Injectable, inject, signal } from '@angular/core';

export type AppTheme = 'ocean' | 'forest' | 'sunset' | 'midnight';

export interface ThemeOption {
  value: AppTheme;
  label: string;
}

@Injectable({ providedIn: 'root' })
export class ThemeService {
  static readonly STORAGE_KEY = 'hms.theme';

  private readonly document = inject(DOCUMENT);
  private readonly activeThemeSignal = signal<AppTheme>('ocean');

  readonly themeOptions: ThemeOption[] = [
    { value: 'ocean', label: 'Ocean' },
    { value: 'forest', label: 'Forest' },
    { value: 'sunset', label: 'Sunset' },
    { value: 'midnight', label: 'Midnight' },
  ];

  readonly activeTheme = this.activeThemeSignal.asReadonly();

  initialize(): void {
    const storedTheme = this.readStoredTheme();
    this.applyTheme(storedTheme);
  }

  setTheme(theme: AppTheme): void {
    this.applyTheme(theme);
    localStorage.setItem(ThemeService.STORAGE_KEY, theme);
  }

  private applyTheme(theme: AppTheme): void {
    this.document.documentElement.setAttribute('data-theme', theme);
    this.activeThemeSignal.set(theme);
  }

  private readStoredTheme(): AppTheme {
    const storedValue = localStorage.getItem(ThemeService.STORAGE_KEY);
    return this.themeOptions.some((theme) => theme.value === storedValue) ? (storedValue as AppTheme) : 'ocean';
  }
}
