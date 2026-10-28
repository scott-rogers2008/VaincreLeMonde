// src/frontend/src/app/components/study-dashboard/study-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { StudyService } from '../../services/study.service';

interface SentenceItem {
  id: number;
  text: string;
  isCoreLovePrinciple?: boolean;
}

@Component({
  selector: 'app-study-dashboard',
  standalone: false, // Remains false to seamlessly support your AppModule layout configuration
  templateUrl: './study-dashboard.component.html',
  styleUrls: ['./study-dashboard.component.css']
})
export class StudyDashboardComponent implements OnInit {
  public targetUrl: string = 'https://churchofjesuschrist.org';
  public chosenLanguage: string = 'English';
  public statusMessage: string = '';
  public isProcessing: boolean = false;
  
  // Dynamic application screen tracker
  public currentStep: 'ingest' | 'study' = 'study'; 
  
  public languageTracks: string[] = ['English', 'Spanish', 'French', 'German', 'Korean'];
  public studySentences: SentenceItem[] = [];

  constructor(private studyService: StudyService) { }

  ngOnInit(): void { }

  public goToStep(step: 'ingest' | 'study') {
    this.currentStep = step;
    if (step === 'study') {
      this.statusMessage = '';
    }
  }

  public toggleLovePrinciple(item: SentenceItem) {
    item.isCoreLovePrinciple = !item.isCoreLovePrinciple;
  }

  public triggerContentIngestion() {
    this.isProcessing = true;
    this.statusMessage = `Initializing pipeline. Fetching and indexing discourse elements in ${this.chosenLanguage}...`;
    this.studySentences = [];

    this.studyService.processTalkContent(this.targetUrl, this.chosenLanguage).subscribe({
      next: (response) => {
        this.statusMessage = `✨ Ingestion complete! Core curriculum loaded into semantic graph frameworks. Ready to analyze theme definitions and study Christ-like love.`;
        
        // Extract the work tracking ID returned by your database registry commit pass
        const targetWorkId = response.work_id || 8; 

        // Query your database retrieval view to pull down sentences automatically
        this.studyService.getStoredSentences(targetWorkId).subscribe({
          next: (fetchRes) => {
            this.isProcessing = false;
            this.studySentences = fetchRes.data || [];
            
            // Swap step views smoothly once the server data has arrived
            setTimeout(() => {
              this.currentStep = 'study';
            }, 1200);
          },
          error: (fetchErr) => {
            this.isProcessing = false;
            this.statusMessage = `⚠️ Text parsing logged successfully, but retrieval check failed: ${fetchErr.error?.error || fetchErr.message}`;
          }
        });
      },
      error: (err) => {
        this.isProcessing = false;
        this.statusMessage = `❌ Pipeline Execution Fault: ${err.error?.error || err.message}`;
      }
    });
  }
}
