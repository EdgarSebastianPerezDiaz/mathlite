import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AnalyzeResponse } from './models';
import { environment } from './environment';

@Injectable({ providedIn: 'root' })
export class MathliteApiService {
  private readonly endpoint = `${environment.apiUrl}/api/analyze`;

  constructor(private readonly http: HttpClient) {}

  analyze(source: string): Observable<AnalyzeResponse> {
    return this.http.post<AnalyzeResponse>(this.endpoint, { source });
  }
}
