import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { PatientService } from '../../services/patient.service';
import { Patient } from '../../models/patient.models';

@Component({
  selector: 'app-patient-list',
  standalone: true,
  imports: [CommonModule, RouterLink, HasPermissionDirective],
  templateUrl: './patient-list.component.html',
  styleUrls: ['./patient-list.component.scss'],
})
export class PatientListComponent {
  private readonly patientService = inject(PatientService);
  private readonly router = inject(Router);

  patients: Patient[] = [];
  loading = true;

  constructor() {
    this.patientService.list().subscribe({
      next: (patients) => {
        this.patients = patients;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  openHistory(patient: Patient): void {
    void this.router.navigate(['/patients', patient.id]);
  }

  openBilling(patient: Patient): void {
    void this.router.navigate(['/billing/create'], { queryParams: { patientId: patient.id } });
  }

  openIpdAdmission(patient: Patient): void {
    void this.router.navigate(['/ipd/admit'], { queryParams: { patientId: patient.id } });
  }

  openOpdRegistration(patient: Patient): void {
    void this.router.navigate(['/opd/register'], { queryParams: { patientId: patient.id } });
  }
}
