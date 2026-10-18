// src/frontend/src/app/services/study.service.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { CookieService } from 'ngx-cookie-service';

@Injectable({
  providedIn: 'root'
})
export class StudyService {
  private baseIngestUrl = 'http://127.0.0.1:8000/study/ingest/';
  private baseFetchUrl = 'http://127.0.0.1:8000/study/fetch/';

  constructor(private http: HttpClient, private cookieService: CookieService) { }

  public processTalkContent(talkUrl: string, targetLanguage: string): Observable<any> {
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'X-CSRFToken': this.cookieService.get('csrftoken') // Replays your functional security design
    });

    const payload = {
      url: talkUrl,
      language: targetLanguage
    };

    return this.http.post(this.baseIngestUrl, payload, { headers: headers });
  }
  
  public getStoredSentences(workId: number): Observable<any> {
    return this.http.get(`${this.baseFetchUrl}?work_id=${workId}`);
  }
}
