from django.db.transaction import atomic
from drf_stripe.models import StripeUser
from drf_stripe.stripe_api.api import stripe_api as stripe
from drf_stripe.stripe_models.customer import StripeCustomers, StripeCustomer
from django.core.exceptions import ObjectDoesNotExist
from drf_stripe.models import get_drf_stripe_user_model as get_user_model
from drf_stripe.stripe_api.customers import _get_or_create_django_user_if_configured, _stripe_api_get_or_create_customer_from_email


@atomic()
def get_or_create_stripe_user(**kwargs) -> StripeUser:
    """
    Get or create a StripeUser given a User instance, or given user id and user email.

    :key user_instance: Django user instance.
    :key str user_id: Django User id.
    :key str user_email: user email address.
    :key str customer_id: Stripe customer id.
    """
    print("Custom helper !!!!!!!!!")
    user_instance = kwargs.get("user_instance")
    user_id = kwargs.get("user_id")
    user_email = kwargs.get("user_email")
    customer_id = kwargs.get("customer_id")

    if user_instance and isinstance(user_instance, get_user_model()):
        return _get_or_create_stripe_user_from_user_instance(user_instance)
    elif user_id and user_email and isinstance(user_id, str):
        return _get_or_create_stripe_user_from_user_id_email(user_id, user_email)
    elif user_id is not None:
        return _get_or_create_stripe_user_from_user_id(user_id)
    elif customer_id is not None:
        return _get_or_create_stripe_user_from_customer_id(customer_id)
    else:
        raise TypeError("Unknown keyword arguments!")


def _get_or_create_stripe_user_from_user_id_email(user_id, user_email: str, customer_id: str = None):
    """
    Return a StripeUser instance given user_id and user_email.

    :param user_id: user id
    :param str user_email: user email address
    """
    stripe_user, created = StripeUser.objects.get_or_create(
        user_id=user_id, customer_id=customer_id)

    if created and not customer_id:
        customer = _stripe_api_get_or_create_customer_from_email(user_email)
        stripe_user.customer_id = customer.id
        stripe_user.save()

    return stripe_user


def _get_or_create_stripe_user_from_user_instance(user_instance):
    """
    Returns a StripeUser instance given a Django User instance.

    :param user_instance: Django User instance.
    """
    return _get_or_create_stripe_user_from_user_id_email(user_instance.id, user_instance.email)


def _get_or_create_stripe_user_from_user_id(user_id):
    """
    Returns a StripeUser instance given user_id.

    :param str user_id: user id
    """
    user = get_user_model().objects.get(id=user_id)
    stripe_user = StripeUser.objects.filter(user=user).first()
    if stripe_user:
        customer_id = stripe_user.customer_id
    else:
        customer_id = None

    return _get_or_create_stripe_user_from_user_id_email(user.id, user.email, customer_id)


def _get_or_create_stripe_user_from_customer_id(customer_id):
    """
    Returns a StripeUser instance given customer_id

    If there is no Django user connected to a StripeUser with the given customer_id then
    Stripe's customer API is called to get the customer's details (e.g. email address).
    Then if a Django user exists for that email address a StripeUser record will be created.
    If a Django user does not exist for that email address and USER_CREATE_DEFAULTS_ATTRIBUTE_MAP
    is set then a Django user will be created along with a StripeUser record. If
    USER_CREATE_DEFAULTS_ATTRIBUTE_MAP is not set then a CreatingNewUsersDisabledError will be raised.

    :param str customer_id: Stripe customer id
    """

    try:
        user = get_user_model().objects.get(stripe_user__customer_id=customer_id)

    except ObjectDoesNotExist:
        customer_response = stripe.Customer.retrieve(customer_id)
        customer = StripeCustomer(**customer_response)
        user, created = _get_or_create_django_user_if_configured(customer)
        if created:
            print(f"Created new User with customer_id {customer_id}")

    return _get_or_create_stripe_user_from_user_id_email(user.id, user.email, customer_id)
