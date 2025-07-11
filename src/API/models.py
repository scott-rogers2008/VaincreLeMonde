from operator import truediv
from tkinter import SE
from turtle import update
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class BlogPost(models.Model):
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=256)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.author.username + ": " + self.title + ": " + str(self.updated_at)

    class Meta:
        ordering = ['id', 'author', 'updated_at']

class Responce(models.Model):
    id = models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")
    toBlog = models.BooleanField()
    blogPost = models.ForeignKey(BlogPost, on_delete=models.CASCADE, blank=True, null=True)
    bResponce = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='children')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        reference :str = ""
        if self.toBlog:
            reference = "[" + self.blogPost.author.username + ":" + self.blogPost.title + "]"
        else:
            reference = "[" + self.bResponce.author.username + ":" + str(self.bResponce.updated_at) + "]"
        return self.author.username + ": " + reference + ": " + str(self.updated_at)

    class Meta:
        ordering = ['id', 'author', 'updated_at']

