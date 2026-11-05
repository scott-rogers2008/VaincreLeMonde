// src/frontend/src/app/components/study-loader/study-loader.component.ts
import { Component, OnInit } from '@angular/core';
import { StudyService } from '../../services/study.service';

@Component({
  selector: 'app-study-loader',
  standalone: false,
  templateUrl: './study-loader.component.html',
  styleUrls: ['./study-loader.component.css']
})
export class StudyLoaderComponent implements OnInit {
  public targetUrl: string = 'https://churchofjesuschrist.org';
  public customTitle: string = 'soul_sculpting_analysis.md';
  public chosenLanguage: string = 'English';
  
  public statusMessage: string = '';
  public isProcessing: boolean = false;
  public languageTracks: string[] = ['English', 'Spanish', 'French', 'German', 'Korean'];

  constructor(private studyService: StudyService) { }

  ngOnInit(): void { }

  public triggerContentIngestion() {
    if (!this.targetUrl.trim()) {
      alert('Please specify a valid discourse source target address URL.');
      return;
    }

    this.isProcessing = true;
    this.statusMessage = `⚡ Transmitting payload to ingestion network. Processing text frames into matrix...`;

    this.studyService.processTalkContent(this.targetUrl, this.chosenLanguage, this.customTitle).subscribe({
      next: (response) => {
        this.isProcessing = false;
        this.statusMessage = `✨ Success! Resource indexed. Assigned ID: ${response.work_id}. File saved to disk storage as: ${response.title}`;
      },
      error: (err) => {
        this.isProcessing = false;
        this.statusMessage = `❌ Pipeline Error: ${err.error?.error || err.message}`;
      }
    });
  }
}
