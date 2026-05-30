export type WeatherStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface City {
  id: number;
  name: string;
  latitude: number | null;
  longitude: number | null;
  temperature: number | null;
  humidity: number | null;
  description: string | null;
  status: WeatherStatus;
  error: string | null;
  task_id: string | null;
  last_refreshed_at: string | null;
  created_at: string;
  updated_at: string;
}
