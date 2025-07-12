from django.contrib.auth import get_user_model
from rest_framework import serializers

UserModel = get_user_model()

class UserSerializer(serializers.HyperlinkedModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = UserModel
        fields = ( 'id', 'username', 'email', 'password')

    def create(self, validated_data):
        email = ''
        if 'email' in validated_data:
            email = validated_data['email']

        user = UserModel.objects.create_user(
            email=email,
            username=validated_data['username'],
            password=validated_data['password'],
        )
        user.is_active = True
        return user

class UserRegisterSerializer(serializers.ModelSerializer):
        password2 = serializers.CharField(style={'input_type': 'password'}, write_only=True)

        class Meta:
            model = UserModel
            fields = ['username', 'email', 'password', 'password2']
            extra_kwargs = {
                'password': {'write_only': True}
            }

        def validate(self, data):
            if data['password'] != data['password2']:
                raise serializers.ValidationError({"password": "Passwords do not match."})
            return data

        def create(self, validated_data):
            email = ''
            if 'email' in validated_data:
                email = validated_data['email']
            user = User.objects.create_user(
                username=validated_data['username'],
                email=email,
                password=validated_data['password']
            )
            return user