// src/frontend/src/app/app.module.ts
import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common'; 
import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './app.router';
import { AuthService } from './services/auth.service';
import { StudyService } from './services/study.service'; 

import { LoginComponent } from './components/login/login.component';
import { RegisterComponent } from './components/register/register.component';
import { LandingComponent } from './components/landing/landing.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { StudyDashboardComponent } from './components/study-dashboard/study-dashboard.component'; 

import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatTreeModule } from '@angular/material/tree';
import { CookieService } from 'ngx-cookie-service';
import { BlogComponent } from './components/blog/blog.component';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    RegisterComponent,
    LandingComponent,
    DashboardComponent,
    StudyDashboardComponent 
  ],
  imports: [
    BrowserModule,
    CommonModule, 
    FormsModule,  
    AppRoutingModule,
    MatToolbarModule, 
    MatIconModule,
    MatTreeModule,
    BlogComponent, 
  ],
  providers: [
    AuthService,
    StudyService,
    CookieService,
    provideHttpClient(withInterceptorsFromDi())
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
