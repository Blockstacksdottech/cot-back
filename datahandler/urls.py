from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path, re_path, include
from rest_framework import routers


router = routers.SimpleRouter()
router.register("data", DataHandler, basename="data-handler")
router.register("all-data", AllDataHandler, basename="all-data-handler")
router.register("dates", DatesHandler, basename="dates-handler")
router.register("top", HomePairsView, basename="top pairs")
router.register("adm-announcement", AdminAnnouncementView,
                basename="admin-announcement")
router.register("announcement", PublicAnnouncementView,
                basename="announcement")
router.register("blog", ArticleViewSet,
                basename="blog")
router.register("adm-seasonality",AdminSeasonalityViewSet,basename='admin-seasonality')


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
    path('general-change-data',NonCommSignalOverview.as_view(),name="general-change-data"),
    path('general-comm-change-data',CommSignalOverview.as_view(),name="general-change-data"),
    path("checkout", CustomCheckout.as_view(), name="checkout_demo"),
    # new data endpoints
    path("sentiment-data", SentimentData.as_view(), name="sentiment_data"),
    path("change-data", ChangeData.as_view(), name="change_data"),
    path("scanner-data", ScannerView.as_view(), name="scanner_data"),
    # User
    path('user-details', UserDetailsView.as_view(), name='user-details'),
    path('user-image', UserImageView.as_view(), name='user-image'),
    path("team-members",GetTeamMembers.as_view(),name="public-get-team-members"),
    path("change-password", ChangePasswordView.as_view(),
         name="change-password"),
     path("change-username", UpdateUsername.as_view(),
         name="change-username"),
    path("subscription-handler", SubscriptionHandler.as_view(),
         name="subscription-handler"),
    path("latestdate",getLatestDataDate.as_view(),name="get_latest_date"),
    # Admin
    path("userlist", UserBan.as_view(), name="user-ban"),
    path("create-team-member", AdmCreateTeamMember.as_view(),name='create-team-member'),
    path("create-team-member-details", AdmUserDetailsView.as_view(),name='create-team-member-details'),
    path("create-team-member-image", AdmUserImageView.as_view(),name='create-team-member-image'),
    path("userpromote", UserPromote.as_view(), name="user-promote"),
    path("userdelete", UserDelete.as_view(), name="user-delete"),
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
    path("fundamental",CurrencyEventDataView.as_view(),name='fondamental-view'),
    path("user-seasonality",UserSeasonalityView.as_view(),name="user-seasonality")
]
