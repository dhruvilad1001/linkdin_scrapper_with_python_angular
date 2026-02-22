import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <nav class="navbar">
      <div class="container">
        <h1>LinkedIn Profile Scraper</h1>
        <ul class="nav-links">
          <li><a routerLink="/dashboard" routerLinkActive="active">Dashboard</a></li>
          <li><a routerLink="/profiles" routerLinkActive="active">Profiles</a></li>
          <li><a routerLink="/scraper" routerLinkActive="active">Scraper</a></li>
          <li><a routerLink="/analytics" routerLinkActive="active">Analytics</a></li>
        </ul>
      </div>
    </nav>
    <router-outlet></router-outlet>
  `,
  styles: [`
    .navbar {
      background: #0a66c2;
      color: white;
      padding: 15px 0;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .navbar .container {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .navbar h1 {
      font-size: 24px;
      font-weight: 600;
    }
    .nav-links {
      display: flex;
      list-style: none;
      gap: 30px;
    }
    .nav-links a {
      color: white;
      text-decoration: none;
      padding: 8px 16px;
      border-radius: 4px;
      transition: background 0.3s;
    }
    .nav-links a:hover, .nav-links a.active {
      background: rgba(255,255,255,0.2);
    }
  `]
})
export class AppComponent {
  title = 'LinkedIn Profile Scraper';
}
