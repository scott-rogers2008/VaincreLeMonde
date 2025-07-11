import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';
import { jwtDecode } from 'jwt-decode';

@Injectable()
export class UserService {

  // http options used for making API calls
  private httpOptions: any;

  // the actual JWT token
  public token: string;

  // the token expiration date
  public token_expires: Date;

  // the username of the logged in user
  public username: string;

  // error messages received from the login attempt
  public errors: any = [];

  public Data: any;

  constructor(private http: HttpClient, private cookieservice: CookieService) {
    this.token = '';
    this.token_expires = new Date(0);
    this.username = '';
    this.httpOptions = {
      headers: new HttpHeaders({ 'Content-Type': 'application/json' })
    };
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

  // Refreshes the JWT token, to extend the time the user is logged in
  public refreshToken() {
    this.http.post('http://127.0.0.1:8000/api-token-refresh/', JSON.stringify({ token: this.token }), this.httpOptions).subscribe(
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

  public logout() {
    this.token = '';
    this.updateData(this.token);
    this.cookieservice.delete('X-AuthToken', '/');
  }

  private updateData(token: string) {
    this.token = token;
    this.errors = [];

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
