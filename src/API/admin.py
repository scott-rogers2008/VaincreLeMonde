from django.contrib import admin
from django.contrib.auth.models import User
from .models import BlogPost, Responce

# Register your models here.
admin.site.register(BlogPost)
admin.site.register(Responce)