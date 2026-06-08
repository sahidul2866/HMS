import { CommonModule } from '@angular/common';
import { Component, HostListener, inject } from '@angular/core';
import { Router, RouterOutlet } from '@angular/router';

import { PERMISSIONS } from '../../core/constants/permissions';
import { AuthService } from '../../core/services/auth.service';
import { CommandPaletteService } from '../../core/services/command-palette.service';
import { NotificationService } from '../../core/services/notification.service';
import { RoleExperienceService } from '../../core/services/role-experience.service';
import { SessionService } from '../../core/services/session.service';
import { TabService } from '../../core/services/tab.service';
import { ThemeService } from '../../core/services/theme.service';
import { MenuItem, menuConfig } from '../../navigation/menu.config';
import { SidebarComponent } from '../../navigation/sidebar/sidebar.component';
import { BreadcrumbsComponent } from '../../shared/components/breadcrumbs/breadcrumbs.component';
import { CommandPaletteComponent } from '../../shared/components/command-palette/command-palette.component';
import { FloatingAssistantComponent } from '../../shared/components/floating-assistant/floating-assistant.component';
import { GlobalScannerComponent } from '../../shared/components/global-scanner/global-scanner.component';
import { NotificationCenterComponent } from '../../shared/components/notification-center/notification-center.component';
import { TabStripComponent } from '../../shared/components/tab-strip/tab-strip.component';

type ChromeDensity = 'full' | 'compact' | 'focus';

@Component({
  selector: 'app-app-layout',
  standalone: true,
  imports: [CommonModule, RouterOutlet, SidebarComponent, TabStripComponent, BreadcrumbsComponent, FloatingAssistantComponent, GlobalScannerComponent, CommandPaletteComponent, NotificationCenterComponent],
  templateUrl: './app-layout.component.html',
  styleUrl: './app-layout.component.scss',
})
export class AppLayoutComponent {
  private static readonly QUICK_FLOW_STATE_KEY = 'hms.quickFlow.collapsedGroups';
  private static readonly CHROME_DENSITY_KEY = 'hms.chromeDensity';
  readonly sessionService = inject(SessionService);
  readonly tabService = inject(TabService);
  readonly themeService = inject(ThemeService);
  readonly quickActions = [
    { label: 'New Bill', route: '/billing/create', permissions: [PERMISSIONS.billingInvoiceCreate], tone: 'primary' },
    { label: 'Due', route: '/billing/due-payments', permissions: [PERMISSIONS.billingInvoiceCreate] },
    { label: 'OPD List', route: '/opd/visits', permissions: [PERMISSIONS.opdView] },
    { label: 'IPD List', route: '/ipd/admissions', permissions: [PERMISSIONS.ipdAdmissionManage] },
    { label: 'Diagnostics', route: '/diagnostics/orders', permissions: [PERMISSIONS.laboratoryView] },
    { label: 'Pharmacy Sale', route: '/pharmacy/sales', permissions: [PERMISSIONS.pharmacyView] },
  ];
  readonly chromeDensityOptions: { value: ChromeDensity; label: string; title: string }[] = [
    { value: 'full', label: 'Full', title: 'Show account, breadcrumbs, page tabs, and module actions' },
    { value: 'compact', label: 'Compact', title: 'Keep navigation available while reducing page chrome' },
    { value: 'focus', label: 'Focus', title: 'Maximize page data area' },
  ];
  readonly keyboardShortcuts = [
    { key: 'Alt+1', label: 'Dashboard' },
    { key: 'Alt+2', label: 'Patients' },
    { key: 'Alt+3', label: 'OPD Visits' },
    { key: 'Alt+4', label: 'New Bill' },
    { key: 'Alt+5', label: 'Pharmacy Sale' },
    { key: 'Alt+6', label: 'Lab Worklist' },
    { key: 'Alt+7', label: 'Radiology' },
    { key: 'Alt+Q', label: 'Queue center' },
    { key: 'Alt+B', label: 'Global barcode/QR scan' },
    { key: 'Ctrl/Cmd+K', label: 'Command palette' },
    { key: 'Ctrl/Cmd+S', label: 'Save focused form' },
    { key: 'Ctrl/Cmd+P', label: 'Print on supported pages' },
    { key: '? or Ctrl+/', label: 'User manual' },
    { key: 'Alt+S', label: 'Sidebar' },
    { key: 'Alt+M', label: 'Top density' },
    { key: 'Alt+/', label: 'Search/filter' },
    { key: 'Alt+[ / ]', label: 'Previous/next open page' },
  ];
  private readonly authService = inject(AuthService);
  private readonly commandPalette = inject(CommandPaletteService);
  private readonly notificationService = inject(NotificationService);
  private readonly roleExperience = inject(RoleExperienceService);
  private readonly router = inject(Router);

  sidebarCollapsed = false;
  mobileSidebarOpen = false;
  isMobileViewport = false;
  accountMenuOpen = false;
  shortcutsOpen = false;
  chromeDensity: ChromeDensity = 'compact';
  collapsedQuickFlowGroups = new Set<string>(['module', 'fast', 'recent']);

  constructor() {
    this.syncViewport();
    this.restoreQuickFlowState();
    this.restoreChromeDensity();
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    this.syncViewport();
  }

  @HostListener('window:keydown', ['$event'])
  onWindowKeydown(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      this.commandPalette.show({ module: this.activeModule()?.label });
      return;
    }

    if ((event.key === '?' || ((event.ctrlKey || event.metaKey) && event.key === '/')) && !this.isTypingTarget(event.target)) {
      event.preventDefault();
      this.openManual();
      return;
    }

    if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || this.isTypingTarget(event.target)) {
      return;
    }

    const key = event.key.toLowerCase();
    const roleRoute = this.roleShortcutRoute(key);
    if (roleRoute) {
      event.preventDefault();
      this.navigate(roleRoute);
      return;
    }

    const routeMap: Record<string, string> = {
      '1': '/dashboard',
      '2': '/patients',
      '3': '/opd/visits',
      '4': '/billing/create',
      '5': '/pharmacy/sales',
      '6': '/laboratory',
      '7': '/radiology',
      q: '/queue',
    };

    if (routeMap[key]) {
      event.preventDefault();
      this.navigate(routeMap[key]);
      return;
    }

    if (key === 's') {
      event.preventDefault();
      if (this.isMobileViewport) {
        this.toggleMobileSidebar();
      } else {
        this.sidebarCollapsed = !this.sidebarCollapsed;
      }
      return;
    }

    if (key === 'm') {
      event.preventDefault();
      this.cycleChromeDensity();
      return;
    }

    if (key === '/') {
      event.preventDefault();
      this.focusFirstFilter();
      return;
    }

    if (event.key === '[' || event.key === ']') {
      event.preventDefault();
      this.activateAdjacentTab(event.key === ']' ? 1 : -1);
    }
  }

  toggleMobileSidebar(): void {
    this.mobileSidebarOpen = !this.mobileSidebarOpen;
  }

  closeMobileSidebar(): void {
    this.mobileSidebarOpen = false;
  }

  toggleAccountMenu(): void {
    this.accountMenuOpen = !this.accountMenuOpen;
    this.shortcutsOpen = false;
  }

  closeAccountMenu(): void {
    this.accountMenuOpen = false;
  }

  setChromeDensity(value: ChromeDensity): void {
    this.chromeDensity = value;
    localStorage.setItem(AppLayoutComponent.CHROME_DENSITY_KEY, value);
  }

  cycleChromeDensity(): void {
    const values = this.chromeDensityOptions.map((option) => option.value);
    const currentIndex = values.indexOf(this.chromeDensity);
    const nextValue = values[(currentIndex + 1) % values.length] ?? 'compact';
    this.setChromeDensity(nextValue);
  }

  toggleShortcuts(): void {
    this.shortcutsOpen = !this.shortcutsOpen;
    this.accountMenuOpen = false;
  }

  openManual(): void {
    this.shortcutsOpen = false;
    this.accountMenuOpen = false;
    this.navigate('/manual');
  }

  logout(): void {
    this.accountMenuOpen = false;
    this.authService.logout().subscribe(() => this.notificationService.info('Logged out.'));
  }

  openProfile(): void {
    this.accountMenuOpen = false;
    this.navigate('/profile');
  }

  switchTheme(): void {
    this.themeService.setTheme(this.themeService.activeTheme() === 'midnight' ? 'ocean' : 'midnight');
    this.accountMenuOpen = false;
  }

  visibleQuickActions(): Array<{ label: string; route: string; permissions: string[]; tone?: string }> {
    const roleActions = this.roleExperience.visibleActions().map((action) => ({
      label: action.label,
      route: action.route,
      permissions: action.permissions,
      tone: action.tone,
    }));
    const genericActions = this.quickActions.filter((action) => this.sessionService.hasPermission(action.permissions));
    const byRoute = new Map<string, { label: string; route: string; permissions: string[]; tone?: string }>();
    [...roleActions, ...genericActions].forEach((action) => byRoute.set(action.route, action));
    return [...byRoute.values()].slice(0, 8);
  }

  activeModule(): MenuItem | null {
    const currentPath = this.currentPath();
    return (
      menuConfig.find((item) => {
        if (item.children?.some((child) => this.routeMatches(child.route, currentPath))) {
          return true;
        }
        return this.routeMatches(item.route, currentPath);
      }) ?? null
    );
  }

  activeModuleActions(): MenuItem[] {
    const activeModule = this.activeModule();
    if (!activeModule?.children?.length) {
      return [];
    }
    return activeModule.children
      .filter((item) => item.route && this.sessionService.hasPermission(item.permissions))
      .slice(0, 8);
  }

  recentPages(): { path: string; label: string }[] {
    const activePath = this.tabService.activePath();
    return this.tabService
      .tabs()
      .filter((tab) => tab.path !== activePath)
      .slice(-4)
      .reverse();
  }

  isQuickFlowGroupCollapsed(group: string): boolean {
    return this.collapsedQuickFlowGroups.has(group);
  }

  toggleQuickFlowGroup(group: string): void {
    const next = new Set(this.collapsedQuickFlowGroups);
    if (next.has(group)) {
      next.delete(group);
    } else {
      next.add(group);
    }
    this.collapsedQuickFlowGroups = next;
    this.persistQuickFlowState();
  }

  quickFlowGroupCount(group: 'module' | 'fast' | 'recent'): number {
    switch (group) {
      case 'module':
        return this.activeModuleActions().length;
      case 'fast':
        return this.visibleQuickActions().length;
      case 'recent':
        return this.recentPages().length;
    }
  }

  isQuickActionActive(route: string): boolean {
    return this.routeMatches(route, this.currentPath());
  }

  navigate(route: string): void {
    this.router.navigateByUrl(route);
    this.shortcutsOpen = false;
    this.closeMobileSidebar();
  }

  userInitials(): string {
    const name = this.sessionService.snapshot.user?.full_name || 'User';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }

  accountTypeLabel(): string {
    const user = this.sessionService.snapshot.user;
    if (user?.principal_type === 'patient' || user?.patient_id) {
      return 'Patient Portal';
    }
    return user?.roles?.[0]?.name || 'Staff Account';
  }

  roleKeyboardShortcuts(): Array<{ key: string; label: string }> {
    return this.roleExperience.visibleShortcuts().map((item) => ({ key: item.key, label: item.label }));
  }

  showStaffAssistant(): boolean {
    const user = this.sessionService.snapshot.user;
    return !!user && user.principal_type !== 'patient' && !user.patient_id && this.sessionService.hasPermission('ai.assistant.use');
  }

  private syncViewport(): void {
    this.isMobileViewport = window.innerWidth <= 1100;
    if (!this.isMobileViewport) {
      this.mobileSidebarOpen = false;
    }
  }

  private currentPath(): string {
    return this.router.url.split('?')[0].split('#')[0] || '/';
  }

  private routeMatches(route: string | undefined, currentPath: string): boolean {
    return !!route && (currentPath === route || currentPath.startsWith(`${route}/`));
  }

  private persistQuickFlowState(): void {
    localStorage.setItem(AppLayoutComponent.QUICK_FLOW_STATE_KEY, JSON.stringify([...this.collapsedQuickFlowGroups]));
  }

  private restoreChromeDensity(): void {
    const stored = localStorage.getItem(AppLayoutComponent.CHROME_DENSITY_KEY) as ChromeDensity | null;
    this.chromeDensity = stored === 'full' || stored === 'compact' || stored === 'focus' ? stored : 'compact';
  }

  private restoreQuickFlowState(): void {
    const stored = localStorage.getItem(AppLayoutComponent.QUICK_FLOW_STATE_KEY);
    if (!stored) {
      return;
    }
    try {
      const groups = JSON.parse(stored) as string[];
      this.collapsedQuickFlowGroups = new Set(Array.isArray(groups) ? groups : ['module', 'fast', 'recent']);
    } catch {
      localStorage.removeItem(AppLayoutComponent.QUICK_FLOW_STATE_KEY);
    }
  }

  private isTypingTarget(target: EventTarget | null): boolean {
    if (!(target instanceof HTMLElement)) {
      return false;
    }
    const tagName = target.tagName.toLowerCase();
    return tagName === 'input' || tagName === 'textarea' || tagName === 'select' || target.isContentEditable;
  }

  private focusFirstFilter(): void {
    const target = document.querySelector<HTMLElement>(
      '.content input[type="search"], .content .table-toolbar input, .content .filter-grid input, .content input:not([type="hidden"]), .content select'
    );
    target?.focus();
  }

  private activateAdjacentTab(direction: 1 | -1): void {
    const tabs = this.tabService.tabs();
    if (tabs.length < 2) {
      return;
    }
    const activePath = this.tabService.activePath();
    const currentIndex = tabs.findIndex((tab) => tab.path === activePath);
    const nextIndex = (currentIndex + direction + tabs.length) % tabs.length;
    this.tabService.activate(tabs[nextIndex]?.path ?? tabs[0].path);
  }

  private roleShortcutRoute(key: string): string | null {
    const candidates = [`Alt+${key.toUpperCase()}`, `Alt+${key}`];
    for (const candidate of candidates) {
      const route = this.roleExperience.routeForShortcut(candidate);
      if (route) return route;
    }
    return null;
  }
}
