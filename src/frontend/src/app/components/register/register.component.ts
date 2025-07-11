import { Component, OnInit } from '@angular/core';
import { User } from '../../models/user';
import { AuthService } from '../../services/auth.service';
import { CookieService } from 'ngx-cookie-service';

@Component({
    selector: 'app-register',
    templateUrl: './register.component.html',
    styleUrls: ['./register.component.css'],
    standalone: false
})
export class RegisterComponent implements OnInit {

  constructor(public auth: AuthService, public cookieservice: CookieService) { }
  public user = new User('', '', null);

  ngOnInit() {
  }

  RegisterUser() {
    console.log("register user");
    this.auth.register(this.user).subscribe({
      next: (data) => {
        console.log(data);
        if (data.status == 200) {
          if (data.json()['status'] == 'success') {
            this.cookieservice.set('X-AuthToken', data.json()['token'], 0, '/');
          } else {
            console.log('Invalid Credentials');
          }
        }
        else {
          console.log("Some error occured")
        }
      }
    })

  }
    get diagnostic() { return JSON.stringify(this.user); }

}
