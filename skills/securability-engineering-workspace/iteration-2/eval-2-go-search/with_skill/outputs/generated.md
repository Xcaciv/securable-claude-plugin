# SearchInventory

Go function for an authenticated internal API handler that searches the
PostgreSQL `items` table by name substring, optionally filtered by category,
with a bounded result set.

## Package and types

```go
package inventory

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
)

// Item is the projection returned to API callers. We deliberately pick the
// columns we expose rather than `SELECT *` (Request Surface Minimization,
// Confidentiality) so adding a column to `items` cannot accidentally leak it.
type Item struct {
	ID         uuid.UUID `json:"id"`
	SKU        string    `json:"sku"`
	Name       string    `json:"name"`
	Category   string    `json:"category"`
	PriceCents int32     `json:"price_cents"`
}

// Querier is the minimum surface we need from a pgx pool / tx. Depending on
// this interface (not a concrete *pgxpool.Pool) keeps SearchInventory
// testable without a live database.
type Querier interface {
	Query(ctx context.Context, sql string, args ...any) (pgx.Rows, error)
}

// Input bounds. Exposed as constants so reviewers and operators can see them
// and tests can pin to them.
const (
	maxQueryLen    = 200  // chars; longer search terms are almost certainly abuse
	maxCategoryLen = 64   // matches the domain's category taxonomy
	maxLimit       = 200  // hard ceiling regardless of caller request
	defaultLimit   = 50   // used when caller passes limit <= 0
)

// Sentinel errors let callers distinguish validation failures from infra
// failures without string matching.
var (
	ErrInvalidQuery    = errors.New("inventory: invalid query")
	ErrInvalidCategory = errors.New("inventory: invalid category")
	ErrInvalidLimit    = errors.New("inventory: invalid limit")
)
```

## The function

```go
// SearchInventory returns items whose name contains `query` (case-insensitive),
// optionally restricted to `category`, up to `limit` rows.
//
// Trust boundary: `query` and `category` originate from the caller's HTTP
// request. They are validated and passed as bind parameters; they are never
// concatenated into SQL. `limit` is clamped server-side — callers cannot ask
// for unbounded result sets.
func SearchInventory(
	ctx context.Context,
	db Querier,
	query string,
	category string,
	limit int,
) ([]Item, error) {
	q, cat, lim, err := validateSearchInputs(query, category, limit)
	if err != nil {
		slog.InfoContext(ctx, "inventory.search.rejected",
			"reason", err.Error(),
			"query_len", len(query),
			"category_len", len(category),
			"limit", limit,
		)
		return nil, err
	}

	sql, args := buildSearchSQL(q, cat, lim)

	rows, err := db.Query(ctx, sql, args...)
	if err != nil {
		// Wrap, don't expose — callers get a stable error, operators get logs.
		slog.ErrorContext(ctx, "inventory.search.db_error", "err", err.Error())
		return nil, fmt.Errorf("inventory: query failed: %w", err)
	}
	defer rows.Close()

	items, err := scanItems(rows, lim)
	if err != nil {
		slog.ErrorContext(ctx, "inventory.search.scan_error", "err", err.Error())
		return nil, fmt.Errorf("inventory: scan failed: %w", err)
	}

	slog.InfoContext(ctx, "inventory.search.ok",
		"category_filter", cat != "",
		"result_count", len(items),
		"limit", lim,
	)
	return items, nil
}
```

## Helpers

```go
// validateSearchInputs canonicalizes and validates the three user-supplied
// arguments. Returns cleaned values suitable for parameter binding.
func validateSearchInputs(query, category string, limit int) (string, string, int, error) {
	q := strings.TrimSpace(query)
	if q == "" {
		return "", "", 0, fmt.Errorf("%w: empty", ErrInvalidQuery)
	}
	if len(q) > maxQueryLen {
		return "", "", 0, fmt.Errorf("%w: too long", ErrInvalidQuery)
	}
	if strings.ContainsRune(q, 0x00) {
		return "", "", 0, fmt.Errorf("%w: null byte", ErrInvalidQuery)
	}

	cat := strings.TrimSpace(category)
	if len(cat) > maxCategoryLen {
		return "", "", 0, fmt.Errorf("%w: too long", ErrInvalidCategory)
	}
	if strings.ContainsRune(cat, 0x00) {
		return "", "", 0, fmt.Errorf("%w: null byte", ErrInvalidCategory)
	}

	lim := limit
	switch {
	case lim <= 0:
		lim = defaultLimit
	case lim > maxLimit:
		lim = maxLimit
	}

	return q, cat, lim, nil
}

// buildSearchSQL returns the query text and bound arguments. The SQL itself
// is static; only the argument values change. The user-supplied `q` is
// escaped for LIKE metacharacters (\, %, _) so a search for "50%" does not
// silently become a wildcard.
func buildSearchSQL(q, cat string, lim int) (string, []any) {
	pattern := "%" + escapeLikePattern(q) + "%"

	if cat == "" {
		return `
			SELECT id, sku, name, category, price_cents
			FROM items
			WHERE name ILIKE $1 ESCAPE '\'
			ORDER BY name
			LIMIT $2
		`, []any{pattern, lim}
	}

	return `
		SELECT id, sku, name, category, price_cents
		FROM items
		WHERE name ILIKE $1 ESCAPE '\'
		  AND category = $2
		ORDER BY name
		LIMIT $3
	`, []any{pattern, cat, lim}
}

// escapeLikePattern escapes the three LIKE metacharacters so that caller
// input is treated as a literal substring match, not a pattern.
func escapeLikePattern(s string) string {
	r := strings.NewReplacer(
		`\`, `\\`,
		`%`, `\%`,
		`_`, `\_`,
	)
	return r.Replace(s)
}

// scanItems materializes rows into the fixed projection. The `lim` hint lets
// us allocate once; we still honor rows.Err() to surface iteration failures.
func scanItems(rows pgx.Rows, lim int) ([]Item, error) {
	items := make([]Item, 0, lim)
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
```

## Notes for the caller (HTTP handler)

The handler is responsible for two things this function intentionally does
not do:

1. **AuthN/AuthZ**: verify the caller is an authenticated internal principal
   before invoking `SearchInventory`. This function assumes that check has
   already happened — it is not a defense against unauthenticated callers.
2. **Deadline**: pass a `context.Context` with a request deadline
   (e.g. `context.WithTimeout(r.Context(), 2*time.Second)`) so a pathological
   query cannot hold a DB connection indefinitely. `pgx` honors the context
   and will cancel the in-flight query.

## Securability Notes

- **SSEM attributes enforced**:
  - *Integrity* — parameterized SQL only; LIKE metacharacters in user input
    are escaped so `%` and `_` cannot silently become wildcards; fixed column
    projection prevents accidental field leakage.
  - *Availability* — `limit` is clamped to `maxLimit` server-side regardless
    of caller input; `ctx` flows through to `pgx` so request cancellation
    and deadlines actually cancel the query.
  - *Testability / Modifiability* — `Querier` interface decouples the
    function from a concrete pool; pure helpers (`validateSearchInputs`,
    `buildSearchSQL`, `escapeLikePattern`) are directly unit-testable.
  - *Accountability* — structured `slog` events at rejection, DB error, and
    success; no user input echoed into log messages (lengths and flags only).
- **ASVS references**:
  - V1.2.4 — parameterized queries for SQL injection protection.
  - V12.3.1 — DB connection is expected to be TLS (handler/pool
    configuration; noted as a pool-level concern).
  - V7 (logging) and V8 (data protection) — logs carry metadata, not
    payload; response projection is minimal.
- **Trust boundaries**: `query` and `category` are canonicalized
  (trim + null-byte reject + length bound) and bound as parameters; `limit`
  is clamped to a hard ceiling. Sentinel errors (`ErrInvalidQuery`,
  `ErrInvalidCategory`) let the handler map to 400 without leaking detail.
- **Dependencies**:
  - `github.com/jackc/pgx/v5` — current mainstream PostgreSQL driver for Go;
    picked over `database/sql` because the table uses `uuid` and pgx's
    native type handling removes a class of conversion bugs. Pin in
    `go.mod` and commit `go.sum`.
  - `github.com/google/uuid` — standard Go UUID type.
  - `log/slog` — standard library; no extra dependency.
- **Trade-offs**:
  - Substring match uses `ILIKE '%term%'` which cannot use a standard btree
    index. For production load, add a `pg_trgm` GIN index on
    `lower(name)` or move to full-text search (`tsvector`). Flagged rather
    than silently chosen because the right answer depends on table size and
    query patterns.
  - Rate limiting and authn/authz are handler-layer concerns and
    intentionally out of scope here.
  - `limit` is silently clamped rather than rejected when the caller asks
    for too many. If the API contract requires 400 on over-limit, swap the
    clamp for `ErrInvalidLimit`.
