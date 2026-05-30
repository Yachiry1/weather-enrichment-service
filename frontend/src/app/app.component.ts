import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { CityApiService } from './city-api.service';
import { City } from './city.model';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent implements OnInit {
  cities: City[] = [];
  cityName = '';
  loading = false;
  saving = false;
  error = '';

  constructor(private readonly cityApi: CityApiService) {}

  ngOnInit(): void {
    this.loadCities();
  }

  loadCities(): void {
    this.loading = true;
    this.error = '';

    this.cityApi.getCities().subscribe({
      next: (cities) => {
        this.cities = cities;
        this.loading = false;
      },
      error: () => {
        this.error = 'Could not load cities';
        this.loading = false;
      },
    });
  }

  addCity(): void {
    const name = this.cityName.trim();
    if (!name) {
      return;
    }

    this.saving = true;
    this.error = '';

    this.cityApi.createCity(name).subscribe({
      next: () => {
        this.cityName = '';
        this.saving = false;
        this.loadCities();
      },
      error: (error) => {
        this.error = this.getErrorMessage(error);
        this.saving = false;
        this.loadCities();
      },
    });
  }

  refreshCity(city: City): void {
    this.error = '';

    this.cityApi.refreshCity(city.id).subscribe({
      next: () => {
        this.loadCities();
      },
      error: () => {
        this.error = `Could not refresh ${city.name}`;
      },
    });
  }

  private getErrorMessage(error: any): string {
    const detail = error?.error?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (typeof detail?.message === 'string') {
      return detail.message;
    }

    return 'Request failed. Try again later.';
  }
}
