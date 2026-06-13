from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from auctions.models import Auction
from audit.services import log_audit
from payments.models import PaymentTransaction
from subscriptions.models import AuctionSubscription


def _for_update_kwargs():
    if connection.vendor == "postgresql":
        return {"of": ("self",)}
    return {}


def participant_type(auction: Auction, user) -> str:
    if auction.seller_id == user.id:
        return "seller"
    return "bidder"


def compute_subscription_fees(auction: Auction, user):
    """Return (insurance_fee, subscription_fee, total_fee) from category fees."""
    fees = auction.product_category.fees_configuration
    if auction.seller_id == user.id:
        insurance = fees.seller_insurance_amount
    else:
        insurance = fees.bidder_insurance_amount
    subscription = fees.subscription_amount
    return insurance, subscription, insurance + subscription


def validate_subscribe_eligibility(auction: Auction, user) -> None:
    if auction.seller_id == user.id:
        if auction.status != Auction.Status.APPROVED:
            raise DRFValidationError(
                {
                    "auction": (
                        "Seller can subscribe only when the auction is approved "
                        "(pay to activate listing)."
                    )
                }
            )
        return

    if auction.status != Auction.Status.ACTIVE:
        raise DRFValidationError(
            {"auction": "Bidders can subscribe only when the auction is active."}
        )


def activate_auction_on_seller_payment(
    auction: Auction, paid_at, *, actor=None, request=None
) -> Auction:
    auction = (
        Auction.objects.select_for_update(**_for_update_kwargs()).get(pk=auction.pk)
    )
    if auction.status != Auction.Status.APPROVED:
        return auction

    auction.starts_at = paid_at
    auction.ends_at = paid_at + timedelta(days=auction.duration_days)
    auction.origin_deadline = auction.ends_at
    auction.status = Auction.Status.ACTIVE
    auction.save(
        update_fields=[
            "starts_at",
            "ends_at",
            "origin_deadline",
            "status",
            "updated_at",
        ]
    )
    log_audit(
        actor=actor,
        entity_type="auction",
        entity_id=auction.id,
        action="seller_payment_activated",
        old_values={"status": Auction.Status.APPROVED},
        new_values={
            "status": auction.status,
            "starts_at": auction.starts_at.isoformat(),
            "ends_at": auction.ends_at.isoformat(),
        },
        request=request,
    )
    return auction


def activate_subscription_payment(
    subscription: AuctionSubscription, *, paid_at=None, request=None
) -> AuctionSubscription:
    paid_at = paid_at or timezone.now()
    subscription.status = AuctionSubscription.Status.ACTIVE
    subscription.payment_status = AuctionSubscription.PaymentStatus.PAID
    subscription.activated_at = paid_at
    subscription.save(
        update_fields=["status", "payment_status", "activated_at", "updated_at"]
    )

    auction = subscription.auction
    if subscription.user_id == auction.seller_id:
        activate_auction_on_seller_payment(
            auction, paid_at, actor=subscription.user, request=request
        )
    return subscription


def complete_subscription_payment(
    subscription: AuctionSubscription, *, paid_at=None, request=None
) -> AuctionSubscription:
    """Mark linked payment succeeded and activate subscription atomically."""
    paid_at = paid_at or timezone.now()
    with transaction.atomic():
        PaymentTransaction.objects.filter(
            related_entity_type=PaymentTransaction.RelatedEntityType.SUBSCRIPTION,
            related_entity_id=subscription.id,
        ).update(
            status=PaymentTransaction.PaymentStatus.SUCCEEDED,
            completed_at=paid_at,
        )
        return activate_subscription_payment(
            subscription, paid_at=paid_at, request=request
        )
