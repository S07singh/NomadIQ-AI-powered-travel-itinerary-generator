"""
Payment provider interface. Plug Razorpay (India) / Stripe (global) in here.
The mock accepts any token except "tok_fail".
"""

from abc import ABC, abstractmethod
from enum import StrEnum

from app.common.schemas import APIModel, Money
from app.core.utils import new_token


class PaymentStatus(StrEnum):
    requires_payment = "requires_payment"
    succeeded = "succeeded"
    failed = "failed"
    refunded = "refunded"


class PaymentIntent(APIModel):
    id: str
    provider: str
    amount: Money
    status: PaymentStatus
    client_secret: str | None = None
    failure_reason: str | None = None


class PaymentProvider(ABC):
    name = "base"

    @abstractmethod
    async def create_intent(self, amount: Money, metadata: dict) -> PaymentIntent: ...

    @abstractmethod
    async def capture(self, intent: PaymentIntent, payment_token: str | None) -> PaymentIntent: ...

    @abstractmethod
    async def refund(self, intent: PaymentIntent) -> PaymentIntent: ...


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    async def create_intent(self, amount: Money, metadata: dict) -> PaymentIntent:
        return PaymentIntent(id=f"pi_mock_{new_token(9)}", provider=self.name, amount=amount, status=PaymentStatus.requires_payment, client_secret=f"secret_{new_token(12)}")

    async def capture(self, intent: PaymentIntent, payment_token: str | None) -> PaymentIntent:
        if payment_token == "tok_fail":
            return intent.model_copy(update={"status": PaymentStatus.failed, "failure_reason": "Card declined (simulated)"})
        return intent.model_copy(update={"status": PaymentStatus.succeeded})

    async def refund(self, intent: PaymentIntent) -> PaymentIntent:
        return intent.model_copy(update={"status": PaymentStatus.refunded})
