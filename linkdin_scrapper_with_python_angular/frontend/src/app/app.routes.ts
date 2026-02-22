import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { 
    path: 'dashboard', 
    loadComponent: () => import('./components/dashboard/dashboard.component').then(m => m.DashboardComponent)
  },
  { 
    path: 'profiles', 
    loadComponent: () => import('./components/profiles/profiles.component').then(m => m.ProfilesComponent)
  },
  { 
    path: 'profiles/:id', 
    loadComponent: () => import('./components/profile-detail/profile-detail.component').then(m => m.ProfileDetailComponent)
  },
  { 
    path: 'scraper', 
    loadComponent: () => import('./components/scraper/scraper.component').then(m => m.ScraperComponent)
  },
  { 
    path: 'analytics', 
    loadComponent: () => import('./components/analytics/analytics.component').then(m => m.AnalyticsComponent)
  }
];
