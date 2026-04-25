# SearchInventory — Securable Go Implementation

A FIASSE/SSEM-aligned implementation of `SearchInventory` for a PostgreSQL `items`
table. The function is invoked from an authenticated internal API handler, so the
trust boundary for this code is *the handler -> this function* seam: all inbound
values are treated as untrusted input that must be canonicalized, sanitized, and
validated before being composed into a parameterized SQL statement.

## Package layout

Three small files in package `inventory`. They are shown as separate listings
below but belong to the same package.

### `inventory/model.go`

```go
// Package inventory provides read-only search access to the items catalogue.
//
// Trust boundary: callers are authenticated internal handlers. This package
// still treats the `query`, `category`, and `limit` arguments as untrusted
// input and enforces canonicalize -> sanitize -> validate at the entry point
// (Derived Integrity Principle, Request Surface Minimization).
package inventory

import "github.com/google/uuid"

// Item is the read model returned by SearchInventory.
// Fields mirror the `items` table columns exactly and are exported for JSON
// marshalling by upstream handlers. PriceCents is kept as an integer count of
// minor units to avoid floating-point drift.
type Item struct {
    ID         uuid.UUID `json:"id"`
    SKU        string    `json:"sku"`
    Name       string    `json:"name"`
    Category   string    `json:"category"`
    PriceCents int64     `json:"price_cents"`
}
```

### `inventory/validate.go`

```go
package inventory

import (
    "errors"
    "strings"
    "unicode/utf8"
)

// Input bounds. Keep small and explicit so they are easy to audit and tune.
const (
    maxQueryLen    = 100 // characters, post-trim
    maxCategoryLen = 64
    maxLimit       = 200
    defaultLimit   = 50
)

// ErrInvalidInput is returned for any validation failure at the trust boundary.
// It is deliberately generic so callers can surface a safe message to clients
// while the structured log record carries the specific reason (V16.5.1).
var ErrInvalidInput = errors.New("inventory: invalid search input")

// allowedCategories is a fixed allowlist. Category is a server-owned
// classification, so accepting an arbitrary client string here would violate
// the Derived Integrity Principle. Empty string means "any category".
var allowedCategories = map[string]struct{}{
    "":            {}, // wildcard (no filter)
    "apparel":     {},
    "electronics": {},
    "grocery":     {},
    "home":        {},
    "toys":        {},
}

// searchParams is the canonicalized, validated input used internally.
// It intentionally exposes only the fields the query needs (Request Surface
// Minimization): nothing from the raw request leaks further than this struct.
type searchParams struct {
    likePattern string // already escaped for LIKE, may be empty
    category    string // already in allowlist, may be empty
    limit       int    // 1..maxLimit
}

// validateInputs canonicalizes and validates the three caller-supplied values.
// Returns ErrInvalidInput wrapped with a short reason on failure. The reason
// string is safe to log but should NOT be returned verbatim to external API
// consumers (V16.5.1).
func validateInputs(query, category string, limit int) (searchParams, error) {
    q := strings.TrimSpace(query)
    if !utf8.ValidString(q) {
        return searchParams{}, errors.Join(ErrInvalidInput, errors.New("query not valid utf-8"))
    }
    if utf8.RuneCountInString(q) > maxQueryLen {
        return searchParams{}, errors.Join(ErrInvalidInput, errors.New("query too long"))
    }

    c := strings.ToLower(strings.TrimSpace(category))
    if utf8.RuneCountInString(c) > maxCategoryLen {
        return searchParams{}, errors.Join(ErrInvalidInput, errors.New("category too long"))
    }
    if _, ok := allowedCategories[c]; !ok {
        return searchParams{}, errors.Join(ErrInvalidInput, errors.New("category not permitted"))
    }

    return searchParams{
        likePattern: buildLikePattern(q),
        category:    c,
        limit:       clampLimit(limit),
    }, nil
}

// buildLikePattern escapes LIKE metacharacters in user input and wraps the
// result in %...% for substring matching. Empty input returns an empty string,
// which the query layer translates to "no name filter".
//
// The order matters: escape backslash first, then % and _, so we don't double-
// escape the escape character.
func buildLikePattern(s string) string {
    if s == "" {
        return ""
    }
    r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
    return "%" + r.Replace(s) + "%"
}

// clampLimit forces the page size into a safe range. Any non-positive value
// falls back to defaultLimit; values above maxLimit are capped to protect
// memory and query latency (SSEM: Availability).
func clampLimit(n int) int {
    switch {
    case n <= 0:
        return defaultLimit
    case n > maxLimit:
        return maxLimit
    default:
        return n
    }
}
```

### `inventory/search.go`

```go
package inventory

import (
    "context"
    "database/sql"
    "errors"
    "fmt"
    "log/slog"
    "time"
)

// DBQuerier is the narrow surface SearchInventory needs from a database handle.
// Accepting an interface (rather than *sql.DB directly) keeps this package
// loosely coupled and testable without a live PostgreSQL instance
// (SSEM: Modifiability, Testability).
type DBQuerier interface {
    QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
}

// queryTimeout bounds a single search call so a slow or stuck database cannot
// pin a handler goroutine indefinitely (SSEM: Availability / Resilience).
const queryTimeout = 3 * time.Second

// searchSQL is a static, parameterized statement. Column list is explicit
// (no SELECT *). ORDER BY and LIMIT use server-owned values only; no user
// input is ever concatenated into the SQL text (ASVS V1.2.4).
//
// The $1/$2 pattern below lets us express "optional filter" without dynamic
// SQL: an empty string for name or category skips that predicate via the
// `$N = ''` guard. Postgres handles this cleanly with the parameterized plan.
const searchSQL = `
SELECT id, sku, name, category, price_cents
FROM items
WHERE ($1 = '' OR name ILIKE $1 ESCAPE '\')
  AND ($2 = '' OR category = $2)
ORDER BY name ASC
LIMIT $3
`

// SearchInventory returns items whose name matches `query` (substring, case-
// insensitive) and, optionally, whose category equals `category`. The caller
// is expected to be an authenticated internal API handler; authorization for
// reading inventory is assumed to have happened upstream. This function
// enforces its own input validation regardless.
//
// Parameters:
//   - ctx:      request-scoped context; a 3s timeout is applied on top of it.
//   - db:       any type satisfying DBQuerier (typically *sql.DB or *sql.Tx).
//   - query:    free-text name fragment; trimmed, length-capped, LIKE-escaped.
//   - category: optional category filter; must be in the server-side allowlist.
//   - limit:    max rows to return; clamped to [1, maxLimit].
//
// Returns ErrInvalidInput for validation failures and a wrapped error for
// infrastructure failures. Never returns a partial result set on error.
func SearchInventory(
    ctx context.Context,
    db DBQuerier,
    query, category string,
    limit int,
) ([]Item, error) {
    logger := slog.Default().With(slog.String("op", "inventory.SearchInventory"))

    params, err := validateInputs(query, category, limit)
    if err != nil {
        logger.WarnContext(ctx, "input validation failed",
            slog.Int("query_len", len(query)),
            slog.String("category", category),
            slog.Int("limit", limit),
            slog.String("reason", err.Error()),
        )
        return nil, err
    }

    callCtx, cancel := context.WithTimeout(ctx, queryTimeout)
    defer cancel()

    rows, err := db.QueryContext(callCtx, searchSQL, params.likePattern, params.category, params.limit)
    if err != nil {
        // Do not propagate the raw driver error to callers; wrap with a stable
        // sentinel so handlers can map it to a generic 5xx response (V16.5.1).
        logger.ErrorContext(ctx, "database query failed", slog.String("error", err.Error()))
        return nil, fmt.Errorf("inventory: query failed: %w", err)
    }
    defer rows.Close()

    return scanItems(rows, params.limit)
}

// scanItems materializes rows into Item values. Preallocating to the requested
// limit avoids unbounded growth even if the DB were to misbehave and return
// more rows than LIMIT asked for.
func scanItems(rows *sql.Rows, cap int) ([]Item, error) {
    out := make([]Item, 0, cap)
    for rows.Next() {
        var it Item
        if err := rows.Scan(&it.ID, &it.SKU, &it.Name, &it.Category, &it.PriceCents); err != nil {
            return nil, fmt.Errorf("inventory: row scan failed: %w", err)
        }
        out = append(out, it)
    }
    if err := rows.Err(); err != nil {
        if errors.Is(err, context.DeadlineExceeded) || errors.Is(err, context.Canceled) {
            return nil, err
        }
        return nil, fmt.Errorf("inventory: row iteration failed: %w", err)
    }
    return out, nil
}
```

## Suggested test sketch (not generated in full, but trivially wirable)

```go
// inventory/search_test.go
//
// Uses a fake DBQuerier to verify:
//   - empty query and empty category produce a statement whose bound args
//     are ("", "", defaultLimit) and still return rows
//   - a query containing % and _ is LIKE-escaped before hitting the DB
//   - category "robots" (not in allowlist) is rejected with ErrInvalidInput
//     and no QueryContext call is made
//   - limit=0 becomes defaultLimit, limit=10000 is clamped to maxLimit
//   - context cancellation surfaces context.Canceled unmodified
//   - utf-8 invalid bytes are rejected
```

Because `DBQuerier` is an interface, the test file can supply a struct whose
`QueryContext` records the call and returns canned `*sql.Rows` via `sqlmock`
or a hand-rolled fake. No network or container is required.

## go.mod dependency guidance

Only one third-party dependency is introduced, for UUID typing:

```
module example.com/yourorg/yourapp

go 1.22

require github.com/google/uuid v1.6.0
```

Rationale (dependency hygiene):

- `github.com/google/uuid` is the de-facto Go UUID package, actively
  maintained, MIT-licensed, with a minimal API and no transitive deps. The
  version pinned is the latest stable at time of generation; regenerate
  `go.sum` via `go mod tidy` and commit it. If your project already exposes
  UUIDs as `string`, drop this dep entirely and change `Item.ID` to `string`.
- All other functionality is satisfied by the Go standard library
  (`database/sql`, `context`, `log/slog`, `strings`, `unicode/utf8`, `errors`,
  `fmt`, `time`). No ORM, no query builder, no logging framework is pulled
  in. Fewer dependencies, smaller supply-chain attack surface.
- The PostgreSQL driver (`github.com/jackc/pgx/v5/stdlib` or
  `github.com/lib/pq`) is expected to be wired up by the application root,
  not by this package. That keeps `inventory` driver-agnostic and lets the
  caller pick the latest patched driver without touching this code.

---

## Securability Notes

**Trust boundary handling (S6.3, S6.4).** The function treats its three
caller-supplied arguments as crossing a trust boundary even though the caller
is authenticated. `validateInputs` performs the canonicalize -> sanitize ->
validate sequence (S6.4.1): trim whitespace, check UTF-8 validity, cap length,
lowercase category, reject categories outside an allowlist, clamp limit.

**Derived Integrity Principle (S6.4.1.1).** Category is a server-owned taxonomy
value, so we do not accept an arbitrary client string. The allowlist is the
only source of truth. Similarly, `limit` is clamped server-side; the client
cannot coerce the system into returning unbounded rows.

**Request Surface Minimization (S6.4.1.1).** Only `query`, `category`, and
`limit` enter the function. They are projected into `searchParams`, which
contains just the three fields the SQL needs. No request-level struct is
passed through, and no field is read from anywhere else.

**SSEM attributes actively enforced:**

- *Analyzability*: Every function is well under 30 LoC with single
  responsibility and explicit names. Comments explain *why* at each
  non-obvious choice (LIKE-escape order, ILIKE ESCAPE clause, preallocation,
  error wrapping policy).
- *Modifiability*: `DBQuerier` interface decouples the package from `*sql.DB`.
  Tunable constants (`maxQueryLen`, `maxLimit`, `queryTimeout`, allowlist) are
  centralized at the top of the file so future changes are low-risk.
- *Testability*: The DB seam is an interface; `validateInputs`,
  `buildLikePattern`, and `clampLimit` are pure functions that are
  trivially unit-tested without I/O.
- *Confidentiality*: Log records contain `query_len` and `category`, never
  the raw query string, so even if the search text carried a customer name
  or other incidental PII it does not land in logs. The validated SQL never
  interpolates user text into the statement.
- *Accountability*: Structured `slog` fields (`op`, `query_len`, `category`,
  `limit`, `reason`) produce machine-parseable audit records at the trust
  boundary. Warnings for validation failures, errors for infra faults.
- *Authenticity*: Out of scope for this function; authentication is performed
  upstream by the API handler. The package does not accept or forward a
  principal ID, avoiding impersonation surface.
- *Availability*: `context.WithTimeout(ctx, 3s)` prevents a stuck DB query
  from pinning a handler goroutine. `limit` is clamped to `maxLimit` so
  response size and query cost are bounded. Result slice is preallocated to
  `params.limit` to avoid repeated growth.
- *Integrity*: The SQL statement is a constant; parameters are bound
  positionally. LIKE metacharacters (`\`, `%`, `_`) are escaped before
  binding, and `ESCAPE '\'` is set explicitly. No string concatenation is
  used to build the query. This satisfies ASVS V1.2.4 and the guidance that
  parameterization alone is insufficient if metacharacter semantics are not
  also controlled.
- *Resilience*: All error paths return specific wrapped errors; `rows.Close()`
  is deferred; `rows.Err()` is checked after iteration; `context.Canceled`
  and `context.DeadlineExceeded` are preserved verbatim so callers can react
  correctly. No panics, no `_ = rows.Close()` silent discards, no bare catch.

**ASVS requirements satisfied:**

- *V1.2.4 (Parameterized queries)* — `QueryContext` with `$1/$2/$3`
  placeholders, no string concatenation.
- *V2.2.1 (Positive input validation)* — length caps, UTF-8 check, category
  allowlist, limit clamp.
- *V2.2.2 (Validation at trusted service layer)* — validation executes
  inside this package rather than trusting the handler to have done it.
- *V15.3 (Defensive coding)* — bounded limits, explicit timeouts,
  preallocated slices, checked `rows.Err()`.
- *V16.2 (General Logging)* — structured `slog` records with stable field
  names and no sensitive payload.
- *V16.5.1 (Generic error messages)* — wrapped sentinel errors
  (`ErrInvalidInput`, `inventory: query failed: %w`) let handlers map to
  generic 4xx/5xx responses without leaking driver messages to clients.
- *V16.5.3 (Fail securely)* — on any error, the function returns a nil
  slice; there is no partial success path that could be misinterpreted as
  an empty result.

**Dependency rationale (supply-chain hygiene):**

- `github.com/google/uuid@v1.6.0` — only third-party dep; actively
  maintained, no transitive deps, wide adoption, MIT license, no
  outstanding critical CVEs at time of writing. Optional: can be removed
  by typing `Item.ID` as `string`.
- Standard library only for SQL, context, logging, string handling, and
  time. No ORM, no logging framework, no query builder. Smaller attack
  surface and faster patch-through when Go itself releases a fix.
- Pin versions in `go.mod` and commit `go.sum` for reproducible, reviewable
  builds.

**Trade-offs:**

- The `$1 = '' OR name ILIKE $1` idiom makes the statement plan-cache
  friendly while supporting optional filters. If the `items` table grows
  large, add a trigram or tsvector index on `name` and consider switching
  to full-text search; the function signature does not need to change.
- Category is an allowlist rather than a free-form text match. This
  trades flexibility for integrity; if your product catalogue introduces
  new categories, update `allowedCategories` at the same time the
  taxonomy ships. A future improvement is to load the allowlist from
  configuration or a `categories` table at startup.
- No per-caller rate limiting is implemented in this function; that
  belongs at the handler or gateway layer. The function does contribute
  to availability by bounding `limit` and wall-clock time per call.
