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
        <button (click)="exportProfiles()" class="btn btn-export">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
            <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
            <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"/>
          </svg>
          Export to Excel
        </button>
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
        <div *ngIf="loading" class="loading">
          <div class="spinner"></div>
          Loading profiles...
        </div>
        
        <div *ngIf="error" class="error">{{ error }}</div>

        <div class="table-container" *ngIf="!loading && profiles.length > 0">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Headline</th>
                <th>Experience</th>
                <th>Education</th>
                <th>Last Updated</th>
                <th class="actions-column">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let profile of profiles">
                <td class="name-cell">{{ profile.name }}</td>
                <td class="headline-cell">{{ profile.headline || 'N/A' }}</td>
                <td class="text-center">{{ profile.experience?.length || 0 }}</td>
                <td class="text-center">{{ profile.education?.length || 0 }}</td>
                <td>{{ profile.last_updated | date:'M/d/yy, h:mm a' }}</td>
                <td class="actions-cell">
                  <a [routerLink]="['/profiles', profile._id]" class="btn-icon btn-view" title="View Profile">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M16 8s-3-5.5-8-5.5S0 8 0 8s3 5.5 8 5.5S16 8 16 8zM1.173 8a13.133 13.133 0 0 1 1.66-2.043C4.12 4.668 5.88 3.5 8 3.5c2.12 0 3.879 1.168 5.168 2.457A13.133 13.133 0 0 1 14.828 8c-.058.087-.122.183-.195.288-.335.48-.83 1.12-1.465 1.755C11.879 11.332 10.119 12.5 8 12.5c-2.12 0-3.879-1.168-5.168-2.457A13.134 13.134 0 0 1 1.172 8z"/>
                      <path d="M8 5.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5zM4.5 8a3.5 3.5 0 1 1 7 0 3.5 3.5 0 0 1-7 0z"/>
                    </svg>
                    View
                  </a>
                  <button (click)="deleteProfile(profile._id)" class="btn-icon btn-delete" title="Delete Profile">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                      <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6z"/>
                      <path fill-rule="evenodd" d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118zM2.5 3V2h11v1h-11z"/>
                    </svg>
                    Delete
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div *ngIf="!loading && profiles.length === 0" class="no-data">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
            <path d="M14 1a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1h12zM2 0a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V2a2 2 0 0 0-2-2H2z"/>
            <path d="M10.97 4.97a.75.75 0 0 1 1.071 1.05l-3.992 4.99a.75.75 0 0 1-1.08.02L4.324 8.384a.75.75 0 1 1 1.06-1.06l2.094 2.093 3.473-4.425a.235.235 0 0 1 .02-.022z"/>
          </svg>
          <p>No profiles found</p>
        </div>

        <div class="pagination" *ngIf="profiles.length > 0">
          <button (click)="previousPage()" [disabled]="currentPage === 0" class="btn btn-secondary">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M11.354 1.646a.5.5 0 0 1 0 .708L5.707 8l5.647 5.646a.5.5 0 0 1-.708.708l-6-6a.5.5 0 0 1 0-.708l6-6a.5.5 0 0 1 .708 0z"/>
            </svg>
            Previous
          </button>
          <span class="page-info">Page {{ currentPage + 1 }}</span>
          <button (click)="nextPage()" [disabled]="profiles.length < pageSize" class="btn btn-secondary">
            Next
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
              <path fill-rule="evenodd" d="M4.646 1.646a.5.5 0 0 1 .708 0l6 6a.5.5 0 0 1 0 .708l-6 6a.5.5 0 0 1-.708-.708L10.293 8 4.646 2.354a.5.5 0 0 1 0-.708z"/>
            </svg>
          </button>
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

    .btn-export {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #10a37f;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-export:hover {
      background: #0d8c6d;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(16, 163, 127, 0.3);
    }

    .btn-export svg {
      width: 18px;
      height: 18px;
    }

    .search-input {
      width: 100%;
      padding: 12px 16px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      font-size: 14px;
      transition: all 0.2s;
    }

    .search-input:focus {
      outline: none;
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }

    .table-container {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead {
      background: #f8f9fa;
      border-bottom: 2px solid #e0e0e0;
    }

    th {
      padding: 14px 16px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      color: #374151;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    td {
      padding: 14px 16px;
      border-bottom: 1px solid #f0f0f0;
      font-size: 14px;
      color: #1f2937;
    }

    tbody tr {
      transition: background-color 0.2s;
    }

    tbody tr:hover {
      background-color: #f9fafb;
    }

    .name-cell {
      font-weight: 500;
      color: #111827;
    }

    .headline-cell {
      max-width: 300px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #6b7280;
    }

    .text-center {
      text-align: center;
    }

    .actions-column {
      text-align: center;
      width: 180px;
    }

    .actions-cell {
      display: flex;
      gap: 8px;
      justify-content: center;
      align-items: center;
    }

    .btn-icon {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      border: none;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      text-decoration: none;
    }

    .btn-icon svg {
      width: 16px;
      height: 16px;
    }

    .btn-view {
      background: #2563eb;
      color: white;
    }

    .btn-view:hover {
      background: #1d4ed8;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
    }

    .btn-delete {
      background: #dc2626;
      color: white;
    }

    .btn-delete:hover {
      background: #b91c1c;
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(220, 38, 38, 0.3);
    }

    .loading {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      color: #6b7280;
      gap: 16px;
    }

    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #f3f4f6;
      border-top-color: #2563eb;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .error {
      padding: 16px;
      background: #fee2e2;
      color: #991b1b;
      border-radius: 8px;
      border-left: 4px solid #dc2626;
    }

    .no-data {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 60px 20px;
      color: #9ca3af;
      gap: 16px;
    }

    .no-data svg {
      opacity: 0.5;
    }

    .no-data p {
      font-size: 16px;
      font-weight: 500;
      margin: 0;
    }

    .pagination {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 16px;
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid #e5e7eb;
    }

    .pagination button {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 16px;
      background: white;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      color: #374151;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .pagination button:hover:not(:disabled) {
      background: #f9fafb;
      border-color: #9ca3af;
    }

    .pagination button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .pagination button svg {
      width: 14px;
      height: 14px;
    }

    .page-info {
      padding: 8px 16px;
      background: #f3f4f6;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 500;
      color: #374151;
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
