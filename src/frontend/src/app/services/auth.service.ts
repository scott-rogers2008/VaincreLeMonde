import { Injectable } from '@angular/core';
import { HttpHeaders, HttpClient } from '@angular/common/http';
import { CookieService } from 'ngx-cookie-service';
import { Observable } from 'rxjs';


@Injectable()
export class AuthService {
  public headers: HttpHeaders = new HttpHeaders({
        'content-type': 'application/json',
        'X-CSRFToken': this.cookieservice.get('csrftoken')
      })  	

  constructor(private http: HttpClient, private cookieservice: CookieService ){}

  login(user:any): Observable <any> {
    let url: string = 'http://127.0.0.1:8000/api-login-user/';
		console.log(document.cookie);
		return this.http.post(url, user, {headers:
								 this.headers});
	}

  register(user: any): Observable <any>{
    let url: string = 'http://127.0.0.1:8000/api-register-user/';
    console.log('attempting to register');
    return this.http.post(url, JSON.stringify(user), {headers:
								this.headers});
	}

}


// http://www.pybloggers.com/2017/08/user-authentication-with-angular-4-and-flask/
