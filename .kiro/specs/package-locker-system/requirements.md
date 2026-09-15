# Requirements — Smart Package Locker Management System

Derived from the Everest Engineering coding challenge (Levels 1–4) plus user
interface and deployment requirements. Acceptance criteria use EARS notation
(WHEN / IF … THE SYSTEM SHALL …).

## Roles

- **System User (Admin)** — creates and manages lockers, views the notification/transaction log. Desktop.
- **Delivery Agent** — stores packages, receives a pickup code and locker identifier. Mobile.
- **Customer** — retrieves packages using a locker identifier + pickup code. Mobile.

---

## Requirement 1: Locker management (Admin)

**User story:** As a system user, I want to create and manage lockers of different sizes, so that delivery agents have somewhere to store packages.

1. THE SYSTEM SHALL support creating lockers of sizes Small, Medium, and Large.
2. THE SYSTEM SHALL assign each locker a human-readable identifier that groups by size and increments per size (e.g. `S-001`, `M-001`, `L-001`).
3. WHEN a locker is created THE SYSTEM SHALL mark it available.
4. THE SYSTEM SHALL allow viewing the list of lockers with their size and current status.
5. THE SYSTEM SHALL be designed so new locker sizes can be added without rewriting allocation logic (allocation reads a size ordering, not literals).

---

## Requirement 2: Locker size specification (dimensions & volume)

**User story:** As any user, I want to know each locker's physical size, so that I can judge what fits.

1. THE SYSTEM SHALL define, per size, interior dimensions (width × depth × height in cm) and a derived interior volume (litres) as a single source of truth.
2. THE SYSTEM SHALL expose the size catalogue — dimensions, volume, and a plain-language fit hint — via a read endpoint.
3. THE SYSTEM SHALL include each locker's dimensions in its representation returned by the locker list.
4. THE SYSTEM SHALL compute volume from dimensions rather than storing it independently.
5. THE SYSTEM SHALL let the UI read the size spec from the API so no dimension data is hardcoded client-side.

---

## Requirement 3: Store a package — two-phase (Delivery Agent) — Level 1

**User story:** As a delivery agent, I want to reserve a locker, physically place the package, then confirm, so that a locker isn't finalized before the package is actually inside.

1. WHEN an agent requests storage for a package of size S THE SYSTEM SHALL select an available locker whose size is ≥ S.
2. WHEN more than one available locker fits THE SYSTEM SHALL reserve the **smallest** fitting locker (ties broken deterministically by identifier).
3. WHEN a locker is reserved (phase 1, "hold") THE SYSTEM SHALL set it to HELD, create a pending package with a unique pickup code, and return the package id, locker id, and pickup code ("door open").
4. IF no suitable locker is available THEN THE SYSTEM SHALL return a result indicating the package cannot be stored, with a human-readable message (not an error/exception).
5. WHEN the agent confirms placement (phase 2, "complete") THE SYSTEM SHALL move the package to STORED, set the locker to OCCUPIED, and record the storage start time (the charge clock starts here, not at hold).
6. WHEN the agent cancels before confirming THE SYSTEM SHALL discard the pending package and return the locker to AVAILABLE.
7. THE SYSTEM SHALL ensure each stored package has a unique pickup code associated with exactly one package and locker.
8. THE SYSTEM SHALL store at most one package per locker at a time.

---

## Requirement 4: Hold expiry (abandoned reservations)

**User story:** As the business, I want unconfirmed reservations to auto-release, so that a locker isn't held forever if an agent walks away.

1. THE SYSTEM SHALL treat a pending (held-but-not-confirmed) package older than a configurable timeout as expired.
2. WHEN an expiry sweep runs THE SYSTEM SHALL discard each expired pending package and return its locker from HELD to AVAILABLE, recording a log entry.
3. THE SYSTEM SHALL run the sweep lazily at the start of hold/list operations, requiring no background thread.
4. IF the configured timeout is zero THEN THE SYSTEM SHALL disable expiry.
5. IF an agent attempts to confirm a hold that has already expired THEN THE SYSTEM SHALL reject it cleanly with a message.
6. WHEN expiry runs under concurrency THE SYSTEM SHALL release each expired hold exactly once (guarded, no double-processing).

---

## Requirement 5: Retrieve a package — two-phase (Customer) — Level 2

**User story:** As a customer, I want to unlock my locker with my locker ID and pickup code, take my package, then confirm the door is shut, so that the locker isn't reused while physically open.

1. WHEN a customer provides a locker identifier and pickup code matching a STORED package THE SYSTEM SHALL unlock that locker (phase 1, "open"), set it to OPEN, mark the package RETRIEVED, and finalize the charge.
2. WHEN a locker is opened for pickup THE SYSTEM SHALL NOT make it reusable until the customer confirms the door is shut.
3. WHEN the customer confirms closure (phase 2, "close") THE SYSTEM SHALL return the locker from OPEN to AVAILABLE.
4. IF the locker identifier and pickup code do not match a stored package THEN THE SYSTEM SHALL reject the request with a clear message and unlock nothing.
5. IF a pickup code is reused after retrieval THEN THE SYSTEM SHALL reject it.
6. IF a close is attempted on a locker that is not open THEN THE SYSTEM SHALL reject it with a message.

---

## Requirement 6: Storage charges — Level 3

**User story:** As the business, I want tiered storage charges based on how long a package stays, so that lockers turn over.

1. WHEN a package is stored THE SYSTEM SHALL record the storage start time.
2. WHEN a package is retrieved THE SYSTEM SHALL calculate the total charge from the duration it remained in the locker.
3. THE SYSTEM SHALL apply a tiered rule: X/day for days 1–5, 2X/day for days 6–10, and 3X/day for day 11 onward, where X is a fixed configurable value.
4. THE SYSTEM SHALL treat one day as 24 hours from the storage start time, and SHALL count any partial day as a full day (round up).
5. WHEN a package is retrieved THE SYSTEM SHALL return the storage charge together with the pickup confirmation.
6. WHEN a package is retrieved THE SYSTEM SHALL also return an audit of the charge basis: the storage start time, retrieval time, and the number of billable days.
7. WHEN a package is retrieved THE SYSTEM SHALL make the locker available again (via the close step in Requirement 5).

---

## Requirement 7: Concurrent storage requests — Level 4

**User story:** As the business, I want correct behavior when multiple agents store packages at once, so that no two packages ever get the same locker.

1. WHEN multiple storage requests occur simultaneously THE SYSTEM SHALL assign each locker to at most one package.
2. WHEN two requests contend for the same locker THE SYSTEM SHALL grant it to exactly one; the other SHALL retry the next candidate or be rejected.
3. THE SYSTEM SHALL keep locker availability correct and up to date under concurrency.
4. IF there are more requests than available lockers THEN THE SYSTEM SHALL assign only the available lockers and return a "no suitable locker available" message to the remainder.
5. THE SYSTEM SHALL behave correctly when contention crosses size boundaries (a smaller package may claim a larger locker under the smallest-fit rule).
6. THE SYSTEM SHALL continue to behave correctly under sustained concurrent load.

---

## Requirement 8: Notification subsystem & transaction log (Admin)

**User story:** As a system user, I want a log of all transactions and notifications, so that I can audit activity and pickup-code delivery.

1. THE SYSTEM SHALL record a log entry for every store attempt and its outcome (hold success/failure, store success, cancel, expiry).
2. THE SYSTEM SHALL record a log entry for every pickup attempt and its outcome (success/failure, close).
3. WHEN a pickup code is "sent" THE SYSTEM SHALL record the send with an outcome (real SMS/email is out of scope; the POC logs intent + outcome).
4. THE SYSTEM SHALL expose the transaction log to the admin view, most recent first.
5. THE SYSTEM SHALL implement notification sending behind a swappable interface so a real provider can replace the logger without changing callers.
6. THE SYSTEM SHALL record, on each log row where applicable, the associated locker id and package id.

---

## Requirement 9: User interfaces

**User story:** As each role, I want a view suited to my task and device.

### 9a. Admin (master system view, desktop)
1. THE SYSTEM SHALL provide a locker creation control that shows each size's dimensions and volume.
2. THE SYSTEM SHALL render a visual locker map grouped by size (small→large), with footprint scaled by size and color encoding status.
3. THE SYSTEM SHALL render a locker table including id, size, dimensions, volume, and status.
4. THE SYSTEM SHALL render the transaction log, newest first, auto-refreshing.

### 9b. Delivery Agent (mobile)
1. THE SYSTEM SHALL default to a (simulated) incoming package of a random size on load.
2. THE SYSTEM SHALL recommend the smallest available locker that fits the current package, computed from live availability.
3. THE SYSTEM SHALL provide a control to change the package, which re-rolls the size and updates the recommendation.
4. IF no locker fits the current package THEN THE SYSTEM SHALL clearly indicate this and disable the store action.
5. WHEN a locker is created or freed elsewhere THE SYSTEM SHALL update the recommendation live.
6. THE SYSTEM SHALL walk the agent through the two-phase store (open → confirm/cancel) and display the pickup code with a copy control.

### 9c. Customer (mobile)
1. THE SYSTEM SHALL present available lockers awaiting pickup as a visual selection (no manual locker-number typing), arranged like the admin locker map (grouped by size, footprint scaled).
2. THE SYSTEM SHALL require only the pickup code once a locker is selected, and keep the unlock action disabled until both are provided.
3. THE SYSTEM SHALL walk the customer through the two-phase pickup (unlock → confirm door closed).
4. WHEN a package is retrieved THE SYSTEM SHALL display the storage charge and its billable-day basis.
5. THE SYSTEM SHALL keep the selectable locker set current and clear a stale selection if that locker is no longer pickable.

### 9d. Shared
1. THE SYSTEM SHALL expose all operations via REST so the UI and any other client share one contract.
2. THE SYSTEM SHALL provide a landing page linking to all three views and to the API docs (opening in a new tab).

---

## Requirement 10: Invalid scenarios & errors

1. THE SYSTEM SHALL handle invalid scenarios with clear responses: unknown locker, wrong code, empty/again-retrieved package, confirming/canceling a nonexistent hold, closing a non-open locker.
2. THE SYSTEM SHALL validate package/locker size and reject unknown sizes.
3. THE SYSTEM SHALL keep unmatched API paths as JSON errors (not the SPA shell) so clients get correct 404s.

---

## Requirement 11: Deployment & operations

**User story:** As an operator, I want to build locally, publish to a registry, and run on Ubuntu with Docker.

1. THE SYSTEM SHALL build into a single Docker image containing the API and the built UI.
2. THE SYSTEM SHALL serve the SPA and the API from one process on one port, with client-side routing fallback.
3. THE SYSTEM SHALL run the container as a non-root user.
4. THE SYSTEM SHALL store its database under a declared volume path so data can persist across restarts when a volume is mounted.
5. THE SYSTEM SHALL expose a health endpoint used by a container healthcheck.
6. THE SYSTEM SHALL be publishable to a public container registry and runnable on Ubuntu with a single `docker run` exposing one port.
7. THE SYSTEM SHALL document build, run, and deploy steps.

---

## Requirement 12: Configuration

1. THE SYSTEM SHALL read all configuration from environment variables with sensible defaults so it runs with zero setup.
2. THE SYSTEM SHALL support: `DATABASE_URL` (DB connection), `STORAGE_UNIT_RATE` (X in the charge rule), `HOLD_TIMEOUT_SECONDS` (0 disables expiry), and `PORT`.
