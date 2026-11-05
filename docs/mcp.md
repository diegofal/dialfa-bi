# MCP: Dialfa for agents

`POST /mcp` exposes Dialfa's commercial facts (sales, stock, purchase orders, customers' collections, debt and
post-dated cheques) as [MCP](https://modelcontextprotocol.io) tools, **read-only**, so an agent (Jarvis, Finanzas,
Claude Code) can answer "¿cuánto cobramos en octubre?", "¿qué me debe Marti?" or "¿qué cheques tengo para cobrar?"
from the live sales base. Contract: `Raw/Analisis/19-dialfa-cobranzas.md` §10.1. Code: `dialfa-analytics/routes/mcp.py`
(transport, texts, brief) over `analytics/cobranzas.py` and `analytics/ventas.py` (the numbers).

## Tools

All answers carry a short Spanish text to read aloud (`content`) and the data (`structuredContent`), which always has
`datos_al` (ISO UTC) and `fuente`. Amounts in ARS with 2 decimals unless the key ends in `_usd`; dates `YYYY-MM-DD`.
A customer is its trimmed name; `cliente` arguments match without case or accents ("marti" is MARTI; an exact match
wins over a partial one, so "Marti" is not also "MARTIN SA").

| Tool | Arguments | `structuredContent` |
|---|---|---|
| `cobranzas` | `mes` or `desde, hasta` (default: this month); `cliente?` | `{desde, hasta, total, n, por_medio:{efectivo, cheque, echeq, transferencia, retencion, otro}, por_cliente:[{cliente, total, n}], datos_al, fuente}`: payments dated in the range **and up to today** |
| `deuda` | `cliente?, solo_vencida?` | `{total, vencido, a_vencer, clientes:[{cliente, libros, saldo, vencido, no_cierra}], datos_al, fuente}`: every customer in `sync_customers` (one without a balance row owes 0) |
| `cheques_en_cartera` | `cliente?` | `{total, n, cheques:[R], datos_al, fuente}`: cheques and echeqs (`medio` cheque/echeq) dated after today, up to the legal 360 days (below). A future-dated transfer or cash payment is not a cheque: it stays in `cuenta_corriente.cartera` only |
| `cuenta_corriente` | `desde, hasta, cliente?` | `{desde, hasta, datos_al, fuente, recibos:[R], facturas:[{id, fecha, cliente, libro, numero, importe}], cartera:[R]}` |
| `clientes` | `buscar?` | `{clientes:[{cliente, libros}], datos_al, fuente}` |
| `calidad` | none | `{ultimo_sync, sync_ok, errores:[{cliente, archivo, mensaje}], xerp: "ok" \| "no responde" \| "no configurado", datos_al, fuente}` |
| `ventas` | `mes` or `desde, hasta`; `por: mes \| categoria \| cliente` | `{desde, hasta, por, filas:[{clave, venta_ars, venta_usd, venta_costeada_usd, cif_usd, contribucion_usd, margen_lista_pct, descuento_pct, margen_real_pct, facturas, unidades, clientes, ticket_usd, pct_bridas}], factor_cif, cobertura_costo_pct, datos_al, fuente}` |
| `stock` | none | `{fecha, total_usd, por_estado:[{estado, articulos, usd}], serie:[{fecha, total_usd}] (12 months), datos_al, fuente}` |
| `ordenes_compra` | none | `{ordenes:[{id, codigo, proforma, fecha, estado, items, fob_usd, cif_usd}], datos_al, fuente}` |
| `brief` | `horizon_days?` (default 7) | the suite's brief (below) |

`R` = `{id, fecha, cliente, libro, medio, numero, banco, importe, recibo}`.

A bad argument (`mes: "octubre"`) answers `isError: true` with the reason, so the model can fix it. A customer that
doesn't exist answers the normal shape, empty, with a text that says so.

### Where the numbers come from

- **Freshness.** Collections, debt, cheques and customers come from the `sync_*` tables: each customer's spreadsheet,
  synced once a day around 02:00 Buenos Aires time. `datos_al` = end of the last `sync_runs` without error.
  Invoices, sales, stock and orders are live (`datos_al` = time of the query; stock is the daily 02:00 snapshot).
- **`libro` is the ledger book (0/1)**, the `type` of `sync_customers`: which spreadsheet the customer comes from.
  It is **not** cash/electronic. A customer in both books is the same customer and is added up.
- **Payment medium**, one definition (`cobranzas.medio_de_pago(recibo, banco)`), used by the MCP and the dashboard,
  in order: contains "efectivo" → `efectivo`; "retenc" → `retencion`; "echeq"/"e-cheq" → `echeq` + the last number of
  3+ digits; "transf" or "trasf" → `transferencia` (the misspelling "TRASFERENCIA ELECTRONICA" is in the
  spreadsheets); only digits (3+) → `cheque` + that number; else `otro` (e.g. 1–2 digit numbers like "94"). Withholdings (`retencion`) are tax certificates, not money.
- **Cheques more than 360 days ahead are not in the portfolio.** A deferred cheque (or echeq) is payable at most 360
  days after issue (Ley 24.452, art. 54). A payment dated after today + 360 days is a typo in the spreadsheet (on
  04/11/2026: PATIÑO CONVAL, "68", dated 12/04/2975, $392.739,62). It is left out of `cheques_en_cartera` and of
  `cuenta_corriente.cartera`, and reported in `calidad.errores` and in the brief, so it is never silent.
- **Sales** (Raw/Analisis/15 "Inventario de orígenes", Raw/Analisis/02): valid invoices exclude deleted, cancelled,
  credit notes and quotations. `venta_usd` = quantity × list price (`unit_price_usd`) × (1 − discount %). `venta_ars` =
  that × the invoice's `usd_exchange_rate` (equal to `net_amount` to the cent from March 2026; `net_amount` is in USD in
  January and mixed in February because it sums `line_total`). Cost = `articles.last_purchase_price` (FOB of the last
  proforma; `cost_price` is empty); CIF = FOB × (1 + `cif_percentage`/100) (50 % everywhere, `factor_cif` 1,5).
  `margen_lista_pct` = 1 − CIF / list sales with cost; `descuento_pct` = 1 − sales / list sales; `margen_real_pct` =
  contribution / sales with cost; `cobertura_costo_pct` = list sales with cost / list sales. Costs are today's: a new
  proforma changes old months (the base keeps no cost history).

## Connect

1. Create a token (one per client; shown once, never written to a file):

   ```sh
   cd dialfa-analytics && python scripts/mcp_token.py
   ```

   It prints the token (give it to the client) and its sha256. Add the sha256 to the Railway variable
   `DIALFA_MCP_TOKENS` (comma-separated hex). Revoking a client = removing its hash.

2. Point the agent at `/mcp` with the token as a bearer header. Claude Code:

   ```sh
   claude mcp add --transport http dialfa https://<dialfa-bi host>/mcp --header "Authorization: Bearer dmcp_…"
   ```

By hand:

```sh
curl -s https://<host>/mcp -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"deuda","arguments":{"cliente":"Marti"}}}'
```

## Transport

Streamable HTTP, the simple subset (as Changuito's `docs/mcp.md`): one JSON-RPC message per `POST`, one JSON response
(no sessions, no SSE, no batches); notifications get `202`; `GET /mcp` is `405`. Methods: `initialize`, `ping`,
`tools/list`, `tools/call`. Protocol versions 2024-11-05 to 2025-11-25. `initialize` returns `serverInfo {name:
"dialfa", title: "Dialfa · ventas, clientes y cobranzas"}` and Spanish `instructions` for the router model (which tool
answers what, how fresh each fact is, what `libro` means).

- **Auth:** `Authorization: Bearer <token>`, valid if `sha256(token)` is in `DIALFA_MCP_TOKENS`. No valid token: `401`
  with `WWW-Authenticate: Bearer`. Without the variable nobody gets in. `/mcp` is outside flask-login (no session
  cookie involved); the rest of the app still requires login.
- **No browsers:** a request with an `Origin` header is refused (`403`).
- **Read-only, twice:** every connection opens with `default_transaction_read_only=on` and a 30 s statement timeout,
  and the query function refuses anything but a single `SELECT`/`WITH` (`database/readonly.py`).
- **Log:** every `tools/call` logs the tool, the first 8 hex of the token's hash, the result and the milliseconds.

## The brief

Same item shape as the rest of the suite (`{source, kind, title, detail, due, urgency, action}`), here
`source: "dialfa"` and `action` always `null` (nothing here writes). The answer is `{source, horizon_days,
generated_at, items, avisos}`. Items, in order:

- `alerta` (high): the last spreadsheet sync failed, or the last good one is more than 26 h old, or the base could not
  be read at all. Said first: what can't be read is said.
- `vencido` (medium): today's overdue debt, total and the three largest. **Not "how much it grew":** the base keeps
  no history of balances (`sync_balances` is rewritten on every sync), so growth can't be computed as a fact; the
  answer says so in `avisos`. A consumer that wants growth compares two days of this item.
- `fecha_imposible` (medium): a payment dated beyond the 360-day cheque limit (a typo to fix in the spreadsheet).
- `cheques` (medium tomorrow, low after): cheques in portfolio due within `horizon_days`, one item per day.
- `no_cierra` (low): spreadsheets whose invoices minus payments don't give the balance (`sync_errors`).

## Environment

| Variable | What |
|---|---|
| `SPISA_PG_URL` | The sales base (Postgres on Railway). Already set. |
| `DIALFA_MCP_TOKENS` | sha256 hex of each MCP token, comma-separated. New. |
| `DB_SERVER`, `DB_USER`, `DB_PASSWORD` | The old Azure SQL Server (xERP). No defaults in code any more: without them xERP is "no configurado", its dashboard cards stay empty and the app still starts. |

## Tests

```sh
cd dialfa-analytics && python -m pytest tests -q
```

The analytics functions take a query callable `q(sql, params) -> [dict]`; the tests inject fake rows keyed by the
`SQL_*` constants, and also run the real `create_app()` without a database to check that `/mcp` is outside the login
and that the app starts without xERP.
