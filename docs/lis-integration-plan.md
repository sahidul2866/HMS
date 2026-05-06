# HMS LIS Integration Plan (Step-by-Step)

## 1) Canonicalize Source

- Use only `LIS/LIS_CPH_Code` as source of truth.
- Keep protocol references in `LIS/LIS_Protocol`.
- Do not run analyzer scripts directly from random folders in production.

## 2) Define Unified LIS Bridge Module

Create a new backend module:

- `backend/app/modules/lis/`
  - `router.py`
  - `service.py`
  - `repository.py`
  - `schemas.py`
  - `adapters/` (one adapter per analyzer family)

Target behavior:

- Single API for:
  - order dispatch to analyzer
  - result ingest
  - ACK/NACK tracking
  - retry and dead-letter handling

## 3) Data Model (Minimum)

Add LIS tables via migration:

- `lis_analyzers`
  - analyzer code, type, host, port, protocol (`HL7/ASTM/TCP/Serial`)
- `lis_test_code_map`
  - analyzer test code ↔ HMS lab test/analyte mapping
- `lis_order_outbox`
  - pending/sent/acknowledged order messages
- `lis_result_inbox`
  - raw inbound payload + parse status
- `lis_result_items`
  - normalized result rows (test/analyte/value/unit/flag/ref range)
- `lis_message_log`
  - request/response audit trail with timestamps

## 4) Adapter Strategy

Wrap each machine script under adapter interface:

- `prepare_order_payload(order_context)`
- `send_order(payload)`
- `receive_result(raw_payload)`
- `parse_result(raw_payload) -> normalized rows`
- `health_check()`

Start with top priority analyzers in your current demo flow:

1. `XN_1000`
2. `ATELICA_SOLUTION`
3. `URISED_3`
4. `D_10`

## 5) HMS Workflow Wiring

- When billing includes lab item and order is confirmed:
  - create `lab_orders` / `lab_order_items`
  - enqueue into `lis_order_outbox`
- Background worker sends messages by analyzer adapter.
- Incoming results:
  - store raw payload
  - parse to normalized items
  - write to `lab_results` and `lab_result_items`
  - update dashboard/workbench status.

## 6) Safety and Operations

- Add strict per-analyzer config in DB + admin UI (not hardcoded files).
- Add retry policy + idempotency key by specimen/order.
- Add alerting for:
  - ACK timeout
  - parse failure
  - unknown test code mapping
- Log PHI carefully; avoid dumping full payloads in plain logs in production.

## 7) Cutover Plan

Phase A (Readiness):
- implement tables + adapter scaffold + dry-run parse.

Phase B (Shadow):
- receive results from analyzers and compare with current process (no auto-post).

Phase C (Controlled Live):
- enable selected analyzers for live posting.

Phase D (Full Live):
- all supported analyzers routed through LIS module.

## 8) Immediate Next Tasks

1. Create `backend/app/modules/lis/` scaffold.
2. Add migration for LIS tables.
3. Implement adapter for one analyzer (`XN_1000`) end-to-end.
4. Add admin API for analyzer config + code map.
5. Add one integration test for order→result pipeline.
