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
  private baseExplorerUrl = 'http://127.0.0.1:8000/study/explorer/list/';

  constructor(private http: HttpClient, private cookieService: CookieService) { }

  private getAuthHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Content-Type': 'application/json',
      'X-CSRFToken': this.cookieService.get('csrftoken')
    });
  }

  public processTalkContent(talkUrl: string, targetLanguage: string, customFilename?: string): Observable<any> {
    const payload = {
      url: talkUrl,
      language: targetLanguage,
      filename: customFilename || ''
    };
    return this.http.post(this.baseIngestUrl, payload, { headers: this.getAuthHeaders() });
  }
  
  public getStoredSentences(workId: number): Observable<any> {
    return this.http.get(`${this.baseFetchUrl}?work_id=${workId}`);
  }

  public loadQuizBank(workId: number): Observable<any> {
    return this.http.get(`${this.baseFetchUrl}quiz/bank/?work_id=${workId}`);
  }

  public createQuizQuestion(questionPayload: any): Observable<any> {
    return this.http.post(`${this.baseFetchUrl}quiz/bank/`, questionPayload, { headers: this.getAuthHeaders() });
  }

  public deleteQuizQuestion(id: number): Observable<any> {
    return this.http.delete(`${this.baseFetchUrl}quiz/bank/?id=${id}`, { headers: this.getAuthHeaders() });
  }

  public loadExplorerTree(id: number): Observable<any> {
    return this.http.get(`${this.baseExplorerUrl}?id=${id}`, { headers: this.getAuthHeaders() });
  }
}