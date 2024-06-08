from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.status import *
from rest_framework import permissions

# serializers imports
from .serializer import *

# models imports
from .models import *

from rest_framework_simplejwt.views import TokenObtainPairView

# Create your views here.


class CustomTokenObtain(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class Register(APIView):
    def post(self, request, format=None):
        data = request.data
        print(data)
        # del temp_data['pin']
        u = UserSerializer(data=data)
        if u.is_valid():
            u_data = u.save()
            u_data.set_password(data["password"])
            u_data.save()
            return Response(UserSerializer(u_data).data)
        else:
            print(u.error_messages)
            return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)


class DataHandler(ModelViewSet):
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get"]
    serializer_class = DateSerializer

    def get_queryset(self):
        return [DateInterval.objects.latest('date')]


class TestSession(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        return Response(UserSerializer(user).data)
