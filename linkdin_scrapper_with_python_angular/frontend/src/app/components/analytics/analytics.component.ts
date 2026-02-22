import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService, Stats } from '../../services/api.service';

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="container">
      <h2>Analytics</h2>

      <div class="card">
        <h3>Overview</h3>
        <div class="stats-row">
          <div class="stat-item">
            <span class="stat-label">Total Profiles:</span>
            <span class="stat-value">{{ stats?.total_profiles || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Today's Profiles:</span>
            <span class="stat-value">{{ stats?.today_profiles || 0 }}</span>
          </div>
        </div>
      </div>

      <div class="card">
        <h3>Top Companies</h3>
        <div *ngIf="stats && stats.top_companies && stats.top_companies.length > 0">
          <div class="chart-item" *ngFor="let company of stats.top_companies">
            <span class="chart-label">{{ company._id || 'Unknown' }}</span>
            <div class="chart-bar">
              <div class="chart-fill" [style.width.%]="getPercentage(company.count, maxCompanyCount)"></div>
              <span class="chart-count">{{ company.count }}</span>
            </div>
          </div>
        </div>
        <p *ngIf="!stats || !stats.top_companies || stats.top_companies.length === 0">No data available</p>
      </div>

      <div class="card">
        <h3>Top Schools</h3>
        <div *ngIf="stats && stats.top_schools && stats.top_schools.length > 0">
          <div class="chart-item" *ngFor="let school of stats.top_schools">
            <span class="chart-label">{{ school._id || 'Unknown' }}</span>
            <div class="chart-bar">
              <div class="chart-fill" [style.width.%]="getPercentage(school.count, maxSchoolCount)"></div>
              <span class="chart-count">{{ school.count }}</span>
            </div>
          </div>
        </div>
        <p *ngIf="!stats || !stats.top_schools || stats.top_schools.length === 0">No data available</p>
      </div>
    </div>
  `,
  styles: [`
    .stats-row {
      display: flex;
      gap: 40px;
      margin: 20px 0;
    }
    .stat-item {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .stat-label {
      color: #666;
      font-size: 14px;
    }
    .stat-value {
      font-size: 32px;
      font-weight: bold;
      color: #0a66c2;
    }
    .chart-item {
      margin: 15px 0;
    }
    .chart-label {
      display: block;
      margin-bottom: 5px;
      font-weight: 500;
    }
    .chart-bar {
      position: relative;
      background: #f0f0f0;
      height: 30px;
      border-radius: 4px;
      overflow: hidden;
    }
    .chart-fill {
      background: linear-gradient(90deg, #0a66c2, #004182);
      height: 100%;
      transition: width 0.3s;
    }
    .chart-count {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: #333;
      font-weight: 600;
      font-size: 14px;
    }
  `]
})
export class AnalyticsComponent implements OnInit {
  stats: Stats | null = null;
  maxCompanyCount = 0;
  maxSchoolCount = 0;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadStats();
  }

  loadStats() {
    this.apiService.getStats().subscribe({
      next: (data) => {
        this.stats = data;
        
        if (data.top_companies && data.top_companies.length > 0) {
          this.maxCompanyCount = Math.max(...data.top_companies.map(c => c.count));
        }
        
        if (data.top_schools && data.top_schools.length > 0) {
          this.maxSchoolCount = Math.max(...data.top_schools.map(s => s.count));
        }
      },
      error: (err) => console.error('Error loading stats:', err)
    });
  }

  getPercentage(value: number, max: number): number {
    return max > 0 ? (value / max) * 100 : 0;
  }
}
