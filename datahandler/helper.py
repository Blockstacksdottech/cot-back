from django.db.transaction import atomic
from drf_stripe.models import StripeUser
from drf_stripe.stripe_api.api import stripe_api as stripe
from drf_stripe.stripe_models.customer import StripeCustomers, StripeCustomer
from django.core.exceptions import ObjectDoesNotExist
from drf_stripe.models import get_drf_stripe_user_model as get_user_model, Subscription
from drf_stripe.stripe_models.subscription import StripeSubscriptions
from drf_stripe.stripe_api.customers import _get_or_create_django_user_if_configured, _stripe_api_get_or_create_customer_from_email, CreatingNewUsersDisabledError
from drf_stripe.stripe_api.subscriptions import _update_subscription_items
from django.utils import timezone


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


def update_user_subscription(customer_id):
    ignore_new_user_creation_errors = False
    subscriptions_response = stripe.Subscription.list(customer=customer_id)
    stripe_subscriptions = StripeSubscriptions(**subscriptions_response).data

    creation_count = 0

    for subscription in stripe_subscriptions:
        try:
            stripe_user = get_or_create_stripe_user(
                customer_id=subscription.customer)

            _, created = Subscription.objects.update_or_create(
                subscription_id=subscription.id,
                defaults={
                    "stripe_user": stripe_user,
                    "period_start": subscription.current_period_start,
                    "period_end": subscription.current_period_end,
                    "cancel_at": subscription.cancel_at,
                    "cancel_at_period_end": subscription.cancel_at_period_end,
                    "ended_at": subscription.ended_at,
                    "status": subscription.status,
                    "trial_end": subscription.trial_end,
                    "trial_start": subscription.trial_start
                }
            )
            print(f"Updated subscription {subscription.id}")
            _update_subscription_items(
                subscription.id, subscription.items.data)
            if created is True:
                creation_count += 1
        except CreatingNewUsersDisabledError as e:
            if not ignore_new_user_creation_errors:
                raise e
            else:
                print(
                    f"User for customer id '{subscription.customer}' with subscription '{subscription.id}' does not exist, skipping.")

    print(f"Created {creation_count} new Subscriptions.")


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
    if subscription.cancel_at:
        if subscription.cancel_at <= timezone.now():
            return True
        else:
            return False
    elif subscription.ended_at:
        if subscription.ended_at <= timezone.now():
            return True
        else:
            return False
    else:
        return False


def get_valid_and_tier(user):
    s_user = StripeUser.objects.filter(user=user).first()
    tier = 0
    valid = False
    item = None
    if not s_user:
        valid = False
    else:
        subscriptions = Subscription.objects.filter(
            stripe_user=s_user).order_by("-period_start")
        print(len(subscriptions))
        if len(subscriptions) == 0:
            valid = False
        else:
            print('Subscription details')
            sub = subscriptions[0]
            print(sub.period_end)
            time_valid_sub = is_subscription_valid(sub)
            print(time_valid_sub)
            cancel_valid_sub = is_subscription_canceled(sub)
            print(cancel_valid_sub)
            valid = time_valid_sub and (not cancel_valid_sub)
            if valid:
                item = s_user.subscription_items.filter(
                    subscription=sub).first()
                price_item = item.price
                product_item = price_item.product
                tier = get_tier_level(product_item.name)
    print(f"{user.username} | {valid} | {tier}")
    return valid, tier, s_user, item


def validate_user(s_user, tier, isvalid, user, requiredTier):
    if user.is_superuser or user.is_member:
        return True
    elif not isvalid:
        return False
    else:
        if tier >= requiredTier:
            return True
        else:
            return False
