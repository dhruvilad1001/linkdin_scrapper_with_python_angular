import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService, Profile } from '../../services/api.service';

@Component({
  selector: 'app-profiles',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="container">
      <div class="header">
        <h2>Profiles</h2>
        <button (click)="exportProfiles()" class="btn btn-primary">Export to Excel</button>
      </div>

      <div class="card">
        <input 
          type="text" 
          [(ngModel)]="searchQuery" 
          (input)="onSearch()"
          placeholder="Search by name, headline, or company..."
          class="search-input"
        />
      </div>

      <div class="card">
        <div *ngIf="loading" class="loading">Loading profiles...</div>
        
        <div *ngIf="error" class="error">{{ error }}</div>

        <table *ngIf="!loading && profiles.length > 0">
          <thead>
            <tr>
              <th>Name</th>
              <th>Headline</th>
              <th>Experience</th>
              <th>Education</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let profile of profiles">
              <td>{{ profile.name }}</td>
              <td>{{ profile.headline || 'N/A' }}</td>
              <td>{{ profile.experience?.length || 0 }}</td>
              <td>{{ profile.education?.length || 0 }}</td>
              <td>{{ profile.last_updated | date:'short' }}</td>
              <td>
                <a [routerLink]="['/profiles', profile._id]" class="btn btn-primary btn-sm">View</a>
                <button (click)="deleteProfile(profile._id)" class="btn btn-danger btn-sm">Delete</button>
              </td>
            </tr>
          </tbody>
        </table>

        <div *ngIf="!loading && profiles.length === 0" class="no-data">
          No profiles found
        </div>

        <div class="pagination" *ngIf="profiles.length > 0">
          <button (click)="previousPage()" [disabled]="currentPage === 0" class="btn btn-secondary">Previous</button>
          <span>Page {{ currentPage + 1 }}</span>
          <button (click)="nextPage()" [disabled]="profiles.length < pageSize" class="btn btn-secondary">Next</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .search-input {
      margin-bottom: 20px;
    }
    .btn-sm {
      padding: 6px 12px;
      font-size: 12px;
      margin-right: 5px;
    }
    .pagination {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 20px;
      margin-top: 20px;
    }
    .no-data {
      text-align: center;
      padding: 40px;
      color: #666;
    }
  `]
})
export class ProfilesComponent implements OnInit {
  profiles: Profile[] = [];
  loading = true;
  error = '';
  searchQuery = '';
  currentPage = 0;
  pageSize = 20;

  constructor(private apiService: ApiService) {}

  ngOnInit() {
    this.loadProfiles();
  }

  loadProfiles() {
    this.loading = true;
    this.error = '';
    
    this.apiService.getProfiles(this.currentPage * this.pageSize, this.pageSize, this.searchQuery).subscribe({
      next: (data) => {
        this.profiles = data;
        this.loading = false;
      },
      error: (err) => {
        this.error = 'Failed to load profiles';
        this.loading = false;
        console.error(err);
      }
    });
  }

  onSearch() {
    this.currentPage = 0;
    this.loadProfiles();
  }

  nextPage() {
    this.currentPage++;
    this.loadProfiles();
  }

  previousPage() {
    if (this.currentPage > 0) {
      this.currentPage--;
      this.loadProfiles();
    }
  }

  deleteProfile(id: string) {
    if (confirm('Are you sure you want to delete this profile?')) {
      this.apiService.deleteProfile(id).subscribe({
        next: () => this.loadProfiles(),
        error: (err) => {
          this.error = 'Failed to delete profile';
          console.error(err);
        }
      });
    }
  }

  exportProfiles() {
    this.apiService.exportProfiles('grouped').subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `linkedin_profiles_${new Date().getTime()}.xlsx`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.error = 'Failed to export profiles';
        console.error(err);
      }
    });
  }
}
