import { Injectable } from '@angular/core';
import { HttpHeaders, HttpClient } from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';
import { Observable } from 'rxjs';
import { jwtDecode } from 'jwt-decode';


@Injectable()
export class AuthService {

  // the actual JWT token
  public token: string;

  // the token expiration date
  public token_expires: Date;

  // the username of the logged in user
  public username: string;

  // error messages received from the login attempt
  public errors: any = [];
  public Data: any;

  public headers: HttpHeaders = new HttpHeaders({
        'content-type': 'application/json',
        'X-CSRFToken': this.cookieservice.get('csrftoken')
      })  	

  constructor(private http: HttpClient, private cookieservice: CookieService) {
    this.token = '';
    this.token_expires = new Date(0);
    this.username = '';
  }

  login(user:any): Observable <any> {
    let url: string = 'http://127.0.0.1:8000/api-login-user/';
		console.log(document.cookie);
		return this.http.post(url, user, {headers:
								 this.headers});
  }

  logout() {
    this.token = '';
    this.token_expires = new Date(0);
    this.username = '';
    this.cookieservice.set('X-AuthToken', this.token, 0, '/');
  }

  register(user: any): Observable <any>{
    let url: string = 'http://127.0.0.1:8000/api-register-user/';
    console.log('attempting to register');
    let ret: Observable<any> = this.http.post(url, user, {headers: this.headers });
    console.log(ret);
    return ret;
  }

  // Refreshes the JWT token, to extend the time the user is logged in
  public refreshToken() {
    this.http.post('http://127.0.0.1:8000/api-token-refresh/', JSON.stringify({ token: this.token }), { headers: this.headers }).subscribe(
      (data: any) => {
        this.Data = data
        const index = Math.floor(Math.random() * this.Data.length);
        this.updateData(data['token']);
      },
      (err: any) => {
        this.errors = err['error'];
      }
    );
  }

  public getCookie() {
    const cookieExists: boolean = this.cookieservice.check('X-AuthToken');
    if (cookieExists) {
      this.token = this.cookieservice.get('X-AuthToken');
      if (this.token != '') {
        const exp_date = jwtDecode(this.token).exp ?? this.token_expires.getDate();
        if (exp_date < Date.now() / 1000) {
          this.token = '';
        }
      }

      this.updateData(this.token);
    }
  }

  updateData(token: string) {
    this.token = token;
    this.errors = [];

    console.log("updateData");
    console.log(token);
    // decode the token to read the username and expiration timestamp
    if (token == '') {
      const token_parts = '';
      const token_decoded = '';
      this.token_expires = new Date(0);
      this.username = '';
    } else {
      const token_parts = this.token.split(/\./);
      const token_decoded = JSON.parse(window.atob(token_parts[1]));
      this.token_expires = new Date(token_decoded.exp * 1000);
      this.username = token_decoded.username;
    }
    this.cookieservice.set('X-AuthToken', this.token, 0, '/');
  }

}


// http://www.pybloggers.com/2017/08/user-authentication-with-angular-4-and-flask/
