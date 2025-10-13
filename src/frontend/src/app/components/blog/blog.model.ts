
export interface User {
  username: string;
}

export interface BlogPost {
  id?: number;
  title: string;
  content: string;
  author: User;
  created_at?: Date;
  updated_at?: Date;
}
