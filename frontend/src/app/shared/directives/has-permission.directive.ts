import { Directive, Input, OnDestroy, TemplateRef, ViewContainerRef, inject } from '@angular/core';
import { Subscription } from 'rxjs';

import { SessionService } from '../../core/services/session.service';

@Directive({
  selector: '[appHasPermission]',
  standalone: true,
})
export class HasPermissionDirective implements OnDestroy {
  private readonly templateRef = inject(TemplateRef<unknown>);
  private readonly viewContainer = inject(ViewContainerRef);
  private readonly sessionService = inject(SessionService);
  private requiredPermissions: string[] = [];
  private readonly subscription: Subscription;

  @Input()
  set appHasPermission(value: string | string[]) {
    this.requiredPermissions = Array.isArray(value) ? value : [value];
    this.render();
  }

  constructor() {
    this.subscription = this.sessionService.state$.subscribe(() => this.render());
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  private render(): void {
    this.viewContainer.clear();
    if (!this.requiredPermissions.length || this.sessionService.hasPermission(this.requiredPermissions)) {
      this.viewContainer.createEmbeddedView(this.templateRef);
    }
  }
}
