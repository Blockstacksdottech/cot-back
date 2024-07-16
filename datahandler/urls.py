from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path, re_path, include
from rest_framework import routers


router = routers.SimpleRouter()
router.register("data", DataHandler, basename="data-handler")
router.register("top", HomePairsView, basename="top pairs")
router.register("adm-announcement", AdminAnnouncementView,
                basename="admin-announcement")
router.register("announcement", PublicAnnouncementView,
                basename="announcement")


urlpatterns = [
    path("", include(router.urls)),
    path('token', CustomTokenObtain.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('session', TestSession.as_view()),
    path("register", Register.as_view()),
    path('sentiment_scores', SentimentScoreView.as_view(),
         name='sentiment-scores'),
    path('net_speculative', NetSpeculativeView.as_view(),
         name='net-speculative'),
    path('crowding_positions', CrowdingPositionsView.as_view(),
         name='crowding-positions'),
    path('net_comm_speculative', NetSpeculativeCommView.as_view(),
         name='net-speculative'),
    path('crowding_comm_positions', CrowdingPositionsCommView.as_view(),
         name='crowding-positions'),
    path("checkout", CustomCheckout.as_view(), name="checkout_demo"),
    # new data endpoints
    path("sentiment-data", SentimentData.as_view(), name="sentiment_data"),
    path("change-data", ChangeData.as_view(), name="change_data"),
    path("scanner-data", ScannerView.as_view(), name="scanner_data"),
    # User
    path('user-details', UserDetailsView.as_view(), name='user-details'),
    path('user-image', UserImageView.as_view(), name='user-image'),
    path("change-password", ChangePasswordView.as_view(),
         name="change-password"),
    # Admin
    path("userlist", UserBan.as_view(), name="user-ban"),
    path('video-link', VideoLinksAPIView.as_view(), name='video-link'),
    path('public-video-link', PublicVideoView.as_view(), name='video-link'),
    path('delete-video-link', DeleteVideoLink.as_view(), name='video-link'),
    path('pdf-file', PdfFilesAPIView.as_view(), name='pdf-file-api'),
    path('delete-pdf-file', DeletePdfFile.as_view(), name='pdf-file-api'),
    path('public-pdf-file', PublicPdfView.as_view(), name='pdf-file-api'),
    path('request-password-reset', RequestPasswordResetView.as_view(),
         name='request-password-reset'),
    path('reset-password', ResetPasswordView.as_view(), name='reset-password'),
    path('contact', ContactFormView.as_view(), name='contact-form'),
]
