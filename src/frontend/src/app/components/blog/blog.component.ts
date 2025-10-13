import { Component, OnInit } from '@angular/core';
import { BlogService } from './blog.service';
import { BlogPost } from './blog.model';
import { SafeHtmlPipe } from './blog.pipe';

@Component({
  selector: 'app-blog',
  templateUrl: './blog.component.html',
  imports: [SafeHtmlPipe],
  styleUrl: './blog.component.css'
})

export class BlogComponent implements OnInit {
  posts: BlogPost[] = [];

  constructor(private blogService: BlogService) { }

  ngOnInit(): void {
    this.blogService.getPosts().subscribe(posts => {
      this.posts = posts;
    });
  }
}
