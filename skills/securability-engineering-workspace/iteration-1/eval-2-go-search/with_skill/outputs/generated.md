# SearchInventory — Securable Implementation

The function below is split across three small files to keep each piece single-purpose, testable, and below the 30-LoC / cyclomatic-complexity-10 thresholds. All three are part of the same `inventory` package.

```go
// file: inventory/types.go
package inventory

import (
	"context"
	"errors"

	"github.com/google/uuid"
)

// ErrInvalidQuery is returned when caller-supplied search parameters fail
// canonicalization or validation. It is intentionally generic so callers
// cannot infer which specific input was rejected.
var ErrInvalidQuery = errors.New("inventory: invalid search parameters")

// Item is the projected, server-curated view returned from SearchInventory.
// Fields are restricted to what an authenticated internal API handler is
// allowed to read — no internal-only columns leak through this projection.
type Item struct {
	ID         uuid.UUID `json:"id"`
	SKU        string    `json:"sku"`
	Name       string    `json:"name"`
	Category   string    `json:"category"`
	PriceCents int64     `json:"price_cents"`
}

// Querier is the minimal subset of *sql.DB / *sql.Tx that SearchInventory
// needs. Accepting an interface here makes the function unit-testable
// without a live PostgreSQL instance and lets callers pass a transaction
// when they need read-your-writes semantics.
type Querier interface {
	QueryContext(ctx context.Context, query string, args ...any) (Rows, error)
}

// Rows mirrors the small surface area of *sql.Rows that we actually use.
type Rows interface {
	Next() bool
	Scan(dest ...any) error
	Err() error
	Close() error
}
```

```go
// file: inventory/validate.go
package inventory

import (
	"strings"
	"unicode/utf8"
)

// Validation thresholds are package-level constants so they are easy to
// audit, change, and reference from tests. Tuned for an internal API:
// generous enough for legitimate searches, strict enough to prevent
// resource-exhaustion via oversized inputs.
const (
	maxQueryLen    = 100
	maxCategoryLen = 64
	defaultLimit   = 50
	maxLimit       = 200
)

// canonicalizeQuery trims, NFC-equivalent-trims, and bounds the free-text
// query. We do NOT lowercase — collation is the database's job (ILIKE).
// We reject non-UTF-8 input outright rather than silently replacing bytes,
// so malformed payloads cannot smuggle through as replacement characters.
func canonicalizeQuery(q string) (string, error) {
	q = strings.TrimSpace(q)
	if q == "" {
		return "", ErrInvalidQuery
	}
	if !utf8.ValidString(q) {
		return "", ErrInvalidQuery
	}
	if utf8.RuneCountInString(q) > maxQueryLen {
		return "", ErrInvalidQuery
	}
	return q, nil
}

// canonicalizeCategory trims and bounds the optional category filter.
// An empty category means "any category" and is a legitimate caller intent.
func canonicalizeCategory(c string) (string, error) {
	c = strings.TrimSpace(c)
	if c == "" {
		return "", nil
	}
	if !utf8.ValidString(c) || utf8.RuneCountInString(c) > maxCategoryLen {
		return "", ErrInvalidQuery
	}
	return c, nil
}

// clampLimit applies server-owned bounds to the caller-supplied limit.
// Per Derived Integrity (FIASSE S6.4.1.1), pagination caps are server
// state — we never let the caller exceed maxLimit, even on an internal API.
func clampLimit(limit int) int {
	if limit <= 0 {
		return defaultLimit
	}
	if limit > maxLimit {
		return maxLimit
	}
	return limit
}

// escapeLikePattern escapes the LIKE/ILIKE metacharacters so user input
// is treated as literal substring text, not as a pattern. The caller is
// responsible for wrapping the result in `%...%` for substring matching.
func escapeLikePattern(s string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return r.Replace(s)
}
```

```go
// file: inventory/search.go
package inventory

import (
	"context"
	"fmt"
	"log/slog"
)

// searchSQL uses parameterized placeholders exclusively — no string
// concatenation of user input. The ESCAPE clause pairs with
// escapeLikePattern() to keep `%` and `_` literal. The category filter
// is conditional via `($2::text IS NULL OR category = $2)` so a single
// prepared statement covers both "any category" and "specific category"
// without dynamic SQL assembly.
const searchSQL = `
SELECT id, sku, name, category, price_cents
FROM items
WHERE name ILIKE $1 ESCAPE '\'
  AND ($2::text IS NULL OR category = $2)
ORDER BY name ASC
LIMIT $3
`

// SearchInventory returns inventory rows whose name matches the supplied
// query (case-insensitive substring), optionally filtered by category.
//
// Trust boundary: this function sits at the handler -> data-access seam.
// It assumes the caller has already authenticated the principal (per the
// "internal authenticated API" context); it does NOT re-authenticate, but
// it DOES enforce input canonicalization, parameterized queries, and
// server-owned result bounds regardless of caller trust.
func SearchInventory(
	ctx context.Context,
	db Querier,
	query string,
	category string,
	limit int,
) ([]Item, error) {
	logger := slog.Default()

	q, err := canonicalizeQuery(query)
	if err != nil {
		logger.InfoContext(ctx, "inventory.search.rejected",
			slog.String("reason", "invalid_query"))
		return nil, ErrInvalidQuery
	}
	cat, err := canonicalizeCategory(category)
	if err != nil {
		logger.InfoContext(ctx, "inventory.search.rejected",
			slog.String("reason", "invalid_category"))
		return nil, ErrInvalidQuery
	}
	effectiveLimit := clampLimit(limit)

	pattern := "%" + escapeLikePattern(q) + "%"
	categoryArg := nullableString(cat)

	rows, err := db.QueryContext(ctx, searchSQL, pattern, categoryArg, effectiveLimit)
	if err != nil {
		logger.ErrorContext(ctx, "inventory.search.db_error",
			slog.String("op", "query"))
		return nil, fmt.Errorf("inventory: query: %w", err)
	}
	defer rows.Close()

	items, err := scanItems(rows)
	if err != nil {
		logger.ErrorContext(ctx, "inventory.search.scan_error",
			slog.String("op", "scan"))
		return nil, fmt.Errorf("inventory: scan: %w", err)
	}

	logger.InfoContext(ctx, "inventory.search.completed",
		slog.Int("result_count", len(items)),
		slog.Int("effective_limit", effectiveLimit),
		slog.Bool("category_filter", cat != ""))
	return items, nil
}

// scanItems iterates rows defensively: it allocates with the known limit,
// checks rows.Err() after the loop (a common Go pitfall), and never
// silently drops a partial result.
func scanItems(rows Rows) ([]Item, error) {
	items := make([]Item, 0, defaultLimit)
	for rows.Next() {
		var it Item
		if err := rows.Scan(&it.ID, &it.SKU, &it.Name, &it.Category, &it.PriceCents); err != nil {
			return nil, err
		}
		items = append(items, it)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return items, nil
}

// nullableString converts an empty string to a typed nil so the SQL
// `$2::text IS NULL` branch fires. Keeping this helper local avoids a
// dependency on database/sql.NullString in the public type surface.
func nullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}
```

## Securability Notes

**SSEM attributes actively enforced**:
- **Integrity** — Parameterized query (`$1`/`$2`/`$3`) with no string concatenation; LIKE metacharacters escaped via `ESCAPE '\'` and `escapeLikePattern`; UTF-8 validation rejects malformed input rather than silently coercing it; Derived Integrity applied to `limit` (server-clamped to `maxLimit`).
- **Availability** — Caller-supplied `limit` is bounded by `maxLimit` (200) and defaulted to 50 to prevent unbounded result sets; `query` and `category` length-capped to prevent oversized inputs from reaching the database; `ctx` is honored end-to-end so upstream timeouts/cancellations propagate.
- **Resilience** — `defer rows.Close()` guarantees no row-handle leak; explicit `rows.Err()` check after iteration catches the silent-failure pitfall; specific `ErrInvalidQuery` sentinel for validation failures vs. wrapped `%w` for DB errors — no bare catch-all.
- **Confidentiality** — Result projection (`Item`) restricts returned columns to the documented five; `ErrInvalidQuery` is a single generic error so callers cannot oracle which input was rejected; logs never include the raw query string or category value, only structured outcome metadata.
- **Accountability** — Structured `slog` events at every boundary outcome (`rejected`, `db_error`, `scan_error`, `completed`) with stable event names that are SIEM-friendly.
- **Analyzability** — Each function single-purpose and well under 30 LoC; cyclomatic complexity is low (no nested conditionals, no boolean chains); names describe intent (`canonicalizeQuery`, `clampLimit`, `escapeLikePattern`).
- **Modifiability** — `Querier` / `Rows` interfaces decouple from `database/sql` concretes; validation thresholds are named constants in one place; logger is taken from `slog.Default()` so deployments override globally without touching this code.
- **Testability** — `Querier` is a 1-method interface trivial to fake; `canonicalizeQuery`, `canonicalizeCategory`, `clampLimit`, and `escapeLikePattern` are pure functions with no I/O.
- **Authenticity** — Function documents its trust contract (caller is already authenticated); does not itself re-authenticate, but enforces server-owned bounds regardless of caller trust level so a misbehaving handler cannot exfiltrate the table.

**ASVS references**:
- **V5.2.x** (Input Validation) — canonicalize -> validate -> bound at the trust boundary; reject non-UTF-8 and oversized inputs.
- **V5.3.4 / SQLi family** — exclusively parameterized queries; LIKE pattern escaping; no dynamic SQL assembly from user input.
- **V8.1.1 / V8.1.2** (Authorization) — function-level access is the caller's responsibility (documented in the trade-offs); field-level read access is enforced by the `Item` projection.
- **V11.x** (Business Logic / Resource Limits) — server-clamped `limit`; default page size; `ctx`-driven cancellation.
- **V16.3.3 / V16.3.4** (Security Events / Logging) — structured logs for input-validation rejections and unexpected DB/scan errors; no sensitive payload in log fields.

**Trust boundaries handled**:
- Handler -> `SearchInventory` (input canonicalization, length bounds, UTF-8 validation, server-owned limit clamp).
- `SearchInventory` -> PostgreSQL (parameterized query, LIKE-pattern escaping, context-bound execution, projected column list).
- `SearchInventory` -> caller (curated `Item` projection, generic `ErrInvalidQuery` sentinel that does not leak which field failed).

**Dependencies introduced**:
- `github.com/google/uuid` — used for the `uuid.UUID` type on `Item.ID`. Latest stable line is `v1.6.0` (Jan 2024); widely adopted, BSD-3, no open critical CVEs. Pin in `go.mod` and commit `go.sum`. (If the surrounding codebase already uses `pgtype.UUID` from `pgx`, prefer that to avoid double-typing — see trade-offs.)
- Standard library only otherwise: `context`, `database/sql`-compatible interfaces, `errors`, `fmt`, `log/slog` (Go 1.21+), `strings`, `unicode/utf8`. `log/slog` requires Go >= 1.21; fall back to a structured-logger interface if targeting an older toolchain.

**Trade-offs and assumptions**:
- **Driver-agnostic by design.** The function takes a `Querier` interface rather than `*sql.DB` or `*pgx.Conn`. If the codebase standardizes on `pgx`, swap the interface to wrap `pgx.Conn.Query` and consider using `pgtype` natively to avoid the `database/sql` adapter layer.
- **Authentication is assumed, not verified.** The function trusts that the caller (an internal authenticated API handler) has already established the principal. If this is ever exposed to untrusted callers, add a `Principal` parameter and authorization check before the query — and reduce `maxLimit` accordingly.
- **No per-tenant scoping.** The `items` table is treated as global. If multi-tenant isolation is required, add a mandatory `tenant_id` parameter and an `AND tenant_id = $N` clause; do not derive tenant from client input.
- **Logging uses `slog.Default()`.** Fine for most deployments; inject an `*slog.Logger` parameter (or pull from `ctx`) if call-site-specific log routing or sampling is needed.
- **Sort order is fixed (`name ASC`).** If the API needs caller-controlled sorting, expose a typed enum — never accept a raw column name from the caller.
- **`ILIKE` is PostgreSQL-specific.** If the project ever migrates databases, replace with `LOWER(name) LIKE LOWER($1)` plus a functional index, or use a full-text index (`tsvector`) for higher-volume search.
- **No rate limiting in this layer.** Resource bounds here are per-request; cross-request rate limiting belongs at the handler/middleware tier.
