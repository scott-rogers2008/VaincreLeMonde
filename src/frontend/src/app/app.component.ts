import { Component, OnInit } from '@angular/core';
import { AuthService } from './services/auth.service';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css'],
    standalone: false
})
export class AppComponent implements OnInit {
  title = 'frontend';
  public user: any;

  constructor(public _userService: AuthService) { }

  ngOnInit() {
    this._userService.getCookie();
  }

}

