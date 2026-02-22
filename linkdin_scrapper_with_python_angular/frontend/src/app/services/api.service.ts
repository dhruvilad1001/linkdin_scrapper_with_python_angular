import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Profile {
  _id: string;
  name: string;
  url: string;
  headline?: string;
  about?: string;
  experience?: any[];
  education?: any[];
  projects?: any[];
  licenses?: any[];
  last_updated?: string;
}

export interface Stats {
  total_profiles: number;
  today_profiles: number;
  top_companies: any[];
  top_schools: any[];
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private apiUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) {}

  getProfiles(skip: number = 0, limit: number = 20, search?: string): Observable<Profile[]> {
    let params = new HttpParams()
      .set('skip', skip.toString())
      .set('limit', limit.toString());
    
    if (search) {
      params = params.set('search', search);
    }
    
    return this.http.get<Profile[]>(`${this.apiUrl}/profiles`, { params });
  }

  getProfile(id: string): Observable<Profile> {
    return this.http.get<Profile>(`${this.apiUrl}/profiles/${id}`);
  }

  scrapeProfile(url: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/scrape`, { url });
  }

  bulkScrape(urls: string[]): Observable<any> {
    return this.http.post(`${this.apiUrl}/scrape/bulk`, { urls });
  }

  getStats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.apiUrl}/stats`);
  }

  exportProfiles(format: string = 'grouped'): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/export`, 
      { format, filters: {} },
      { responseType: 'blob' }
    );
  }

  deleteProfile(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/profiles/${id}`);
  }
}
