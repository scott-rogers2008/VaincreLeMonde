import { Component, OnInit } from '@angular/core';

@Component({
    selector: 'app-landing',
    templateUrl: './landing.component.html',
    styleUrls: ['./landing.component.css'],
    standalone: false
})
export class LandingComponent implements OnInit {

  constructor() { }

  ngOnInit() {
  	console.log('landing page')
  }


}
