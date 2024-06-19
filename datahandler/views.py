from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.status import *
from rest_framework import permissions
from django.db.models.functions import TruncMonth, TruncWeek
from django.db.models import Sum
from django.utils import timezone
from collections import defaultdict

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


class SentimentScoreView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        queryset = Data.objects.filter(date_interval__date__year=current_year)
        sentiment_data = queryset.annotate(month=TruncMonth('date_interval__date')).values(
            'symbol', 'month').annotate(uv=Sum('sentiment_score')).order_by('symbol', 'month')

        response_data = {}
        for item in sentiment_data:
            symbol = item['symbol']
            if symbol not in response_data:
                response_data[symbol] = []
            response_data[symbol].append(
                {"date": item['month'].strftime('%b'), "score": item['uv']})

        return Response(response_data, status=HTTP_200_OK)


class NetSpeculativeView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = GeneralData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.symbol
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            if week_data:
                week_data["score"] += entry.noncomm_net_position
            else:
                response_data[symbol].append(
                    {"date": entry.date_interval.date.strftime("%y-%m-%d"), "score": entry.noncomm_net_position})

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class CrowdingPositionsView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = GeneralData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.symbol
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            if week_data:
                week_data["long"] += entry.crowded_long_positions
                week_data["short"] += entry.crowded_short_positions
            else:
                response_data[symbol].append({
                    "date": entry.date_interval.date.strftime("%y-%m-%d"),
                    "long": entry.noncomm_long,
                    "short": entry.noncomm_short
                })

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)
