import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../services/auth.service';
import { User } from '../../models/user';

@Component({
    selector: 'login',
    templateUrl: './login.component.html',
    styleUrls: ['./login.component.css'],
    standalone: false
})

export class LoginComponent implements OnInit {
  constructor(public auth: AuthService){}
  public user: any = new User('', '', null);

  ngOnInit(): void{
  }
  
  LoginUser(){
  	console.log("login user");
    this.auth.login(this.user).subscribe({
      next: (data) => {
        console.log(data);
        if (data.status == 'success') {
            console.log('login successful...')
            this.auth.updateData(data.token);
        }
        else {
          console.log("Some error occured data.status = " + data.status)
          alert(data.error)
        }
      },
      error: (err: any) => {
        console.log("Some error occured = " + err)
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

/* In Angular 4, we define a component by wrapping a config object with an @Component
 decorator. We can share code between packages by importing the classes we need; and, 
 in this case, we import Component from the @angular/core package. The LoginComponent 
 class is the component’s controller, and we use the export operator to make it available
 for other classes to import. */
