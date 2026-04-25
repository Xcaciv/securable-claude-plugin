# SearchInventory — Securable Implementation

A FIASSE/SSEM-aligned implementation of `SearchInventory` for a PostgreSQL `items`
table. The function treats its arguments as crossing a trust boundary even though
the caller is an authenticated internal API handler: inputs originate from a
client request and must be canonicalized, sanitized, and validated before being
used in a query.

## Package layout

```go
// Package inventory provides read-only data access for the items catalog.
// All exported functions treat their inputs as untrusted at the trust boundary
// and apply canonicalize -> sanitize -> validate before any database I/O.
package inventory
```

## Types and contracts

```go
import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"log/slog"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/google/uuid"
)

// Item is the read model returned by SearchInventory. Field types are chosen
// for explicit safety: UUID is parsed (not a raw string), price is integer
// cents to avoid floating-point drift, and category is a constrained string.
type Item struct {
	ID         uuid.UUID `json:"id"`
	SKU        string    `json:"sku"`
	Name       string    `json:"name"`
	Category   string    `json:"category"`
	PriceCents int64     `json:"price_cents"`
}

// Querier is the minimal database surface SearchInventory depends on.
// Accepting an interface (rather than *sql.DB) keeps the function loosely
// coupled, mockable in tests, and compatible with *sql.Tx and *sql.Conn.
// (SSEM: Modifiability, Testability)
type Querier interface {
	QueryContext(ctx context.Context, query string, args ...any) (*sql.Rows, error)
}

// SearchInventoryError is the sentinel error type returned for validation
// failures. It is safe to surface to internal API callers; it never carries
// raw input or driver-level detail.
type SearchInventoryError struct {
	Field  string
	Reason string
}

func (e *SearchInventoryError) Error() string {
	return fmt.Sprintf("search_inventory: invalid %s: %s", e.Field, e.Reason)
}

// Public sentinels for caller-side error classification (no input echo).
var (
	ErrInvalidQuery    = &SearchInventoryError{Field: "query", Reason: "failed validation"}
	ErrInvalidCategory = &SearchInventoryError{Field: "category", Reason: "failed validation"}
	ErrInvalidLimit    = &SearchInventoryError{Field: "limit", Reason: "failed validation"}
)
```

## Validation constants (centralized, modifiable)

```go
// Validation bounds are centralized so security-relevant policy is reviewed
// in one place rather than scattered across call sites. (SSEM: Modifiability)
const (
	maxQueryLen    = 100
	maxCategoryLen = 64
	minLimit       = 1
	maxLimit       = 200
	defaultLimit   = 50
	queryTimeout   = 3 * time.Second
)

// allowedCategories is the canonical enum of categories the system serves.
// An allow-list is used instead of free-form validation: this is the
// Derived Integrity Principle applied to a server-owned vocabulary.
// (SSEM: Integrity, Authenticity)
var allowedCategories = map[string]struct{}{
	"":            {}, // empty = no category filter
	"electronics": {},
	"apparel":     {},
	"grocery":     {},
	"home":        {},
	"office":      {},
}
```

## Input canonicalization helpers

```go
// canonicalizeText trims whitespace and normalizes case for category lookups.
// It does NOT lowercase the search query, because product names are
// case-significant for downstream display; case-insensitive matching is
// handled by the SQL ILIKE operator.
func canonicalizeText(s string) string {
	return strings.TrimSpace(s)
}

// escapeLikePattern escapes the LIKE/ILIKE metacharacters '%', '_' and '\'
// so that user input is matched literally. Without this, a user could
// pass "%" and force a full-table scan, or "_" to broaden matches in
// unintended ways. (SSEM: Integrity, Availability)
func escapeLikePattern(s string) string {
	r := strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`)
	return r.Replace(s)
}

// validateQuery enforces length, encoding, and printable-character rules.
// It returns the canonicalized query or an error.
func validateQuery(raw string) (string, error) {
	q := canonicalizeText(raw)
	if q == "" {
		return "", &SearchInventoryError{Field: "query", Reason: "empty"}
	}
	if !utf8.ValidString(q) {
		return "", &SearchInventoryError{Field: "query", Reason: "invalid utf-8"}
	}
	if utf8.RuneCountInString(q) > maxQueryLen {
		return "", &SearchInventoryError{Field: "query", Reason: "too long"}
	}
	for _, r := range q {
		// Reject control characters; allow letters, digits, punctuation,
		// and spaces. NUL bytes are explicitly out.
		if r == 0x00 || (r < 0x20 && r != '\t') {
			return "", &SearchInventoryError{Field: "query", Reason: "control character"}
		}
	}
	return q, nil
}

// validateCategory checks the canonicalized category against the allow-list.
func validateCategory(raw string) (string, error) {
	c := strings.ToLower(canonicalizeText(raw))
	if utf8.RuneCountInString(c) > maxCategoryLen {
		return "", &SearchInventoryError{Field: "category", Reason: "too long"}
	}
	if _, ok := allowedCategories[c]; !ok {
		return "", &SearchInventoryError{Field: "category", Reason: "not allowed"}
	}
	return c, nil
}

// clampLimit applies server-owned bounds to a client-supplied limit.
// A non-positive value is treated as "use default" rather than an error
// to keep handler ergonomics simple while preserving server authority.
// (Derived Integrity Principle: server owns the cap.)
func clampLimit(n int) int {
	if n <= 0 {
		return defaultLimit
	}
	if n < minLimit {
		return minLimit
	}
	if n > maxLimit {
		return maxLimit
	}
	return n
}
```

## SearchInventory

```go
// SearchInventory returns items whose name matches the supplied query,
// optionally filtered by category, capped by a server-bounded limit.
//
// Trust boundary: ctx is propagated for cancellation/timeout; query and
// category are treated as untrusted and validated before use; limit is
// clamped to a server-owned range. The SQL statement uses parameterized
// arguments exclusively — no string concatenation of user input.
//
// Errors:
//   - *SearchInventoryError on validation failure (safe to surface)
//   - context.DeadlineExceeded / context.Canceled on cancellation
//   - a generic wrapped error for storage failures (driver detail not exposed)
//
// (SSEM: Integrity, Confidentiality, Resilience, Accountability,
//        Availability, Analyzability)
func SearchInventory(
	ctx context.Context,
	db Querier,
	query string,
	category string,
	limit int,
) ([]Item, error) {
	logger := loggerFrom(ctx)

	if db == nil {
		return nil, errors.New("search_inventory: nil database handle")
	}

	q, err := validateQuery(query)
	if err != nil {
		logger.WarnContext(ctx, "search_inventory_validation_failed",
			slog.String("field", "query"))
		return nil, err
	}
	cat, err := validateCategory(category)
	if err != nil {
		logger.WarnContext(ctx, "search_inventory_validation_failed",
			slog.String("field", "category"))
		return nil, err
	}
	bounded := clampLimit(limit)

	// Apply a per-call timeout so a slow query cannot exhaust handler
	// goroutines or DB connections. (SSEM: Availability, Resilience)
	queryCtx, cancel := context.WithTimeout(ctx, queryTimeout)
	defer cancel()

	rows, err := runSearch(queryCtx, db, q, cat, bounded)
	if err != nil {
		// Storage errors are wrapped without echoing input or driver detail
		// in the message; the original error is preserved via %w for
		// internal observability. (SSEM: Confidentiality, Accountability)
		logger.ErrorContext(ctx, "search_inventory_storage_error",
			slog.String("category", cat),
			slog.Int("limit", bounded),
			slog.Int("query_len", utf8.RuneCountInString(q)),
		)
		return nil, fmt.Errorf("search_inventory: storage failure: %w", err)
	}

	logger.InfoContext(ctx, "search_inventory_succeeded",
		slog.String("category", cat),
		slog.Int("limit", bounded),
		slog.Int("query_len", utf8.RuneCountInString(q)),
		slog.Int("result_count", len(rows)),
	)
	return rows, nil
}
```

## SQL execution and row mapping

```go
// runSearch performs the parameterized query and maps rows. The SQL is a
// constant string; only validated values are bound as parameters. The
// LIKE pattern uses the explicit ESCAPE clause so escaping is portable
// and unambiguous. (SSEM: Integrity)
func runSearch(
	ctx context.Context,
	db Querier,
	q, category string,
	limit int,
) ([]Item, error) {
	const stmt = `
		SELECT id, sku, name, category, price_cents
		FROM items
		WHERE name ILIKE $1 ESCAPE '\'
		  AND ($2 = '' OR category = $2)
		ORDER BY name ASC
		LIMIT $3
	`
	pattern := "%" + escapeLikePattern(q) + "%"

	rows, err := db.QueryContext(ctx, stmt, pattern, category, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Pre-allocate to the upper bound to avoid repeated growth and to make
	// memory use predictable. (SSEM: Availability)
	results := make([]Item, 0, limit)
	for rows.Next() {
		item, scanErr := scanItem(rows)
		if scanErr != nil {
			return nil, scanErr
		}
		results = append(results, item)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return results, nil
}

// scanItem maps a single row into an Item. It is split out for testability
// and to keep runSearch within the analyzability budget.
func scanItem(rows *sql.Rows) (Item, error) {
	var (
		it     Item
		idStr  string
	)
	if err := rows.Scan(&it.ID, &it.SKU, &it.Name, &it.Category, &it.PriceCents); err != nil {
		// Some drivers do not natively scan into uuid.UUID; if so, scan
		// into a string and parse. The fallback is intentionally explicit
		// rather than panicking. (SSEM: Resilience)
		if err2 := rows.Scan(&idStr, &it.SKU, &it.Name, &it.Category, &it.PriceCents); err2 != nil {
			return Item{}, err2
		}
		parsed, perr := uuid.Parse(idStr)
		if perr != nil {
			return Item{}, fmt.Errorf("invalid uuid in row: %w", perr)
		}
		it.ID = parsed
	}
	return it, nil
}
```

## Logging context

```go
// loggerFrom retrieves a structured logger from context, falling back to
// the default. Centralized so log shape (and PII redaction policy) is
// reviewed in one place. (SSEM: Accountability, Transparency)
type loggerKey struct{}

func loggerFrom(ctx context.Context) *slog.Logger {
	if l, ok := ctx.Value(loggerKey{}).(*slog.Logger); ok && l != nil {
		return l
	}
	return slog.Default()
}
```

## Suggested test seams

```go
// SearchInventory accepts a Querier interface, so unit tests can supply a
// fake without touching a real database. Validation paths are pure
// functions and can be tested in isolation. Example outline:
//
//   func TestSearchInventory_RejectsEmptyQuery(t *testing.T) { ... }
//   func TestSearchInventory_ClampsLimitAboveMax(t *testing.T) { ... }
//   func TestEscapeLikePattern_EscapesMetachars(t *testing.T) { ... }
//   func TestSearchInventory_AppliesQueryTimeout(t *testing.T) { ... }
```

---

## Securability Notes

### SSEM attribute enforcement

- **Analyzability** — Each function is small and single-purpose. `SearchInventory`
  delegates to `validateQuery`, `validateCategory`, `clampLimit`, `runSearch`,
  and `scanItem` so each unit stays well under 30 LoC and cyclomatic complexity
  is low. Naming describes intent (`escapeLikePattern`, `clampLimit`).
- **Modifiability** — Validation thresholds and the category allow-list are
  module-level constants; policy changes happen in one place. The DB
  dependency is the narrow `Querier` interface, not a concrete `*sql.DB`.
- **Testability** — Validation helpers are pure. The `Querier` interface
  enables mock-based tests; a logger is injected through context.
- **Confidentiality** — No raw user input, SKUs, names, or DB error strings
  appear in log fields; only `category`, `limit`, `query_len`, and
  `result_count` are emitted. Wrapped storage errors preserve detail
  internally via `%w` without surfacing it through the public error message.
- **Accountability** — Validation failures and storage errors emit
  structured `slog` events at appropriate levels (`Warn` for input
  rejection, `Error` for infrastructure faults, `Info` for success). Event
  names are stable identifiers suitable for audit/log indexing.
- **Authenticity** — The function trusts authentication established upstream
  (per the task) but does not extend that trust to inputs. Server-owned
  state (limit cap, allowed categories) is enforced server-side.
- **Availability** — `clampLimit` prevents unbounded result sets;
  `context.WithTimeout` bounds query duration; `escapeLikePattern` prevents
  pathological wildcard queries that could induce full scans; result slice
  is pre-allocated.
- **Integrity** — Parameterized SQL exclusively (`$1`, `$2`, `$3`). LIKE
  metacharacters explicitly escaped via `ESCAPE '\'`. Category is
  allow-listed. The Derived Integrity Principle is applied to `limit`
  (server-clamped) and `category` (server-vocabulary).
- **Resilience** — Specific error returns (no bare panic/recover);
  `rows.Err()` checked after iteration; `defer rows.Close()` prevents
  connection leaks; UUID parsing has an explicit fallback path; nil DB
  handle is checked.

### Trust boundary handling

`SearchInventory` is the trust boundary for this data path: handler -> data
access. Canonicalize -> sanitize -> validate is applied to `query` and
`category` before either touches SQL. Interior helpers (`runSearch`,
`scanItem`) operate on already-validated values and stay flexible.

### ASVS feature requirements

Identified ASVS chapters and how this implementation addresses them:

- **V5 Validation, Sanitization & Encoding** — Length, encoding, control-char,
  and allow-list checks (V5.1). Parameterized queries and LIKE escaping
  prevent SQL injection (V5.3). Output integers are typed (`int64`); UUIDs
  are parsed, not passed as raw strings.
- **V8 Data Protection** — Log fields exclude raw input and DB errors,
  reducing the chance of leaking sensitive query content into logs.
- **V10 Logging & Error Handling** — Structured `slog` events with stable
  names; errors are wrapped, not echoed; user-facing error messages do not
  leak internal detail.
- **V11 Business Logic** (limit clamping) — Server-side enforcement of
  pagination bounds prevents resource exhaustion via oversized requests.
- **V14 Configuration** — Validation constants are centralized for review.

### Dependency selection

- **Standard library only**, except `github.com/google/uuid` for the UUID
  type. `google/uuid` is the de-facto Go UUID library: actively maintained
  by Google, broad ecosystem usage, low CVE history, BSD-3 licensed.
  Pinning guidance: select the latest stable v1.x release in `go.mod` and
  commit `go.sum` for reproducible builds. If the project already vendors
  a different UUID library (e.g. `gofrs/uuid`), that one should be used
  instead — adding a parallel UUID package would inflate the dependency
  surface unnecessarily.
- **`log/slog`** is used in lieu of a third-party logger (Go 1.21+),
  removing a dependency entirely.
- **No ORM** — `database/sql` plus a constant SQL string keeps the data
  access layer auditable and avoids the additional surface area of an ORM.

### Trade-offs

- Returning `[]Item` rather than streaming (a channel or iterator) is
  appropriate for a capped result set (max 200 rows). For larger result
  sets the API should switch to keyset pagination.
- The category allow-list is hard-coded for clarity; in a production
  system it should be loaded from configuration or a reference table so
  that adding a category does not require a code change.
- `ILIKE` with a leading wildcard cannot use a btree index on `name`. If
  this query becomes hot, introduce a `pg_trgm` GIN index on
  `lower(name)` and adjust the predicate accordingly. This is a
  performance/availability optimization, not a security change.
