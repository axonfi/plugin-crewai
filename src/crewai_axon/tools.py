"""Axon CrewAI tools — BaseTool subclasses for vault operations."""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# ── Pydantic input schemas ──────────────────────────────────────────────────


class PayInput(BaseModel):
    """Input for sending a payment from the vault."""

    to: str = Field(description="Recipient address (0x...)")
    amount: float = Field(description="Human-readable amount (e.g. 5.00 for 5 USDC)")
    token: str = Field(default="USDC", description="Token symbol (USDC, WETH, etc.) or contract address")
    memo: str | None = Field(default=None, description="Optional payment description")


class SwapInput(BaseModel):
    """Input for in-vault token rebalancing."""

    from_token: str = Field(description="Source token symbol (e.g. USDC)")
    to_token: str = Field(description="Target token symbol (e.g. WETH)")
    amount: float = Field(description="Human-readable amount of source token to swap (e.g. 10.00 for 10 USDC)")


class ExecuteProtocolInput(BaseModel):
    """Input for DeFi protocol interaction."""

    target: str = Field(description="Target protocol contract address (0x...)")
    calldata: str = Field(description="ABI-encoded function calldata (0x...)")
    token: str = Field(default="USDC", description="Token to approve for the protocol")
    amount: float = Field(default=0, description="Approval amount in human-readable units (e.g. 100.00)")
    memo: str | None = Field(default=None, description="Optional description")


class GetBalanceInput(BaseModel):
    """Input for checking vault token balance."""

    token: str = Field(default="USDC", description="Token symbol (default: USDC)")


class GetVaultValueInput(BaseModel):
    """Input for getting vault total USD value (no parameters required)."""

    pass


# ── Helper ───────────────────────────────────────────────────────────────────


def _format_result(result) -> str:
    """Format a PaymentResult into an LLM-friendly string."""
    if result.status == "approved":
        return f"Approved! TX: {result.tx_hash}"
    elif result.status == "pending_review":
        return f"Under review (request ID: {result.request_id}). Poll later to check status."
    else:
        return f"Rejected: {result.reason}"


# ── Tools ────────────────────────────────────────────────────────────────────


class PayTool(BaseTool):
    """Send a payment from the Axon vault to a recipient address."""

    name: str = "axon_pay"
    description: str = (
        "Send a payment from the Axon vault. Specify recipient address and amount "
        "in human-readable units (e.g. 5.00 for 5 USDC). Optionally specify token "
        "(default: USDC) and memo. Returns transaction hash if approved, or a "
        "request ID if the payment requires human review."
    )
    args_schema: type[BaseModel] = PayInput
    client: object = Field(exclude=True)

    def _run(self, to: str, amount: float, token: str = "USDC", memo: str | None = None) -> str:
        result = self.client.pay(to=to, token=token, amount=amount, memo=memo)
        return _format_result(result)


class SwapTool(BaseTool):
    """Swap tokens within the vault (in-vault rebalancing)."""

    name: str = "axon_swap"
    description: str = (
        "Swap tokens within the vault for rebalancing. The output stays in the vault. "
        "Specify source token, target token, and amount in human-readable units "
        "(e.g. 10.00 to swap 10 USDC to WETH). The amount refers to the source token."
    )
    args_schema: type[BaseModel] = SwapInput
    client: object = Field(exclude=True)

    def _run(self, from_token: str, to_token: str, amount: float) -> str:
        result = self.client.swap(
            from_token=from_token,
            to_token=to_token,
            min_to_amount=0,
            max_from_amount=amount,
        )
        return _format_result(result)


class ExecuteProtocolTool(BaseTool):
    """Execute a DeFi protocol interaction through the vault."""

    name: str = "axon_execute_protocol"
    description: str = (
        "Call a DeFi protocol contract through the vault. The vault approves the token, "
        "executes the call, then revokes approval. Provide the protocol contract address "
        "and ABI-encoded calldata. Optionally specify token and approval amount in "
        "human-readable units (e.g. 100.00 for 100 USDC)."
    )
    args_schema: type[BaseModel] = ExecuteProtocolInput
    client: object = Field(exclude=True)

    def _run(
        self,
        target: str,
        calldata: str,
        token: str = "USDC",
        amount: float = 0,
        memo: str | None = None,
    ) -> str:
        kwargs: dict = {
            "protocol": target,
            "call_data": calldata,
            "memo": memo,
        }
        if amount > 0:
            kwargs["tokens"] = [token]
            kwargs["amounts"] = [amount]
        result = self.client.execute(**kwargs)
        return _format_result(result)


class GetBalanceTool(BaseTool):
    """Check the vault balance for a specific token."""

    name: str = "axon_get_balance"
    description: str = (
        "Check how much of a token the vault holds. Returns the balance in "
        "human-readable units (e.g. '125.50 USDC'). Default token is USDC."
    )
    args_schema: type[BaseModel] = GetBalanceInput
    client: object = Field(exclude=True)
    chain_id: int = Field(exclude=True)

    def _run(self, token: str = "USDC") -> str:
        from axonfi import KNOWN_TOKENS, resolve_token

        token_address = resolve_token(token, self.chain_id)
        balance_raw = self.client.get_balance(token_address)

        info = KNOWN_TOKENS.get(token.upper())
        if info:
            human = balance_raw / (10**info.decimals)
            return f"Vault holds {human:.6g} {token.upper()}"
        return f"Vault holds {balance_raw} base units of {token}"


class GetVaultValueTool(BaseTool):
    """Get the total USD value of the vault with per-token breakdown."""

    name: str = "axon_get_vault_value"
    description: str = (
        "Get the total USD value of the vault, including a breakdown by token. "
        "Returns total value in USD and each token's balance, price, and value."
    )
    args_schema: type[BaseModel] = GetVaultValueInput
    client: object = Field(exclude=True)

    def _run(self) -> str:
        value = self.client.get_vault_value()
        lines = [f"Total vault value: ${value.total_value_usd:.2f}"]
        for t in value.tokens:
            human_balance = int(t.balance) / (10**t.decimals)
            lines.append(f"  {t.symbol}: {human_balance:.6g} (${t.value_usd:.2f} @ ${t.price_usd:.4g})")
        return "\n".join(lines)
