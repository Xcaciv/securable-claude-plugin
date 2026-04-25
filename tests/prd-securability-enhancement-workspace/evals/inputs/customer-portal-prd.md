# PRD: Customer Self-Service Portal — Account Recovery

## Context

We're adding self-service account recovery to our customer portal (B2C SaaS, ~250k monthly active users). The portal already has username/password login and email-based sign-up. This PRD covers the account-recovery workflow: forgot password, account lockout recovery, and recovery code issuance for users with 2FA enabled.

The portal handles personal data: names, email addresses, billing addresses, order history. No payment instruments are stored in our system (handled by an external PSP).

## Features

### F-01: Forgot password

A user who does not remember their password can click "Forgot password?" on the login screen. They enter their email address and receive a reset link. Clicking the link lets them set a new password.

### F-02: Account lockout recovery

After 5 failed login attempts within 10 minutes, the account is locked. The user sees a "Your account is locked" message. They can request an unlock email; clicking the link in that email unlocks the account.

### F-03: Recovery codes for 2FA users

Users with 2FA enabled can generate a one-time set of 10 recovery codes from their account settings. If the user later loses their 2FA device, they can use a recovery code in place of their TOTP code at login. Used codes are invalidated.

### F-04: Recovery via support agent

If automated recovery fails, the user can contact support. A support agent can verify the user's identity (verbal challenge against on-file data) and trigger a one-time bypass that sends an emergency reset link to the email on file.

## Constraints

- Must integrate with our existing email provider (SendGrid).
- Recovery flows must work for users in EU (GDPR) and US.
- Must not introduce more than 200ms of latency to the login flow.

## Acceptance

- Users can recover access in under 5 minutes for the common case.
- Support team's recovery-related tickets drop by 30% within 90 days of launch.
