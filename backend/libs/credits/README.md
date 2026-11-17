# Credits

Each user holds a USD credit balance that pays for their generate-text runs. Admins and
invites grant credits, each completed step is charged at its LLM cost times a markup,
and the steps a failed run loses are refunded.

## How it works

1. The balance is `psg_user.credit_balance_usd`, starting at 0 and moved with every
   `psg_credit_ledger` row. Grants come from an invite redeemed at sign-in
   (`InviteService.redeem_invite`) and from an admin's `credit-grants` route.
2. The `validate_credit_balance_covers_run` guard on starting and resuming a run returns
   402 below `minimum_run_balance_usd`. It checks once per start or resume, not per
   step, and charges have no floor, so a run can take the balance below zero.
3. `GenerateTextStepService.complete_step` prices the step (`CreditUtils`), stores its
   `charge_usd`, and calls `GenerateTextCreditService.charge_step`: a `CHARGE` row, a
   lower balance and a higher run `charge_usd`, in the step's transaction.
4. `GenerateTextRunService.fail_run` calls `refund_failed_run_segment`, which refunds
   every step after the run's last review step and lowers the run's `charge_usd`.
5. Once per step: `complete_step` charges only when it moves the step out of `RUNNING`,
   a partial unique index allows one `CHARGE` and one `REFUND` per step, and
   `refund_charges` skips charges already refunded.
6. Balances change by a SQL expression (`balance + amount`), not read and rewritten.
   `complete_step` and `fail_run` lock the run row first, so a late completion can't
   charge a failed run. Credit services never commit; the caller's transaction does.
7. `GET /users/me` returns `is_credit_balance_low`: the balance is below
   `low_balance_threshold_usd`.

## Services

- `CreditLedgerService`: the only writer of ledger rows and the balance column.
- `CreditValidationService`: the balance check the run guard calls.
- `CreditUtils`: the step price (cost × `markup_multiplier`) and the low-balance check.
- `CreditSettings` (`credits` in app settings): markup, run minimum, low threshold.
- `GenerateTextCreditService` (`libs/generate_text/`): charges and refunds run steps.
- `AdminCreditService` (`libs/admin/`): admin grants and the user's ledger page, at
  `/admin/users/{user_identity}/credit-grants` and `/credit-ledger`.
- `psg_credit_ledger` (`CreditLedgerOrm`) and `psg_user.credit_balance_usd`.

## Ledger entries

- `GRANT`: positive; an admin grant with a note, or an invite's (one per `invite_id`).
- `CHARGE`: negative; one completed step, with its run and step.
- `REFUND`: positive; reverses one `CHARGE`, with the same run and step.
- `ADJUSTMENT`: in the enum; nothing writes it yet.
