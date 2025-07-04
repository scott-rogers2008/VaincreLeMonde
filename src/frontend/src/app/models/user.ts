export class User {
  username: string;
  password: string;
  email: any;

	constructor(
		username: string,
		password: string,
		email?: any,
		){
    this.username = username;
    this.password = password;
    if (email) {
      this.email = email;
    }
	}
}
