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
from django.core.mail import send_mail
from django.conf import settings
from urllib.parse import urlparse
# serializers imports
from .serializer import *
import datetime

# models imports
from .models import *

from rest_framework_simplejwt.views import TokenObtainPairView

# stripe
from drf_stripe.models import StripeUser, Subscription
from drf_stripe.views import CreateStripeCheckoutSession
from drf_stripe.stripe_api.api import stripe_api as stripe

# scripts
from .scraper.Sentiment import Sentiment
from .helper import update_user_subscription, get_valid_and_tier, get_tier_level, is_subscription_canceled, is_subscription_valid, validate_user


# helpers here


# Create your views here.

# subscription handling views
class SubscriptionHandler(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        u = request.user
        valid, tier, s_user, item = get_valid_and_tier(u)
        cancel_at_end = item.subscription.cancel_at_period_end
        cancel_date = item.subscription.cancel_at
        return Response({"subscriptionId": item.subscription.subscription_id, "cancel_at_end": cancel_at_end, "cancel_date": cancel_date, "show": cancel_date >= timezone.now() if cancel_date else False}, status=HTTP_200_OK)

    def post(self, request):
        u = request.user
        s_id = request.data.get("sid", None)
        action = request.data.get("action", None)
        p_id = request.data.get("pid", None)
        valid, tier, s_user, item = get_valid_and_tier(u)
        if s_id:
            if p_id:
                if not valid:
                    return Response({"message": "No valid subscription"})
                else:

                    if action == "upgrade":
                        if p_id == item.price.price_id:
                            return Response({"message": "Cannot update an already existing subscription"}, status=HTTP_400_BAD_REQUEST)
                        else:
                            try:
                                res = stripe.Subscription.modify(item.subscription.subscription_id, items=[
                                    {"id": item.sub_item_id, "price": p_id}], payment_behavior="error_if_incomplete", proration_behavior="always_invoice")
                                update_user_subscription(s_user.customer_id)
                                return Response({"message": "Subscription upgraded"}, status=HTTP_200_OK)
                            except Exception as e:
                                print(str(e))
                                return Response({"message": "Failed upgrade"}, status=HTTP_400_BAD_REQUEST)

                    elif action == "cancel":
                        try:
                            if (item.subscription.cancel_at_period_end):
                                return Response({"message": "Already canceled"}, status=HTTP_400_BAD_REQUEST)
                            """ res = stripe.Subscription.modify(
                                item.subscription.subscription_id) """
                            res = stripe.Subscription.cancel(item.subscription.subscription_id)
                            #update_user_subscription(s_user.customer_id)
                            u.delete()
                            return Response({"message": "Subscription canceled"}, status=HTTP_200_OK)
                        except Exception as e:
                            print(str(e))
                            return Response({"message": "Failed Cancel"}, status=HTTP_400_BAD_REQUEST)
                    else:
                        return Response({"message": "Action not recognized"}, status=HTTP_400_BAD_REQUEST)
            else:
                return Response({"message": "Price ID not supplied"}, status=HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "Subscription ID not supplied"}, status=HTTP_400_BAD_REQUEST)

# custom permission
class IsSuperuserOrMember(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow non-authenticated users to read-only requests (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow superusers or members to perform write operations
        return request.user and (request.user.is_superuser or request.user.is_member)
###


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
    permission_classes = [IsSuperuserOrMember]
    http_method_names = ["get"]
    serializer_class = DateSerializer

    def get_queryset(self):
        return [DateInterval.objects.latest('date')]


class TestSession(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        data = UserSerializer(user).data
        valid, tier, stripe_user, item = get_valid_and_tier(user)
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
            date_interval__date__year=current_year).order_by("date_interval__date")

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

            if entry.is_contract:
                pair_long = entry.base_long
                pair_short = entry.base_short
            else:
                pair_long = entry.base_long + entry.quote_long
                pair_short = entry.base_short + entry.quote_short

            score = pair_long - pair_short

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
            date_interval__date__year=current_year).order_by("date_interval__date")

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
                week_data["long"] += entry.base_long if entry.is_contract else entry.base_long + entry.quote_long
                week_data["short"] += entry.base_short if entry.is_contract else entry.base_short + entry.quote_short
            else:
                response_data[symbol].append({
                    "date": entry.date_interval.date.strftime("%y-%m-%d"),
                    "long": entry.base_long if entry.is_contract else entry.base_long + entry.quote_long,
                    "short": entry.base_short if entry.is_contract else entry.base_short + entry.quote_short
                })

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class NetSpeculativeCommView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year).order_by("date_interval__date")

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

            if entry.is_contract:
                pair_long = entry.base_comm_long
                pair_short = entry.base_comm_short
            else:
                pair_long = entry.base_comm_long + entry.quote_comm_long
                pair_short = entry.base_comm_short + entry.quote_comm_short

            score = pair_long - pair_short

            if week_data:
                week_data["score"] += score
            else:
                response_data[symbol].append(
                    {"date": entry.date_interval.date.strftime("%y-%m-%d"), "score": score})

        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)
    

def get_threshold_signal(interest):
    """
    Determines the signal based on the given interest value.

    Args:
        interest: The interest value.

    Returns:
        The signal corresponding to the interest value.
    """

    signal = None

    if interest >= 0 and interest <= 10:
        signal = "Neutral"
    elif interest > 10 and interest <= 30:
        signal = "Buy"
    elif interest > 30:
        signal = "Strong Buy"
    elif interest >= -10 and interest < 0:
        signal = "Neutral"
    elif interest < -10 and interest >= -30:
        signal = "Sell"
    elif interest < -30:
        signal = "Strong Sell"
    else:
        raise ValueError("Interest value is out of the expected range.")

    return signal

class NonCommSignalOverview(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year).order_by("-date_interval__date")
        current_year = data_entries[len(data_entries) - 1].date_interval.date.year
        start_of_year = datetime.datetime(current_year, 1, 1)

        # Calculate the end date for 52 weeks from the start of the year
        end_of_52_weeks = start_of_year + datetime.timedelta(weeks=52)

        data_entries = ProcessedData.objects.filter(
            date_interval__date__gte=start_of_year,
            date_interval__date__lte=end_of_52_weeks
        ).order_by("date_interval__date")
        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            """ if (len(response_data[symbol]) == 0): """
            response_data[symbol].append(
                        {"date": entry.date_interval.date.strftime("%y-%m-%d"), "change": entry.pair_pct_change, "signal" : get_threshold_signal(entry.pair_pct_change)})
            """ else:
                change_data = response_data[symbol][-1]["change"] + entry.pair_pct_change
                response_data[symbol].append(
                        {"date": entry.date_interval.date.strftime("%y-%m-%d"), "change": change_data, "signal" : get_threshold_signal(change_data)}) """
        for sym in response_data.keys():
            current_index = -1
            while True:
                if current_index < (-1 * len(response_data[sym])):
                    break
                else:
                    if current_index == -1:
                        current_index -= 1
                        continue
                    else:
                        response_data[sym][current_index]["change"] += response_data[sym][current_index + 1]["change"]
                        response_data[sym][current_index]["signal"] =  get_threshold_signal(response_data[sym][current_index]["change"])
                        current_index -= 1
        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)
    

class CommSignalOverview(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year).order_by("-date_interval__date")
        current_year = data_entries[len(data_entries) - 1].date_interval.date.year
        start_of_year = datetime.datetime(current_year, 1, 1)

        # Calculate the end date for 52 weeks from the start of the year
        end_of_52_weeks = start_of_year + datetime.timedelta(weeks=52)

        data_entries = ProcessedData.objects.filter(
            date_interval__date__gte=start_of_year,
            date_interval__date__lte=end_of_52_weeks
        ).order_by("date_interval__date")
        # Dictionary to hold aggregated data
        response_data = defaultdict(list)

        for entry in data_entries:
            symbol = entry.pair
            week_start_date = entry.date_interval.date - \
                timezone.timedelta(days=entry.date_interval.date.weekday())
            week_start_str = week_start_date.strftime('%Y-%U')

            # Find if the week already exists in response_data for this symbol
            """ if (len(response_data[symbol]) == 0): """
            response_data[symbol].append(
                        {"date": entry.date_interval.date.strftime("%y-%m-%d"), "change": entry.pair_comm_pct_change, "signal" : get_threshold_signal(entry.pair_comm_pct_change)})
            """ else:
                change_data = response_data[symbol][-1]["change"] + entry.pair_pct_change
                response_data[symbol].append(
                        {"date": entry.date_interval.date.strftime("%y-%m-%d"), "change": change_data, "signal" : get_threshold_signal(change_data)}) """
        """ for sym in response_data.keys():
            current_index = -1
            while True:
                if current_index < (-1 * len(response_data[sym])):
                    break
                else:
                    if current_index == -1:
                        current_index -= 1
                        continue
                    else:
                        response_data[sym][current_index]["change"] += response_data[sym][current_index + 1]["change"]
                        response_data[sym][current_index]["signal"] =  get_threshold_signal(response_data[sym][current_index]["change"])
                        current_index -= 1 """
        # Convert defaultdict to a regular dict
        response_data = dict(response_data)

        return Response(response_data, status=HTTP_200_OK)


class CrowdingPositionsCommView(APIView):
    def get(self, request):
        current_year = timezone.now().year
        data_entries = ProcessedData.objects.filter(
            date_interval__date__year=current_year).order_by("date_interval__date")

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
                week_data["long"] += entry.base_comm_long if entry.is_contract else entry.base_comm_long + \
                    entry.quote_comm_long
                week_data["short"] += entry.base_comm_short if entry.is_contract else entry.base_comm_short + \
                    entry.quote_comm_short
            else:
                response_data[symbol].append({
                    "date": entry.date_interval.date.strftime("%y-%m-%d"),
                    "long": entry.base_comm_long if entry.is_contract else entry.base_comm_long + entry.quote_comm_long,
                    "short": entry.base_comm_short if entry.is_contract else entry.base_comm_short + entry.quote_comm_short
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
        valid, tier, s_user, item = get_valid_and_tier(user)
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
        valid, tier, s_user, item = get_valid_and_tier(user)
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
        valid, tier, s_user, item = get_valid_and_tier(user)
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
    
class UpdateUsername(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        self.object = request.user
        newusername = request.data.get("newusername",None)

        if newusername:
            # Check old password
            if CustomUser.objects.filter(username=newusername).first():
                return Response({"message": "taken"}, status=HTTP_400_BAD_REQUEST)

            # Set new password
            self.object.username = newusername
            self.object.save()
            return Response({"detail": "Username updated successfully."}, status=HTTP_200_OK)

        return Response({"message": "username not supplied"}, status=HTTP_400_BAD_REQUEST)


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


class getLatestDataDate(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self,request):
        try:
            dt = DateInterval.objects.all().order_by("-date")[0]
            return Response({"date" : dt.date},status=HTTP_200_OK)
        except:
            return Response({}, status=HTTP_400_BAD_REQUEST)
        
class GetTeamMembers(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        users = CustomUser.objects.filter(is_superuser=False,is_member=True)
        return Response(HomeUserSerializer(users, many=True).data, status=HTTP_200_OK)

# admin user management



class ArticleViewSet(ModelViewSet):
    
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsSuperuserOrMember]

    def get_queryset(self):
        # Get the limit from the query parameters
        limit = self.request.query_params.get('limit', None)
        
        try:
            limit = int(limit)
            return Article.objects.all()[:limit]
        except:
            return Article.objects.all()

        # Return the queryset limited to the specified number of articles
        

    def perform_create(self, serializer):
        # Assign the current user to the article
        serializer.save(user=self.request.user)


class UserBan(APIView):
    permission_classes = [IsSuperuserOrMember]

    def get(self, request):
        users = CustomUser.objects.filter(is_superuser=False)
        return Response(AdminUserSerializer(users, many=True).data, status=HTTP_200_OK)

    def post(self, request):
        user = request.user
        if user.is_member:
            return Response({}, status=HTTP_400_BAD_REQUEST)
        userId = request.data.get("userid", None)
        if userId:
            u = CustomUser.objects.filter(
                id=userId, is_superuser=False).first()
            if u:
                u.is_active = not u.is_active
                u.save()
                return Response({}, status=HTTP_200_OK)
            else:
                return Response({}, status=HTTP_400_BAD_REQUEST)

        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)
        
class UserPromote(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        users = CustomUser.objects.filter(is_superuser=False,is_member=True)
        return Response(AdminUserSerializer(users, many=True).data, status=HTTP_200_OK)

    def post(self, request):
        userId = request.data.get("userid", None)
        action = request.data.get("action",None)
        if userId and action:
            u = CustomUser.objects.filter(
                id=userId, is_superuser=False).first()
            if u:
                if action == "promote":
                    u.is_member = True
                elif action == "demote":
                    u.is_member = False
                u.save()
                return Response({}, status=HTTP_200_OK)
            else:
                return Response({}, status=HTTP_400_BAD_REQUEST)

        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)

class UserDelete(APIView):
    permission_classes = [permissions.IsAdminUser]



    def post(self, request):
        userId = request.data.get("userid", None)
        if userId:
            u = CustomUser.objects.filter(
                id=userId, is_superuser=False).first()
            if u:
                u.delete()
                return Response({}, status=HTTP_200_OK)
            else:
                return Response({}, status=HTTP_400_BAD_REQUEST)

        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)
        

class AdmCreateTeamMember(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, format=None):
        data = request.data
        print(data)
        # del temp_data['pin']
        u = TeamMemberSerializer(data=data)
        if u.is_valid():
            u_data = u.save()
            u_data.set_password(data["password"])
            u_data.is_member = True
            u_data.save()
            return Response(TeamMemberSerializer(u_data).data)
        else:
            print(u.error_messages)
            return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
        
class AdmUserDetailsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        print("details here")
        user_id = request.query_params.get("userid",None)
        u = CustomUser.objects.filter(id=user_id).first()
        if not u:
            print("here")
            print(user_id)
            print(u)
            Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        try:
            
            user_details = UserDetails.objects.get(user=u)
            serializer = UserDetailsSerializer(
                user_details, data=request.data, partial=True)
        except UserDetails.DoesNotExist:
            newdata = request.data 
            newdata["user"] = u.id
            serializer = UserDetailsSerializer(data=newdata)

        if serializer.is_valid():
            serializer.save(user=u)
            return Response(serializer.data, status=HTTP_200_OK)
        print(serializer.error_messages)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    
class AdmUserImageView(APIView):
    permission_classes = [permissions.IsAdminUser]


    def post(self, request):
        user_id = request.query_params.get("userid",None)
        u = CustomUser.objects.filter(id=user_id).first()
        if not u:
            Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
        try:
            
            user_image = UserImage.objects.get(user=u)
            serializer = UserImageSerializer(
                user_image, data=request.data, partial=True)
        except UserImage.DoesNotExist:
            newdata = request.data 
            newdata["user"] = u.id
            serializer = UserImageSerializer(data=newdata)

        if serializer.is_valid():
            serializer.save(user=u)
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

class VideoLinksAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get_first_get_param(self, url):
        """Extracts the first GET parameter value from a URL.

        Args:
            url: The URL string.

        Returns:
            The value of the first GET parameter, or None if no parameter is found.
        """
        parsed_url = urlparse(url)
        if parsed_url.query:
            # Split query string by '&' to get individual parameters
            params = parsed_url.query.split('&')
            # Assuming the first parameter is what you need
            return params[0].split('=')[1]  # Split by '=' to get value
        else:
            return None

    def get_last_path_segment(self, url):
        """Extracts the last element (segment) of the URL path.

        Args:
            url: The URL string.

        Returns:
            The last element of the URL path, or None if the URL has no path.
        """
        url = url.split("?")[0]
        parsed_url = urlparse(url)
        path = parsed_url.path.strip('/')  # Remove leading/trailing slashes
        if path:
            return path.split('/')[-1]  # Split by '/' and get last element
        else:
            return None

    def process_link(self, l):
        if "embed" in l:
            return l
        elif "watch" in l:
            u_id = self.get_first_get_param(l)
            link = "https://www.youtube.com/embed/"+u_id
            return link
        elif "youtu.be" in l:
            u_id = self.get_last_path_segment(l)
            link = "https://www.youtube.com/embed/"+u_id
            return link

    def get(self, request):
        try:
            video_links = VideoLinks.objects.all()
            if video_links:
                serializer = VideoLinksSerializer(video_links, many=True)
                return Response(serializer.data, status=HTTP_200_OK)
            else:
                return Response({"detail": "No video link found."}, status=HTTP_404_NOT_FOUND)
        except VideoLinks.DoesNotExist:
            return Response({"detail": "No video link found."}, status=HTTP_404_NOT_FOUND)

    def post(self, request):
        video_link = VideoLinks.objects.create(link="")
        serializer = VideoLinksSerializer(video_link, data=request.data)
        if serializer.is_valid():
            obj = serializer.save()
            l = obj.link
            new_link = self.process_link(l)
            obj.link = new_link
            obj.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class PublicVideoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            user = request.user
            valid, tier, s_user, item = get_valid_and_tier(user)
            validation_res = validate_user(s_user, tier, valid, user, 1)
            if not validation_res:
                return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
            video_links = VideoLinks.objects.all()
            if video_links:
                serializer = VideoLinksSerializer(video_links, many=True)
                return Response(serializer.data, status=HTTP_200_OK)
            else:
                return Response({"detail": "No video link found."}, status=HTTP_404_NOT_FOUND)
        except VideoLinks.DoesNotExist:
            return Response({"detail": "No video link found."}, status=HTTP_404_NOT_FOUND)


class DeleteVideoLink(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        v_id = request.data.get("vid", None)
        print(request.data)
        print(v_id)
        if v_id:
            vid = VideoLinks.objects.filter(id=v_id).first()
            if vid:
                vid.delete()

            return Response({}, status=HTTP_200_OK)

        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)


class DeletePdfFile(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        f_id = request.data.get("fid", None)
        if f_id:
            f = PdfFiles.objects.filter(id=f_id).first()
            if f:
                f.delete()

            return Response({}, status=HTTP_200_OK)

        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)


class PdfFilesAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        try:
            pdf_file = PdfFiles.objects.all()
            if pdf_file:
                serializer = PdfFilesSerializer(pdf_file, many=True)
                return Response(serializer.data, status=HTTP_200_OK)
            else:
                return Response({"detail": "No PDF file found."}, status=HTTP_404_NOT_FOUND)
        except PdfFiles.DoesNotExist:
            return Response({"detail": "No PDF file found."}, status=HTTP_404_NOT_FOUND)

    def post(self, request):
        # pdf_file, created = PdfFiles.objects.get_or_create(id=1)
        serializer = PdfFilesSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class PublicPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            valid, tier, s_user, item = get_valid_and_tier(user)
            validation_res = validate_user(s_user, tier, valid, user, 1)
            if not validation_res:
                return Response({"failed": True}, status=HTTP_400_BAD_REQUEST)
            pdf_file = PdfFiles.objects.all()
            if pdf_file:
                serializer = PdfFilesSerializer(pdf_file, many=True)
                return Response(serializer.data, status=HTTP_200_OK)
            else:
                return Response({"detail": "No PDF file found."}, status=HTTP_404_NOT_FOUND)
        except PdfFiles.DoesNotExist:
            return Response({"detail": "No PDF file found."}, status=HTTP_404_NOT_FOUND)

# Recovery view


class RequestPasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        rid = request.query_params.get("rid", None)
        if rid:
            recov = RecoveryRequest.objects.filter(recovery_id=rid).first()
            if recov:

                return Response({}, status=HTTP_200_OK)
            else:
                return Response({}, status=HTTP_400_BAD_REQUEST)
        else:
            return Response({}, status=HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = EmailSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = CustomUser.objects.get(email=email)
                RecoveryRequest.objects.filter(user=user).delete()
                recovery_request = RecoveryRequest.objects.create(user=user)
                recovery_link = f"{settings.FRONT_URL}/reset-password?reqId={recovery_request.recovery_id}"
                print("sending email here ")
                print(settings.EMAIL_HOST_USER)
                send_mail(
                    'Password Recovery',
                    f'Click the link to reset your password: {recovery_link}',
                    settings.EMAIL_HOST_USER,
                    [email,],
                    fail_silently=False,
                )
                return Response({"detail": "Recovery email sent."}, status=HTTP_200_OK)
            except CustomUser.DoesNotExist:
                return Response({"detail": "User with this email does not exist."}, status=HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "Password reset successfully."}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
    


class AdminAnnouncementView(ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [IsSuperuserOrMember]
    http_method_names = ["get", "post", "delete"]


class PublicAnnouncementView(ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.AllowAny]
    http_method_names = ["get"]


class ContactFormView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ContactFormSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            email = serializer.validated_data['email']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            print(settings.EMAIL_HOST_PASSWORD)
            # Send the email
            send_mail(
                subject=f"Contact Form Submission: {subject}",
                message=f"Name: {name}\nEmail: {email}\nMessage:\n{message}",
                from_email=settings.EMAIL_HOST_USER,  # You can use a no-reply email
                recipient_list=[settings.SUPPORT_EMAIL,],
                fail_silently=False,
            )

            return Response({'message': 'Email sent successfully'}, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)
