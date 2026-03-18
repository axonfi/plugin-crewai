# crewai-axon

CrewAI toolkit for [Axon](https://axonfi.xyz) — treasury and payment infrastructure for autonomous AI agents.

Gives your CrewAI agents the ability to send payments, swap tokens, interact with DeFi protocols, and check vault balances — all through non-custodial Axon vaults with gasless EIP-712 signing.

## Prerequisites

Before using this plugin, you need an Axon vault:

1. **Go to [app.axonfi.xyz](https://app.axonfi.xyz)** and connect your wallet
2. **Deploy a vault** - this is your non-custodial treasury. Only you (the owner) can withdraw.
3. **Register a bot key** - generate a new key pair in the dashboard or bring your own. This is the key your CrewAI agent will sign with. Set a `maxPerTxAmount` to cap what the bot can spend per transaction.
4. **Fund the vault** - deposit USDC (or any ERC-20) into your vault address.
5. **Copy your credentials**:
   - `vault_address` - your deployed vault address
   - `bot_private_key` - the bot's private key (the one registered in step 3)
   - `chain_id` - 8453 (Base), 42161 (Arbitrum), or 84532 (Base Sepolia for testing)

Your bot signs payment intents. It never holds funds, never pays gas, and can only spend within the limits you set. If the bot key is compromised, the attacker is capped by `maxPerTxAmount` and can only send to whitelisted destinations.

## Installation

```bash
pip install crewai-axon
```

## Quick Start

```python
from crewai import Agent, Task, Crew
from crewai_axon import AxonToolkit

# Initialize the toolkit
toolkit = AxonToolkit(
    vault_address="0x05c6ab8c7b0b1bb42980d9b6a4cb666f0af424c7",
    chain_id=84532,           # Base Sepolia
    bot_private_key="0x...",
)

# Create an agent with Axon tools
agent = Agent(
    role="Treasury Manager",
    goal="Manage vault funds and execute payments",
    backstory="You manage an on-chain treasury vault for an AI agent fleet.",
    tools=toolkit.get_tools(),
)

# Example: check balance and send payment
task = Task(
    description="Check the USDC balance in the vault, then send 5.00 USDC to 0xRecipient...",
    expected_output="Transaction hash of the payment",
    agent=agent,
)

crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
```

## Available Tools

| Tool | Description |
|------|-------------|
| `axon_pay` | Send a payment from the vault (e.g. 5.00 USDC to a recipient) |
| `axon_swap` | Swap tokens within the vault (e.g. 10.00 USDC to WETH) |
| `axon_execute_protocol` | Call a DeFi protocol contract through the vault |
| `axon_get_balance` | Check the vault balance for a specific token |
| `axon_get_vault_value` | Get total USD value of the vault with per-token breakdown |

All amounts are **human-readable** (e.g. `5.00` for 5 USDC, not `5000000`).

## Configuration

### Raw Private Key

```python
toolkit = AxonToolkit(
    vault_address="0x...",
    chain_id=84532,
    bot_private_key="0x...",
)
```

### Keystore File

```python
toolkit = AxonToolkit(
    vault_address="0x...",
    chain_id=84532,
    bot_keystore="bot-keystore.json",
    bot_passphrase="your-passphrase",
)
```

### Custom Relayer URL

```python
toolkit = AxonToolkit(
    vault_address="0x...",
    chain_id=84532,
    bot_private_key="0x...",
    relayer_url="https://relay.axonfi.xyz",
)
```

## Tool Details

### PayTool (`axon_pay`)

Send a payment from the vault to any recipient address.

```
Parameters:
  to       — Recipient address (0x...)
  amount   — Human-readable amount (e.g. 5.00 for 5 USDC)
  token    — Token symbol, default "USDC"
  memo     — Optional payment description
```

### SwapTool (`axon_swap`)

Swap tokens within the vault. Output stays in the vault (rebalancing).

```
Parameters:
  from_token — Source token symbol (e.g. USDC)
  to_token   — Target token symbol (e.g. WETH)
  amount     — Human-readable amount of source token to swap
```

### ExecuteProtocolTool (`axon_execute_protocol`)

Call a DeFi protocol contract through the vault (approve/call/revoke pattern).

```
Parameters:
  target   — Protocol contract address (0x...)
  calldata — ABI-encoded function calldata (0x...)
  token    — Token to approve, default "USDC"
  amount   — Approval amount in human-readable units
  memo     — Optional description
```

### GetBalanceTool (`axon_get_balance`)

Check how much of a token the vault holds.

```
Parameters:
  token — Token symbol, default "USDC"
```

### GetVaultValueTool (`axon_get_vault_value`)

Get the total USD value of the vault with a per-token breakdown. No parameters required.

## How It Works

1. Your CrewAI agent decides to use a tool (e.g. `axon_pay`)
2. The tool signs an EIP-712 intent using the bot's private key
3. The signed intent is submitted to the Axon relayer
4. The relayer validates policies, runs AI verification if needed, and executes on-chain
5. The bot never holds funds or pays gas

## Supported Chains

| Chain | Chain ID |
|-------|----------|
| Base Sepolia (testnet) | `84532` |
| Base | `8453` |
| Arbitrum One | `42161` |

## License

MIT
