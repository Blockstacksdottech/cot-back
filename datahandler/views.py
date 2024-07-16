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
    elif "custom" in name_lower:
        return 4
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

# admin user management


class UserBan(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        users = CustomUser.objects.filter(is_superuser=False)
        return Response(AdminUserSerializer(users, many=True).data, status=HTTP_200_OK)

    def post(self, request):
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


class VideoLinksAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

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
            serializer.save()
            return Response(serializer.data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)


class PublicVideoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            user = request.user
            valid, tier, s_user = get_valid_and_tier(user)
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
            valid, tier, s_user = get_valid_and_tier(user)
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
    permission_classes = [permissions.IsAdminUser]
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
