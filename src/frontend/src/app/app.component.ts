import { Component, OnInit } from '@angular/core';
import { UserService } from './user.service';

@Component({
    selector: 'app-root',
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css'],
    standalone: false
})
export class AppComponent implements OnInit {
  title = 'frontend';
  public user: any;

  constructor(public _userService: UserService) { }

  ngOnInit() {
    this._userService.getCookie();
  }

}

