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

# stripe
from drf_stripe.models import StripeUser, Subscription
from drf_stripe.views import CreateStripeCheckoutSession

# scripts
from .scraper.Sentiment import Sentiment


# helpers here

def get_tier_level(name):
    """
    This function assigns tier levels based on the string 'name'.

    Args:
        name: The string to check.

    Returns:
        1 if "basic" is found in the name (case-insensitive),
        2 if "standard" is found,
        3 if "premium" is found,
        0 otherwise.
    """
    name_lower = name.lower()
    if "basic" in name_lower:
        return 1
    elif "standard" in name_lower:
        return 2
    elif "premium" in name_lower:
        return 3
    else:
        return 0


def is_subscription_valid(subscription):
    """
    This function checks if a subscription's period_end is still in the future.

    Args:
        subscription: The subscription object to check.

    Returns:
        True if the period_end is in the future, False otherwise.
    """
    now = timezone.now()
    return subscription.period_end > now


def is_subscription_canceled(subscription):
    if subscription.ended_at:
        if subscription.ended_at <= timezone.now():
            return True
        else:
            return True
    else:
        return False


def get_valid_and_tier(user):
    s_user = StripeUser.objects.filter(user=user).first()
    tier = 0
    valid = False
    if not s_user:
        valid = False
    else:
        subscriptions = Subscription.objects.filter(
            stripe_user=s_user).order_by("-period_start")
        if len(subscriptions) == 0:
            valid = False
        else:
            sub = subscriptions[0]
            time_valid_sub = is_subscription_valid(sub)
            cancel_valid_sub = is_subscription_canceled(sub)
            valid = time_valid_sub and (not cancel_valid_sub)
            if valid:
                item = s_user.subscription_items.filter(
                    subscription=sub).first()
                price_item = item.price
                product_item = price_item.product
                tier = get_tier_level(product_item.name)
    print(f"{user.username} | {valid} | {tier}")
    return valid, tier, s_user


def validate_user(s_user, tier, isvalid, user, requiredTier):
    if user.is_superuser:
        return True
    elif not isvalid:
        return False
    else:
        if tier >= requiredTier:
            return True
        else:
            return False


# Create your views here.


class CustomTokenObtain(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer


class CustomCheckout(CreateStripeCheckoutSession):
    """
    Provides session for using Stripe hosted Checkout page.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CustomCheckoutSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response({'session_id': serializer.validated_data['session_id']}, status=HTTP_200_OK)


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
    permission_classes = [permissions.IsAdminUser]
    http_method_names = ["get"]
    serializer_class = DateSerializer

    def get_queryset(self):
        return [DateInterval.objects.latest('date')]


class TestSession(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        data = UserSerializer(user).data
        valid, tier, stripe_user = get_valid_and_tier(user)
        data["isValidSub"] = valid
        data["tier"] = tier
        return Response(data)


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
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            quote_currency = entry.pair.split("/")[-1]
            base_currency = entry.pair.split("/")[0]
            if quote_currency == "USD":
                pair_long = entry.base_long
                pair_short = entry.base_short
                pair_net_position = entry.base_net_position
            elif base_currency == "USD":
                pair_long = entry.quote_short
                pair_short = entry.quote_long
                pair_net_position = -entry.quote_net_position
            else:
                pair_long = entry.base_long
                pair_short = entry.base_short
                pair_net_position = entry.base_net_position

            score = pair_net_position

            if week_data:
                week_data["score"] += score
            else:
                response_data[symbol].append(
                    {"date": entry.date_interval.date.strftime("%y-%m-%d"), "score": score})

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class CrowdingPositionsView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            if week_data:
                week_data["long"] += entry.pair_long
                week_data["short"] += entry.pair_short
            else:
                response_data[symbol].append({
                    "date": entry.date_interval.date.strftime("%y-%m-%d"),
                    "long": entry.pair_long,
                    "short": entry.pair_short
                })

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class NetSpeculativeCommView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            quote_currency = entry.pair.split("/")[-1]
            base_currency = entry.pair.split("/")[0]
            if quote_currency == "USD":
                pair_long = entry.base_comm_long
                pair_short = entry.base_comm_short
                pair_net_position = entry.base_comm_net_position
            elif base_currency == "USD":
                pair_long = entry.quote_comm_short
                pair_short = entry.quote_comm_long
                pair_net_position = -entry.quote_comm_net_position
            else:
                pair_long = entry.base_comm_long
                pair_short = entry.base_comm_short
                pair_net_position = entry.base_comm_net_position

            score = pair_net_position

            if week_data:
                week_data["score"] += score
            else:
                response_data[symbol].append(
                    {"date": entry.date_interval.date.strftime("%y-%m-%d"), "score": score})

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class CrowdingPositionsCommView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year)

        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            week_data = next(
                (item for item in response_data[symbol] if item["date"] == week_start_str), None)

            quote_currency = entry.pair.split("/")[-1]
            base_currency = entry.pair.split("/")[0]
            if quote_currency == "USD":
                pair_long = entry.base_comm_long
                pair_short = entry.base_comm_short
                pair_net_position = entry.base_comm_net_position
            elif base_currency == "USD":
                pair_long = entry.quote_comm_short
                pair_short = entry.quote_comm_long
                pair_net_position = -entry.quote_comm_net_position
            else:
                pair_long = entry.base_comm_long
                pair_short = entry.base_comm_short
                pair_net_position = entry.base_comm_net_position

            if week_data:
                week_data["long"] += pair_long
                week_data["short"] += pair_short
            else:
                response_data[symbol].append({
                    "date": entry.date_interval.date.strftime("%y-%m-%d"),
                    "long": pair_long,
                    "short": pair_short
                })

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class HomePairsView(ModelViewSet):
    permission_classes = [permissions.AllowAny]
    http_method_names = ['get']
    serializer_class = HomeDateSerializer

    def get_queryset(self):
        print("here")
        return [DateInterval.objects.latest('date')]


# Sentiment page
class SentimentData(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        valid, tier, s_user = get_valid_and_tier(user)
        validation_res = validate_user(s_user, tier, valid, user, 2)
        if not validation_res:
            return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
        else:
            s_handler = Sentiment()
            data = s_handler.execute()
            return Response(data, status=HTTP_200_OK)


class ChangeData(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        valid, tier, s_user = get_valid_and_tier(user)
        validation_res = validate_user(s_user, tier, valid, user, 3)
        if not validation_res:
            return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
        else:
            date_interval = DateInterval.objects.latest('date')
            data = HomeDateAllSerializer(date_interval).data
            return Response(data, status=HTTP_200_OK)


class ScannerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        valid, tier, s_user = get_valid_and_tier(user)
        validation_res = validate_user(s_user, tier, valid, user, 1)
        if not validation_res:
            return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
        else:
            date_interval = DateInterval.objects.latest('date')
            data = ScannerDateSerializer(date_interval).data
            return Response(data, status=HTTP_200_OK)

# User views


class UserDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            try:
                user_details = UserDetails.objects.get(user=request.user)
            except:
                user_details = UserDetails.objects.create(user=request.user)
                user_details.save()
            serializer = UserDetailsSerializer(user_details)
            return Response(serializer.data, status=HTTP_200_OK)
        except UserDetails.DoesNotExist:
            return Response({'error': 'User details not found'}, status=HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            user_details = UserDetails.objects.get(user=request.user)
            serializer = UserDetailsSerializer(
                user_details, data=request.data, partial=True)
        except UserDetails.DoesNotExist:
            serializer = UserDetailsSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        self.object = request.user
        serializer = PasswordChangeSerializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=HTTP_400_BAD_REQUEST)

            # Set new password
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            return Response({"detail": "Password updated successfully."}, status=HTTP_200_OK)

        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class UserImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user_image = UserImage.objects.get(user=request.user)
            serializer = UserImageSerializer(user_image)
            return Response(serializer.data, status=HTTP_200_OK)
        except UserImage.DoesNotExist:
            return Response({'error': 'Profile picture not found'}, status=HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            user_image = UserImage.objects.get(user=request.user)
            serializer = UserImageSerializer(
                user_image, data=request.data, partial=True)
        except UserImage.DoesNotExist:
            serializer = UserImageSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
