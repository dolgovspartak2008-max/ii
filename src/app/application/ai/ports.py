"""Ports used by tenant-scoped AI reply use cases."""

from typing import Protocol
from uuid import UUID


class AIResponder(Protocol):
    """Generate one customer-facing answer from isolated tenant context."""

    async def generate(
        self,
        tenant_id: UUID,
        business_name: str,
        business_description: str,
        customer_text: str,
    ) -> str: ...
