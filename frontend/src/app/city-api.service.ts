import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { City } from './city.model';

@Injectable({ providedIn: 'root' })
export class CityApiService {
  private readonly apiUrl = 'http://localhost:8000';

  constructor(private readonly http: HttpClient) {}

  getCities(): Observable<City[]> {
    return this.http.get<City[]>(`${this.apiUrl}/cities`);
  }

  createCity(name: string): Observable<City> {
    return this.http.post<City>(`${this.apiUrl}/cities`, { name });
  }

  refreshCity(cityId: number): Observable<City> {
    return this.http.post<City>(`${this.apiUrl}/cities/${cityId}/refresh`, {});
  }
}
