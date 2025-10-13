import { BrowserModule } from '@angular/platform-browser';
import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { AppComponent } from './app.component';
import { AppRoutingModule } from './app.router';
import { AuthService } from './services/auth.service';

import { LoginComponent } from './components/login/login.component';
import { RegisterComponent } from './components/register/register.component';
import { LandingComponent } from './components/landing/landing.component';
import { DashboardComponent } from './components/dashboard/dashboard.component';
import { BlogComponent } from './components/blog/blog.component';
import { SafeHtmlPipe } from './components/blog/blog.pipe';

import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatTreeModule } from '@angular/material/tree';
import { CookieService } from 'ngx-cookie-service';

@NgModule({
  declarations: [
    AppComponent,
    LoginComponent,
    RegisterComponent,
    LandingComponent,
    DashboardComponent,
  ],
  imports: [
    BrowserModule,
    FormsModule,
    HttpClientModule,
    AppRoutingModule,
    MatToolbarModule,
    MatIconModule,
    MatTreeModule,
    BlogComponent,
  ],
  providers: [
    AuthService,
    CookieService,
  ],
  bootstrap: [AppComponent]
})

export class AppModule { }


/*
Take note of the AppModule within app.module.ts. This is used to bootstrap the Angular app.
The @NgModule decorator takes metadata that lets Angular know how to run the app.
Everything that we create in this tutorial will be added to this object.
 */
