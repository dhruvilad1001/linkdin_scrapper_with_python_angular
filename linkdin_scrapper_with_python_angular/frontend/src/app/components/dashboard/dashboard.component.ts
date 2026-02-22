import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService, Stats, Profile } from '../../services/api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="container">
      <h2>Dashboard</h2>
      
      <div class="stats-grid">
        <div class="stat-card">
          <h3>Total Profiles</h3>
          <p class="stat-number">{{ stats?.total_profiles || 0 }}</p>
        </div>
        <div class="stat-card">
          <h3>Today's Profiles</h3>
          <p class="stat-number">{{ stats?.today_profiles || 0 }}</p>
        </div>
        <div class="stat-card">
          <h3>Companies</h3>
          <p class="stat-number">{{ stats?.top_companies?.length || 0 }}</p>
        </div>
        <div class="stat-card">
          <h3>Schools</h3>
          <p class="stat-number">{{ stats?.top_schools?.length || 0 }}</p>
        </div>
      </div>

      <div class="card">
        <h3>Recent Profiles</h3>
        <div *ngIf="loading" class="loading">Loading...</div>
        <table *ngIf="!loading && recentProfiles.length > 0">
          <thead>
            <tr>
              <th>Name</th>
              <th>Headline</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let profile of recentProfiles">
              <td>{{ profile.name }}</td>
              <td>{{ profile.headline || 'N/A' }}</td>
              <td>{{ profile.last_updated | date:'short' }}</td>
              <td>
                <a [routerLink]="['/profiles', profile._id]" class="btn btn-primary btn-sm">View</a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin: 20px 0;
    }
    .stat-card {
      background: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      text-align: center;
    }
    .stat-card h3 {
      color: #666;
      font-size: 14px;
      margin-bottom: 10px;
    }
    .stat-number {
      font-size: 36px;
      font-weight: bold;
      color: #0a66c2;
    }
    .btn-sm {
      padding: 6px 12px;
      font-size: 12px;
    }
  `]
})
export class DashboardComponent implements OnInit {
  stats: Stats | null = null;
  recentProfiles: Profile[] = [];
  loading = true;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadStats();
    this.loadRecentProfiles();
  }

  loadStats() {
    this.apiService.getStats().subscribe({
      next: (data) => this.stats = data,
      error: (err) => console.error('Error loading stats:', err)
    });
  }

  loadRecentProfiles() {
    this.apiService.getProfiles(0, 5).subscribe({
      next: (data) => {
        this.recentProfiles = data;
        this.loading = false;
      },
      error: (err) => {
        console.error('Error loading profiles:', err);
        this.loading = false;
      }
    });
  }
}
