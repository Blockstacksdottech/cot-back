from .models import (
    CustomUser, DateInterval, Data, GeneralData, ProcessedData, UserDetails, UserImage, VideoLinks, PdfFiles, RecoveryRequest, Announcement, Article
)
from rest_framework.serializers import ModelSerializer, SerializerMethodField
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from rest_framework import exceptions, serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings
from drf_stripe.serializers import CheckoutRequestSerializer, StripeError
from drf_stripe.stripe_api.checkout import stripe_api_create_checkout_session
from .helper import get_or_create_stripe_user, get_valid_and_tier


class CustomCheckoutSerializer(CheckoutRequestSerializer):
    def validate(self, attrs):
        print("validation here !!!!!!!!!!")
        stripe_user = get_or_create_stripe_user(
            user_id=self.context['request'].user.id)
        try:
            checkout_session = stripe_api_create_checkout_session(
                customer_id=stripe_user.customer_id,
                price_id=attrs['price_id'],
                trial_end='auto' if stripe_user.subscription_items.count() == 0 else None
            )
            attrs['session_id'] = checkout_session['id']
        except StripeError as e:
            raise ValidationError(e.error)
        return attrs


class PasswordField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("style", {})

        kwargs["style"]["input_type"] = "password"
        kwargs["write_only"] = True

        super().__init__(*args, **kwargs)


class MyTokenObtainSerializer(serializers.Serializer):
    username_field = "email"

    def __init__(self, *args, **kwargs):
        super(MyTokenObtainSerializer, self).__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = PasswordField()

    def validate(self, attrs):
        # self.user = authenticate(**{
        #     self.username_field: attrs[self.username_field],
        #     'password': attrs['password'],
        # })
        print(attrs)
        self.user = CustomUser.objects.filter(email=attrs[self.username_field]).first(
        ) or CustomUser.objects.filter(username=attrs[self.username_field]).first()
        print(self.user)

        if not self.user:
            raise ValidationError('The user is not valid.')

        if self.user:
            print("password here")
            print(self.user.password)
            if not self.user.check_password(attrs['password']):
                raise ValidationError('Incorrect credentials.')

        # Prior to Django 1.10, inactive users could be authenticated with the
        # default `ModelBackend`.  As of Django 1.10, the `ModelBackend`
        # prevents inactive users from authenticating.  App designers can still
        # allow inactive users to authenticate by opting for the new
        # `AllowAllUsersModelBackend`.  However, we explicitly prevent inactive
        # users from authenticating to enforce a reasonable policy and provide
        # sensible backwards compatibility with older Django versions.
        if self.user is None or not self.user.is_active:
            raise ValidationError(
                'No active account found with the given credentials')

        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplemented(
            'Must implement `get_token` method for `MyTokenObtainSerializer` subclasses')


class MyTokenObtainPairSerializer(MyTokenObtainSerializer):
    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super(MyTokenObtainPairSerializer, self).validate(attrs)

        refresh = self.get_token(self.user)
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        print("here")
        print(data)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class UserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDetails
        fields = "__all__"


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UserImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserImage
        fields = ['profile_picture']


class DateSerializer(serializers.ModelSerializer):

    # En utilisant un `SerializerMethodField', il est nécessaire d'écrire une méthode
    # nommée 'get_XXX' où XXX est le nom de l'attribut, ici 'products'
    data = serializers.SerializerMethodField()

    class Meta:
        model = DateInterval
        fields = "__all__"

    def get_data(self, instance):
        # Le paramètre 'instance' est l'instance de la catégorie consultée.
        # Dans le cas d'une liste, cette méthode est appelée autant de fois qu'il y a
        # d'entités dans la liste

        # On applique le filtre sur notre queryset pour n'avoir que les produits actifs
        queryset = ProcessedData.objects.filter(date_interval=instance)
        print(queryset)
        # Le serializer est créé avec le queryset défini et toujours défini en tant que many=True
        serializer = ProcessedDataSerializer(queryset, many=True)
        # la propriété '.data' est le rendu de notre serializer que nous retournons ici
        return serializer.data


class DataSerialzier(ModelSerializer):
    class Meta:
        model = Data
        fields = "__all__"


class GeneralDataSerializer(ModelSerializer):
    class Meta:
        model = GeneralData
        fields = "__all__"


class ProcessedDataSerializer(ModelSerializer):
    class Meta:
        model = ProcessedData
        fields = "__all__"


class UserSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"
        extra_kwargs = {'password': {'write_only': True, 'required': True}}


class HomeDateSerializer(ModelSerializer):
    # En utilisant un `SerializerMethodField', il est nécessaire d'écrire une méthode
    # nommée 'get_XXX' où XXX est le nom de l'attribut, ici 'products'
    data = serializers.SerializerMethodField()

    class Meta:
        model = DateInterval
        fields = "__all__"

    def get_data(self, instance):
        # Le paramètre 'instance' est l'instance de la catégorie consultée.
        # Dans le cas d'une liste, cette méthode est appelée autant de fois qu'il y a
        # d'entités dans la liste

        # On applique le filtre sur notre queryset pour n'avoir que les produits actifs
        queryset = ProcessedData.objects.filter(
            date_interval=instance, is_contract=False)
        # Le serializer est créé avec le queryset défini et toujours défini en tant que many=True
        queryset = queryset if len(queryset) < 5 else queryset[:5]
        serializer = HomePairChangeSerializer(queryset, many=True)
        # la propriété '.data' est le rendu de notre serializer que nous retournons ici
        return serializer.data


class HomeDateAllSerializer(ModelSerializer):
    # En utilisant un `SerializerMethodField', il est nécessaire d'écrire une méthode
    # nommée 'get_XXX' où XXX est le nom de l'attribut, ici 'products'
    data = serializers.SerializerMethodField()

    class Meta:
        model = DateInterval
        fields = "__all__"

    def get_data(self, instance):
        # Le paramètre 'instance' est l'instance de la catégorie consultée.
        # Dans le cas d'une liste, cette méthode est appelée autant de fois qu'il y a
        # d'entités dans la liste

        # On applique le filtre sur notre queryset pour n'avoir que les produits actifs
        queryset = ProcessedData.objects.filter(
            date_interval=instance)
        # Le serializer est créé avec le queryset défini et toujours défini en tant que many=True
        serializer = HomePairChangeSerializer(queryset, many=True)
        # la propriété '.data' est le rendu de notre serializer que nous retournons ici
        return serializer.data


class HomePairChangeSerializer(ModelSerializer):
    class Meta:
        model = ProcessedData
        fields = [
            'pair',
            'pair_pct_change',
            'pair_comm_pct_change',
            'pair_2_week_change',
            'pair_3_week_change',
            'pair_4_week_change',
            'pair_5_week_change',
            'pair_6_week_change',
            'pair_7_week_change',
            'pair_8_week_change',
            'pair_9_week_change',
            'pair_10_week_change',
            'pair_comm_2_week_change',
            'pair_comm_3_week_change',
            'pair_comm_4_week_change',
            'pair_comm_5_week_change',
            'pair_comm_6_week_change',
            'pair_comm_7_week_change',
            'pair_comm_8_week_change',
            'pair_comm_9_week_change',
            'pair_comm_10_week_change',
            "pair_pct_change_open_interest",
            "pair_2_week_change_open_interest",
            "pair_3_week_change_open_interest",
            "pair_4_week_change_open_interest",
            "pair_5_week_change_open_interest",
            "pair_6_week_change_open_interest",
            "pair_7_week_change_open_interest",
            "pair_8_week_change_open_interest",
            "pair_9_week_change_open_interest",
            "pair_10_week_change_open_interest",
        ]


class ScannerDateSerializer(ModelSerializer):
    # En utilisant un `SerializerMethodField', il est nécessaire d'écrire une méthode
    # nommée 'get_XXX' où XXX est le nom de l'attribut, ici 'products'
    data = serializers.SerializerMethodField()

    class Meta:
        model = DateInterval
        fields = "__all__"

    def get_data(self, instance):
        # Le paramètre 'instance' est l'instance de la catégorie consultée.
        # Dans le cas d'une liste, cette méthode est appelée autant de fois qu'il y a
        # d'entités dans la liste

        # On applique le filtre sur notre queryset pour n'avoir que les produits actifs
        queryset = ProcessedData.objects.filter(
            date_interval=instance)
        # Le serializer est créé avec le queryset défini et toujours défini en tant que many=True
        serializer = ScannerSerializer(queryset, many=True)
        # la propriété '.data' est le rendu de notre serializer que nous retournons ici
        return serializer.data


class ScannerSerializer(ModelSerializer):
    class Meta:
        model = ProcessedData
        fields = [
            'pair',
            'pair_pct_change',
            'pair_comm_pct_change',
            'pair_3_week_change',
            'pair_5_week_change',
            'pair_10_week_change',
            'pair_comm_3_week_change',
            'pair_comm_5_week_change',
            'pair_comm_10_week_change',
            'base_long',
            'base_short',
            'base_net_position',
            'quote_long',
            'quote_short',
            'base_comm_long',
            'base_comm_short',
            'quote_comm_long',
            'quote_comm_short',
            'noncomm_diff_absolute_long',
            'noncomm_diff_absolute_short',
            'comm_diff_absolute_long',
            'comm_diff_absolute_short',
            'noncomm_10_diff_absolute_long',
            'noncomm_10_diff_absolute_short',
            'comm_10_diff_absolute_long',
            'comm_10_diff_absolute_short',
        ]


class AdminUserSerializer(serializers.ModelSerializer):

    details = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    sub = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "username", "is_active",
                  "email", "details", "image", "sub","is_member","date_joined"]

    def get_details(self, instance):
        d = UserDetails.objects.filter(user=instance).first()
        if not d:
            d = UserDetails.objects.create(user=instance)
            d.save()
        return UserDetailsSerializer(d).data

    def get_image(self, instance):
        i = UserImage.objects.filter(user=instance).first()
        if i:
            return UserImageSerializer(i).data
        else:
            return None

    def get_sub(self, instance):
        valid, tier, s_user, item = get_valid_and_tier(instance)
        return {"valid": valid, "tier": tier}
    
class HomeUserSerializer(serializers.ModelSerializer):

    details = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
  

    class Meta:
        model = CustomUser
        fields = ["id", "username", "is_active",
                  "email", "details", "image","is_member","date_joined"]

    def get_details(self, instance):
        d = UserDetails.objects.filter(user=instance).first()
        if not d:
            d = UserDetails.objects.create(user=instance)
            d.save()
        return UserDetailsSerializer(d).data

    def get_image(self, instance):
        i = UserImage.objects.filter(user=instance).first()
        if i:
            return UserImageSerializer(i).data
        else:
            return None



class VideoLinksSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoLinks
        fields = ['id', 'topic', 'link']


class PdfFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = PdfFiles
        fields = ['id', 'topic', 'file']


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetSerializer(serializers.Serializer):
    recovery_id = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)

    def validate_recovery_id(self, value):
        try:
            self.recovery_request = RecoveryRequest.objects.get(
                recovery_id=value)
        except RecoveryRequest.DoesNotExist:
            raise serializers.ValidationError("Invalid recovery ID")
        return value

    def save(self):
        self.recovery_request.user.set_password(
            self.validated_data['new_password'])
        self.recovery_request.user.save()
        self.recovery_request.delete()


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'topic', 'description', 'date']
        extra_kwargs = {'date': {'read_only': True, 'required': False}}


class ContactFormSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()


class ArticleSerializer(serializers.ModelSerializer):
    user = AdminUserSerializer(read_only=True)
    class Meta:
        model = Article
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': True}
        }

    def create(self, validated_data):
        # Ensure the user is correctly linked when creating an article
        article = Article.objects.create(**validated_data)
        return article


class TeamMemberSerializer(ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"
        extra_kwargs = {'password': {'write_only': True, 'required': True}}