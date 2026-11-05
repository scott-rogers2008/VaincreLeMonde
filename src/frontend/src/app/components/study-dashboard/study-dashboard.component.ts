// src/frontend/src/app/components/study-dashboard/study-dashboard.component.ts
import { Component, OnInit } from '@angular/core';
import { StudyService } from '../../services/study.service';

interface SentenceItem { id: number; text: string; isCoreLovePrinciple?: boolean; }
interface DBQuizQuestion { id: number; topic: string; question: string; options: string[]; correctAnswer: string; rationale: string; verificationStatus: string; }
interface ExplorerFile { filename: string; work_id: number | null; displayTitle: string; absolutePath: string; }
interface ExplorerFolder { folder: string; files: ExplorerFile[]; }

@Component({
  selector: 'app-study-dashboard',
  standalone: false,
  templateUrl: './study-dashboard.component.html',
  styleUrls: ['./study-dashboard.component.css']
})
export class StudyDashboardComponent implements OnInit {
  // File Explorer Core State Arrays
  public fileSystemTree: ExplorerFolder[] = [];
  public selectedFile: ExplorerFile | null = null;
  public activeWorkId: number | null = null;

  // Workspace trackers
  public currentStep: 'explorer' | 'study' | 'quiz' = 'explorer';
  public studySentences: SentenceItem[] = [];
  public statusMessage: string = '';
  public isProcessing: boolean = false;

  // Quiz-specific orchestrations
  public liveQuizQuestions: DBQuizQuestion[] = [];
  public currentQuestion: DBQuizQuestion | null = null;
  public currentQuestionIndex: number = 0;
  public userResponse: string = '';
  public gradeResult: { score: number; rationale: string } | null = null;

  constructor(private studyService: StudyService) { }

  ngOnInit(): void {
    this.loadUniversalFileSystemTree();
  }

  public loadUniversalFileSystemTree() {
    this.isProcessing = true;
    this.statusMessage = 'Mapping material repository structures...';
    
    this.studyService.loadExplorerTree(0).subscribe({
      next: (res: any) => {
        this.isProcessing = false;
        this.statusMessage = '';
        this.fileSystemTree = res.tree || [];
      },
      error: (err: any) => {
        this.isProcessing = false;
        this.statusMessage = `❌ Explorer Fault: ${err.error?.error || err.message}`;
      }
    });
  }

  public selectDocumentFromExplorer(file: ExplorerFile) {
    if (!file.work_id) {
      alert(`⚠️ This file is present on disk but hasn't been parsed into the SQL sentence relational schemas yet. Please use the Study Loader tool first.`);
      return;
    }

    this.selectedFile = file;
    this.activeWorkId = file.work_id;
    this.isProcessing = true;
    this.statusMessage = 'Loading split-screen textual matrix parameters...';

    this.studyService.getStoredSentences(this.activeWorkId).subscribe({
      next: (fetchRes) => {
        this.isProcessing = false;
        this.studySentences = fetchRes.data || [];
        this.currentStep = 'study';
      },
      error: (err) => {
        this.isProcessing = false;
        this.statusMessage = `❌ Error: ${err.message}`;
      }
    });
  }

  public goToStep(step: 'explorer' | 'study' | 'quiz') {
    this.currentStep = step;
    if (step === 'quiz' && this.activeWorkId) {
      this.refreshQuizBankCollection();
    }
  }

  public toggleLovePrinciple(item: SentenceItem) {
    item.isCoreLovePrinciple = !item.isCoreLovePrinciple;
  }

  public refreshQuizBankCollection() {
    if (!this.activeWorkId) return;
    this.studyService.loadQuizBank(this.activeWorkId).subscribe({
      next: (res) => {
        this.liveQuizQuestions = res.data || [];
        this.currentQuestion = this.liveQuizQuestions.length > 0 ? this.liveQuizQuestions[this.currentQuestionIndex] : null;
      }
    });
  }

  public selectOptionDirectly(opt: string) { this.userResponse = opt; }

  public evaluateSelectedAnswer() {
    if (!this.currentQuestion || !this.userResponse) return;
    const isCorrect = this.userResponse.trim().charAt(0).toUpperCase() === this.currentQuestion.correctAnswer.trim().toUpperCase();
    this.gradeResult = { score: isCorrect ? 1.0 : 0.0, rationale: this.currentQuestion.rationale };
  }

  public advanceNextQuestion() {
    this.gradeResult = null;
    this.userResponse = '';
    if (this.liveQuizQuestions.length > 0) {
      this.currentQuestionIndex = (this.currentQuestionIndex + 1) % this.liveQuizQuestions.length;
      this.currentQuestion = this.liveQuizQuestions[this.currentQuestionIndex];
    }
  }
}
