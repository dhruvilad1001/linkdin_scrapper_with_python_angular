import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-scraper',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="container">
      <h2>LinkedIn Profile Scraper</h2>

      <div class="card">
        <h3>Single Profile</h3>
        <input 
          type="text" 
          [(ngModel)]="singleUrl" 
          placeholder="https://www.linkedin.com/in/username/"
          class="url-input"
        />
        <button 
          (click)="scrapeSingle()" 
          [disabled]="scraping || !singleUrl"
          class="btn btn-primary"
        >
          {{ scraping ? 'Scraping...' : 'Scrape Profile' }}
        </button>
      </div>

      <div class="card">
        <h3>Bulk Scraping</h3>
        <p>Enter one URL per line:</p>
        <textarea 
          [(ngModel)]="bulkUrls" 
          rows="10"
          placeholder="https://www.linkedin.com/in/user1/&#10;https://www.linkedin.com/in/user2/&#10;https://www.linkedin.com/in/user3/"
        ></textarea>
        <button 
          (click)="scrapeBulk()" 
          [disabled]="scraping || !bulkUrls"
          class="btn btn-primary"
        >
          {{ scraping ? 'Scraping...' : 'Scrape All Profiles' }}
        </button>
      </div>

      <div *ngIf="message" [class]="messageType === 'success' ? 'success' : 'error'">
        {{ message }}
      </div>

      <div class="card" *ngIf="results.length > 0">
        <h3>Scraping Results</h3>
        <table>
          <thead>
            <tr>
              <th>URL</th>
              <th>Status</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let result of results">
              <td>{{ result.url }}</td>
              <td>
                <span [class]="result.success ? 'badge-success' : 'badge-error'">
                  {{ result.success ? '✓ Success' : '✗ Failed' }}
                </span>
              </td>
              <td>{{ result.message }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .url-input {
      margin-bottom: 15px;
    }
    textarea {
      margin-bottom: 15px;
      font-family: monospace;
    }
    .badge-success {
      background: #d4edda;
      color: #155724;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
    .badge-error {
      background: #f8d7da;
      color: #721c24;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
    }
  `]
})
export class ScraperComponent {
  singleUrl = '';
  bulkUrls = '';
  scraping = false;
  message = '';
  messageType: 'success' | 'error' = 'success';
  results: any[] = [];

  constructor(private apiService: ApiService) {}

  scrapeSingle() {
    if (!this.singleUrl) return;

    this.scraping = true;
    this.message = '';
    this.results = [];

    this.apiService.scrapeProfile(this.singleUrl).subscribe({
      next: (response) => {
        this.scraping = false;
        this.message = response.message;
        this.messageType = 'success';
        this.results = [{ url: this.singleUrl, success: true, message: response.message }];
        this.singleUrl = '';
      },
      error: (err) => {
        this.scraping = false;
        this.message = err.error?.detail || 'Scraping failed';
        this.messageType = 'error';
        this.results = [{ url: this.singleUrl, success: false, message: this.message }];
      }
    });
  }

  scrapeBulk() {
    if (!this.bulkUrls) return;

    const urls = this.bulkUrls.split('\n')
      .map(url => url.trim())
      .filter(url => url.length > 0);

    if (urls.length === 0) return;

    this.scraping = true;
    this.message = '';
    this.results = [];

    this.apiService.bulkScrape(urls).subscribe({
      next: (response) => {
        this.scraping = false;
        this.message = response.message;
        this.messageType = 'success';
        this.bulkUrls = '';
      },
      error: (err) => {
        this.scraping = false;
        this.message = err.error?.detail || 'Bulk scraping failed';
        this.messageType = 'error';
      }
    });
  }
}
