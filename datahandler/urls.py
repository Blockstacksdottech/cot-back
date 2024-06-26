from .views import *
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.urls import path, re_path, include
from rest_framework import routers


router = routers.SimpleRouter()
router.register("data", DataHandler, basename="data-handler")


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
]
