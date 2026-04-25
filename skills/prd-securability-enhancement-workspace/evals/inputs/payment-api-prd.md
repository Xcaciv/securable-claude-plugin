# PRD: Merchant Payouts API v2

## Context

We operate a multi-sided marketplace. Merchants sell goods to consumers; we collect payment from consumers and remit net proceeds (gross sales minus fees and refunds) to merchants on a weekly cadence. This PRD covers v2 of the Merchant Payouts API, which lets merchants programmatically read payout history and trigger on-demand payouts to their bank account.

Volume: ~40k active merchants, ~$120M/month in payouts, ~$1.5B/year. Subject to PCI-DSS (we tokenize, but issuance and reconciliation touch the regulated zone) and varying state money-transmitter regulations.

## Features

### F-01: List payouts

A merchant calls `GET /v2/payouts?from=YYYY-MM-DD&to=YYYY-MM-DD` with their API key. The response lists all payouts in the window (ID, amount, currency, scheduled date, status, destination bank account fingerprint).

### F-02: Get payout detail

A merchant calls `GET /v2/payouts/{payout_id}`. The response includes line-item breakdown: gross sales, fees, refunds, adjustments, net amount, source orders.

### F-03: Trigger on-demand payout

A merchant calls `POST /v2/payouts` with `{amount, currency, destination_bank_account_id}`. We verify available balance, create a payout, and return its ID. The destination must be a bank account the merchant previously verified via micro-deposit.

### F-04: Update payout schedule

A merchant calls `PUT /v2/payouts/schedule` with `{cadence, day_of_week}` to change their automatic payout cadence between weekly, biweekly, or daily.

### F-05: Webhook on payout state change

We POST to a merchant-configured URL whenever a payout transitions state (queued → processing → paid → failed). The merchant must verify the webhook signature before acting on it.

## Out of Scope

- Merchant onboarding (separate flow)
- Bank account verification (covered by separate PRD)
- Consumer-side refund flows

## Acceptance

- p99 latency under 800ms for list/detail endpoints.
- 99.95% availability for the API surface.
- All payout state changes deliver a webhook within 60 seconds.
