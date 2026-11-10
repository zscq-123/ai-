import hashlib
import hmac
from uuid import UUID

import httpx
from pydantic import BaseModel

from ai_service.config import Settings
from ai_service.domain.models import Citation
from ai_service.domain.ports import SupportToolProvider


class ToolEvidencePayload(BaseModel):
    content: str
    title: str
    reference: str


def canonical_tool_request(
    message: str,
    *,
    customer_id: UUID | None,
    merchant_id: UUID | None,
    product_id: UUID | None,
    sku_id: UUID | None,
) -> str:
    return "\n".join(
        (
            str(customer_id or ""),
            str(merchant_id or ""),
            str(product_id or ""),
            str(sku_id or ""),
            message,
        )
    )


class NullSupportTools:
    async def lookup(
        self,
        message: str,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> list[tuple[str, Citation]]:
        del message, customer_id, merchant_id, product_id, sku_id
        return []


class CommerceSupportTools:
    """Read-only, customer-scoped evidence from the NOVA commerce service."""

    def __init__(
        self,
        base_url: str,
        secret: str,
        *,
        timeout_seconds: float = 3.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = secret.encode()
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def lookup(
        self,
        message: str,
        *,
        customer_id: UUID | None = None,
        merchant_id: UUID | None = None,
        product_id: UUID | None = None,
        sku_id: UUID | None = None,
    ) -> list[tuple[str, Citation]]:
        canonical = canonical_tool_request(
            message,
            customer_id=customer_id,
            merchant_id=merchant_id,
            product_id=product_id,
            sku_id=sku_id,
        )
        signature = hmac.new(self._secret, canonical.encode(), hashlib.sha256).hexdigest()
        body = {
            "message": message,
            "customerId": str(customer_id) if customer_id is not None else None,
            "merchantId": str(merchant_id) if merchant_id is not None else None,
            "productId": str(product_id) if product_id is not None else None,
            "skuId": str(sku_id) if sku_id is not None else None,
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
                trust_env=False,
            ) as client:
                response = await client.post(
                    "/api/internal/support/evidence",
                    headers={"X-Nova-Tool-Signature": signature},
                    json=body,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, list):
                    return []
                evidence = [ToolEvidencePayload.model_validate(item) for item in payload]
        except (httpx.HTTPError, ValueError):
            return []
        return [
            (item.content, Citation(item.title, item.reference))
            for item in evidence
            if item.content.strip() and item.reference.strip()
        ]


def build_support_tool_provider(settings: Settings) -> SupportToolProvider:
    if not settings.commerce_tool_secret:
        return NullSupportTools()
    return CommerceSupportTools(
        settings.commerce_api_url,
        settings.commerce_tool_secret,
        timeout_seconds=settings.commerce_tool_timeout_seconds,
    )
