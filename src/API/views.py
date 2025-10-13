from django.shortcuts import render, HttpResponse
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.http.response import JsonResponse  

from rest_framework import viewsets, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework_jwt.settings import api_settings
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
import jwt
import json

from .serializers import UserSerializer, BlogPostSerializer
from backend.settings import SECRET_KEY
from .models import BlogPost

jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER


class CreateUserView(CreateAPIView):
    model = get_user_model()
    permission_classes = [
        permissions.AllowAny # Or anon users can't register
    ]
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        print("create user view")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            self.perform_create(user)
            headers = self.get_success_headers(serializer.data)
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)
            print("--Create User View:  successful")
            return Response(
                token,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        else:
            print("--Create User View:  fialed", serializer.errors)
            return JsonResponse(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )


class LoginUserView(APIView):

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)
        if user:
            payload = jwt_payload_handler(user)
            token = {
                'token': jwt.encode(payload, SECRET_KEY),
                'status': 'success'
                }            
            return Response(token)
        else:
            return Response(
              {'error': 'Invalid credentials',
              'status': 'failed'},
            )

class BlogPostViewSet(viewsets.ModelViewSet):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]