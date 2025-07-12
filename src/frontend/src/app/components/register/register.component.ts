import { Component, OnInit } from '@angular/core';
import { User } from '../../models/user';
import { AuthService } from '../../services/auth.service';

@Component({
    selector: 'app-register',
    templateUrl: './register.component.html',
    styleUrls: ['./register.component.css'],
    standalone: false
})
export class RegisterComponent implements OnInit {

  constructor(public auth: AuthService) { }
  public user = new User('', '', null);

  ngOnInit() {
  }

  RegisterUser() {
    console.log("register user");
    this.auth.register(this.user).subscribe({
      next: (data) => {
        console.log(data);
            this.auth.updateData(data);
      },
      error: (err: any) => {
        console.log(err)
        if (err.error.username != undefined) {
          alert(err.error.username[0]);
        }
        else if (err.error.email != undefined) {
          alert(err.error.email)
        }
        else {
          alert(err);
        }
      }
    })

  }

  LogoutUser() {
    console.log("logout user");
    this.auth.logout()
  }

  refreshToken() {
    this.auth.refreshToken();
  }

    get diagnostic() { return JSON.stringify(this.user); }

}
