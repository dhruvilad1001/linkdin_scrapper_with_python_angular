import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService, Profile } from '../../services/api.service';

@Component({
  selector: 'app-profile-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container">
      <button (click)="goBack()" class="btn btn-secondary">← Back</button>

      <div *ngIf="loading" class="loading">Loading profile...</div>
      <div *ngIf="error" class="error">{{ error }}</div>

      <div *ngIf="profile && !loading" class="profile-detail">
        <div class="card">
          <h2>{{ profile.name }}</h2>
          <p class="headline">{{ profile.headline }}</p>
          <a [href]="profile.url" target="_blank" class="profile-link">View on LinkedIn →</a>
        </div>

        <div class="card" *ngIf="profile.about">
          <h3>About</h3>
          <p>{{ profile.about }}</p>
        </div>

        <div class="card" *ngIf="profile.experience && profile.experience.length > 0">
          <h3>Experience ({{ profile.experience.length }})</h3>
          <div class="experience-item" *ngFor="let exp of profile.experience">
            <h4>{{ exp.designation }}</h4>
            <p class="company">{{ exp.company_name }}</p>
            <p class="duration">{{ exp.duration }}</p>
            <p class="location" *ngIf="exp.location">{{ exp.location }}</p>
          </div>
        </div>

        <div class="card" *ngIf="profile.education && profile.education.length > 0">
          <h3>Education ({{ profile.education.length }})</h3>
          <div class="education-item" *ngFor="let edu of profile.education">
            <h4>{{ edu.college }}</h4>
            <p>{{ edu.degree }}</p>
            <p class="duration">{{ edu.duration }}</p>
            <p *ngIf="edu.grade">Grade: {{ edu.grade }}</p>
          </div>
        </div>

        <div class="card" *ngIf="profile.projects && profile.projects.length > 0">
          <h3>Projects ({{ profile.projects.length }})</h3>
          <div class="project-item" *ngFor="let project of profile.projects">
            <h4>{{ project.project_name }}</h4>
            <p class="duration">{{ project.duration }}</p>
            <p *ngIf="project.description">{{ project.description }}</p>
          </div>
        </div>

        <div class="card" *ngIf="profile.licenses && profile.licenses.length > 0">
          <h3>Licenses & Certifications ({{ profile.licenses.length }})</h3>
          <div class="license-item" *ngFor="let license of profile.licenses">
            <h4>{{ license.name }}</h4>
            <p>{{ license.institute }}</p>
            <p class="duration">{{ license.issued_date }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .headline {
      color: #666;
      font-size: 18px;
      margin: 10px 0;
    }
    .profile-link {
      color: #0a66c2;
      text-decoration: none;
    }
    .experience-item, .education-item, .project-item, .license-item {
      padding: 15px 0;
      border-bottom: 1px solid #eee;
    }
    .experience-item:last-child, .education-item:last-child, 
    .project-item:last-child, .license-item:last-child {
      border-bottom: none;
    }
    h4 {
      margin-bottom: 5px;
    }
    .company, .duration, .location {
      color: #666;
      font-size: 14px;
      margin: 5px 0;
    }
  `]
})
export class ProfileDetailComponent implements OnInit {
  profile: Profile | null = null;
  loading = true;
  error = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) {}

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadProfile(id);
    }
  }

  loadProfile(id: string) {
    this.apiService.getProfile(id).subscribe({
      next: (data) => {
        this.profile = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load profile';
        this.loading = false;
        console.error(err);
      }
    });
  }

  goBack() {
    this.router.navigate(['/profiles']);
  }
}
