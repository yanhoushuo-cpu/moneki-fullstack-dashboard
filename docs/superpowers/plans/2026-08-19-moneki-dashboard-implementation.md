# Moneki Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish a polished restaurant operations dashboard whose REST endpoints and AI answers share one auditable SQLite analytics layer.

**Architecture:** A repeatable Python ETL converts immutable CSV inputs into normalized and quarantined SQLite tables. FastAPI exposes one analytics service to both REST routes and allowlisted AI tools, while a React/Vite application renders the dashboard, evidence-backed chat, and data-quality report from the same contracts.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Pandas, SQLite, pytest, React, TypeScript, Vite, Tailwind CSS, TanStack Query, Recharts, Vitest, Playwright, Docker.

**Spec:** `docs/superpowers/specs/2026-08-19-moneki-dashboard-design.md`

## Global Constraints

- Keep the original files under `data/` byte-for-byte unchanged.
- Store money as integer cents and dates as ISO `YYYY-MM-DD` strings.
- Count orders with `COUNT(DISTINCT order_id)` and calculate average order value as revenue divided by that count.
- Route dashboard requests and AI tools through the same `AnalyticsService` methods.
- Never execute model-generated SQL or hardcode a database result in mock AI mode.
- Default to deterministic mock AI when no provider key is configured.
- Use Python 3.11 or newer and Node.js 20.19 or newer; commit lock files.
- Production uses one Docker image and one HTTP origin.
- Every task follows red-green-refactor and ends in a focused commit.

---

### Task 1: Backend foundation and database schema

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/database.py`
- Create: `backend/app/db/schema.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_database.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings`, `create_engine_for_path(path: Path) -> Engine`, `create_schema(engine: Engine) -> None`, and SQLAlchemy tables `ingestion_runs`, `raw_sales`, `stores`, `products`, `sales`, `quarantined_sales`.
- Consumes: the immutable CSV files in repository-level `data/` only in later ETL tasks.

- [ ] **Step 1: Write the failing schema test**

```python
def test_create_schema_builds_all_tables(tmp_path):
    engine = create_engine_for_path(tmp_path / "test.db")
    create_schema(engine)
    names = set(inspect(engine).get_table_names())
    assert names == {
        "ingestion_runs", "raw_sales", "stores", "products",
        "sales", "quarantined_sales",
    }
```

- [ ] **Step 2: Verify the test fails**

Run: `python -m pytest backend/tests/test_database.py -q`  
Expected: import failure for `app.db.database`.

- [ ] **Step 3: Implement settings, engine, and schema**

Build the `sqlite+pysqlite` URL from the resolved database path, use `check_same_thread=False`, enable SQLite foreign keys, use integer cent columns, define explicit unique keys, and add indexes on `sales.date`, `sales.store_id`, and `sales.product_id`.

```python
@dataclass(frozen=True)
class Settings:
    database_path: Path
    data_dir: Path
    ai_mode: Literal["mock", "provider"]
    ai_api_key: str | None
    ai_base_url: str
    ai_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        repository_root = Path(__file__).resolve().parents[2]
        return cls(
            database_path=Path(os.getenv("DATABASE_PATH", repository_root / "var/moneki.db")),
            data_dir=Path(os.getenv("DATA_DIR", repository_root / "data")),
            ai_mode=os.getenv("AI_MODE", "mock"),
            ai_api_key=os.getenv("AI_API_KEY"),
            ai_base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
            ai_model=os.getenv("AI_MODEL", "gpt-4.1-mini"),
        )
```

- [ ] **Step 4: Run the schema test**

Run: `python -m pytest backend/tests/test_database.py -q`  
Expected: PASS.

- [ ] **Step 5: Commit the foundation**

```bash
git add .gitignore backend
git commit -m "chore: bootstrap analytics backend"
```

### Task 2: Tested ETL and data-quality report

**Files:**
- Create: `backend/app/etl/__init__.py`
- Create: `backend/app/etl/models.py`
- Create: `backend/app/etl/normalizers.py`
- Create: `backend/app/etl/importer.py`
- Create: `backend/app/etl/cli.py`
- Create: `backend/tests/etl/test_normalizers.py`
- Create: `backend/tests/etl/test_importer.py`

**Interfaces:**
- Consumes: Task 1 schema and `data/stores.csv`, `data/products.csv`, `data/sales.csv`.
- Produces: `normalize_date(value: str) -> date`, `parse_amount_to_cents(value: str) -> int`, and `build_database(data_dir: Path, database_path: Path) -> IngestionSummary`.

- [ ] **Step 1: Write normalizer tests**

```python
@pytest.mark.parametrize(("raw", "expected"), [
    ("2026-05-01", date(2026, 5, 1)),
    ("01-05-2026", date(2026, 5, 1)),
    ("2026/05/01", date(2026, 5, 1)),
])
def test_normalize_date_accepts_declared_formats(raw, expected):
    assert normalize_date(raw) == expected

def test_parse_amount_strips_currency_symbol():
    assert parse_amount_to_cents("¥66.00") == 6600
```

- [ ] **Step 2: Verify normalizer tests fail**

Run: `python -m pytest backend/tests/etl/test_normalizers.py -q`  
Expected: import failure for `app.etl.normalizers`.

- [ ] **Step 3: Implement strict normalizers**

Use `datetime.strptime` with exactly the three documented formats and `Decimal` with `ROUND_HALF_UP`; reject every other representation with a typed `NormalizationError`.

- [ ] **Step 4: Write importer behavior tests**

Create miniature CSV fixtures containing an exact duplicate, `S01 `, a missing amount, `S99`, `P99`, positive-quantity/negative-amount, negative-quantity/positive-amount, and zero-quantity/nonzero-amount rows.

```python
summary = build_database(fixture_data_dir, tmp_path / "fixture.db")
assert summary.duplicate_rows_removed == 1
assert summary.amounts_imputed == 1
assert summary.valid_sales == 2
assert summary.quarantined_sales == 5
```

- [ ] **Step 5: Verify importer test fails**

Run: `python -m pytest backend/tests/etl/test_importer.py -q`  
Expected: import failure for `app.etl.importer`.

- [ ] **Step 6: Implement transactional import**

Load dimensions first, store all raw rows, de-duplicate by the seven raw sales fields, collect all quality reasons per row, impute only safe missing amounts, and write the successful database through a temporary path followed by `os.replace`.

- [ ] **Step 7: Verify fixture and real-data import**

Run: `python -m pytest backend/tests/etl -q`  
Expected: PASS.  
Run: `python -m backend.app.etl.cli --data-dir data --database var/moneki.db`  
Expected: JSON summary with `raw_sales=12131`, `duplicates_removed=76`, and no unhandled exception.

- [ ] **Step 8: Commit ETL**

```bash
git add backend/app/etl backend/tests/etl
git commit -m "feat: normalize and audit sales imports"
```

### Task 3: Canonical analytics service

**Files:**
- Create: `backend/app/analytics/__init__.py`
- Create: `backend/app/analytics/models.py`
- Create: `backend/app/analytics/service.py`
- Create: `backend/tests/analytics/test_service.py`
- Create: `backend/tests/analytics/test_real_data.py`

**Interfaces:**
- Consumes: Task 2 clean SQLite tables.
- Produces: `AnalyticsService.get_dashboard(filters: DashboardFilters) -> DashboardResult`, `get_revenue(start_date: date, end_date: date, product_name: str | None, store_id: str | None, store_category: str | None) -> RevenueResult`, `get_top_entities(dimension: str, metric: str, start_date: date, end_date: date, limit: int) -> TopEntitiesResult`, `compare_periods(metric: str, current_start: date, current_end: date, previous_start: date, previous_end: date, filters: Mapping[str, str]) -> ComparisonResult`, `get_trend(metric: str, start_date: date, end_date: date, granularity: str, filters: Mapping[str, str]) -> TrendResult`, and `get_data_quality() -> DataQualityResult`.

- [ ] **Step 1: Write metric tests with a tiny database**

```python
result = service.get_dashboard(
    DashboardFilters(start_date=date(2026, 5, 1), end_date=date(2026, 5, 2))
)
assert result.summary.revenue_cents == 10_000
assert result.summary.order_count == 2  # repeated order lines count once
assert result.summary.average_order_value_cents == 5_000
```

- [ ] **Step 2: Verify tests fail**

Run: `python -m pytest backend/tests/analytics/test_service.py -q`  
Expected: import failure for `app.analytics.service`.

- [ ] **Step 3: Implement typed filters and result objects**

```python
@dataclass(frozen=True)
class DashboardFilters:
    start_date: date
    end_date: date
    store_id: str | None = None

    def previous_period(self) -> tuple[date, date]:
        inclusive_days = (self.end_date - self.start_date).days + 1
        previous_end = self.start_date - timedelta(days=1)
        previous_start = previous_end - timedelta(days=inclusive_days - 1)
        return previous_start, previous_end
```

Implement parameterized SQLAlchemy Core statements. Centralize the base predicate builder so every method applies identical date and store filters.

- [ ] **Step 4: Add real-data cross-checks**

Compare service outputs for the three assignment questions to independent direct SQL queries over the generated database. Assert evidence amounts as integer cents.

- [ ] **Step 5: Run analytics tests**

Run: `python -m pytest backend/tests/analytics -q`  
Expected: PASS.

- [ ] **Step 6: Commit analytics layer**

```bash
git add backend/app/analytics backend/tests/analytics
git commit -m "feat: add canonical restaurant analytics"
```

### Task 4: FastAPI dashboard and quality contracts

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/dependencies.py`
- Create: `backend/app/api/routes_dashboard.py`
- Create: `backend/app/api/routes_meta.py`
- Create: `backend/app/api/routes_quality.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/api.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/api/test_dashboard.py`
- Create: `backend/tests/api/test_errors.py`

**Interfaces:**
- Consumes: `AnalyticsService` from Task 3.
- Produces: `/api/v1/health`, `/api/v1/meta`, `/api/v1/dashboard`, and `/api/v1/data-quality` JSON contracts.

- [ ] **Step 1: Write API contract tests**

```python
response = client.get("/api/v1/dashboard?start_date=2026-06-01&end_date=2026-06-30")
assert response.status_code == 200
payload = response.json()
assert set(payload) == {
    "filters", "summary", "daily", "top_products",
    "store_comparison", "coverage",
}
assert payload["summary"]["order_count"] > 0
```

- [ ] **Step 2: Verify contract tests fail**

Run: `python -m pytest backend/tests/api -q`  
Expected: import or 404 failure.

- [ ] **Step 3: Implement Pydantic responses and routes**

Validate inclusive dates, reject `start_date > end_date`, reject unknown stores, serialize money as `{cents, formatted}`, and map empty baselines to `null` changes with `no_baseline=true`.

- [ ] **Step 4: Run API tests and inspect OpenAPI**

Run: `python -m pytest backend/tests/api -q`  
Expected: PASS.  
Run: `python -c "from backend.app.main import app; assert '/api/v1/dashboard' in app.openapi()['paths']"`  
Expected: exit code 0.

- [ ] **Step 5: Commit API**

```bash
git add backend/app/api backend/app/models backend/app/main.py backend/tests/api
git commit -m "feat: expose dashboard analytics api"
```

### Task 5: Evidence-backed AI tool chain

**Files:**
- Create: `backend/app/ai/__init__.py`
- Create: `backend/app/ai/models.py`
- Create: `backend/app/ai/tools.py`
- Create: `backend/app/ai/mock_planner.py`
- Create: `backend/app/ai/provider.py`
- Create: `backend/app/ai/service.py`
- Create: `backend/app/api/routes_chat.py`
- Create: `backend/tests/ai/test_tools.py`
- Create: `backend/tests/ai/test_mock_planner.py`
- Create: `backend/tests/ai/test_chat_contract.py`

**Interfaces:**
- Consumes: Task 3 service methods.
- Produces: `ChatService.answer(request: ChatRequest) -> ChatResponse` and `POST /api/v1/chat`.

- [ ] **Step 1: Write tool/evidence tests**

```python
response = chat_service.answer(ChatRequest(
    message="牛肉poke 六月卖了多少钱？", history=[]
))
assert response.status == "answered"
assert response.evidence[0].tool == "get_revenue"
assert response.evidence[0].parameters["product_name"] == "牛肉poke"
assert response.evidence[0].result["revenue_cents"] == direct_database_value
```

- [ ] **Step 2: Verify AI tests fail**

Run: `python -m pytest backend/tests/ai -q`  
Expected: import failure for `app.ai.service`.

- [ ] **Step 3: Implement allowlisted tools**

Map the five documented tool names to explicit `AnalyticsService` calls. Parse and validate tool arguments with Pydantic before execution, and generate `Evidence` from the returned typed result plus ingestion run ID.

- [ ] **Step 4: Implement deterministic mock planner**

Recognize date periods, `牛肉poke`, store/category/top/trend intents, and follow-up month phrases. For unsupported questions return `unsupported` with the five suggested prompt chips. Do not place a numeric business result in planner code.

- [ ] **Step 5: Implement optional provider adapter**

Call an OpenAI-compatible `/chat/completions` endpoint with strict function schemas, a timeout, and at most two tool rounds. Use provider mode only when explicitly configured; otherwise instantiate `MockPlanner`.

- [ ] **Step 6: Implement chat route and run tests**

Run: `python -m pytest backend/tests/ai backend/tests/api -q`  
Expected: PASS, including the three required questions, a May follow-up, and an unsupported question.

- [ ] **Step 7: Commit AI chain**

```bash
git add backend/app/ai backend/app/api/routes_chat.py backend/tests/ai
git commit -m "feat: add evidence-backed ai analytics"
```

### Task 6: Frontend foundation and typed API state

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles.css`
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/lib/format.ts`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/lib/format.test.ts`

**Interfaces:**
- Consumes: Task 4 and Task 5 JSON contracts.
- Produces: `api.getMeta`, `api.getDashboard`, `api.getDataQuality`, `api.ask`, `formatMoney`, `formatPercent`, and a QueryClient-backed application shell.

- [ ] **Step 1: Scaffold package manifests and write formatter tests**

```ts
expect(formatMoney({ cents: 4200, formatted: "¥42.00" })).toBe("¥42.00");
expect(formatPercent(null)).toBe("暂无对比");
```

- [ ] **Step 2: Install and verify the failing test**

Run: `cd frontend && npm install && npm test -- --run`  
Expected: failure because `formatMoney` is not implemented.

- [ ] **Step 3: Implement typed client and design tokens**

Define exact interfaces matching backend JSON. Use a warm canvas, charcoal text, coral accent, rounded but restrained cards, tabular numbers, focus rings, reduced-motion support, and a bundled system font stack.

- [ ] **Step 4: Run frontend unit tests and type check**

Run: `cd frontend && npm test -- --run && npm run typecheck`  
Expected: PASS.

- [ ] **Step 5: Commit frontend foundation**

```bash
git add frontend
git commit -m "chore: bootstrap operations dashboard ui"
```

### Task 7: Dashboard user experience

**Files:**
- Create: `frontend/src/features/dashboard/useDashboard.ts`
- Create: `frontend/src/features/dashboard/DashboardPage.tsx`
- Create: `frontend/src/features/dashboard/FilterBar.tsx`
- Create: `frontend/src/features/dashboard/KpiCard.tsx`
- Create: `frontend/src/features/dashboard/RevenueChart.tsx`
- Create: `frontend/src/features/dashboard/TopProducts.tsx`
- Create: `frontend/src/features/dashboard/StoreComparison.tsx`
- Create: `frontend/src/features/dashboard/DataQualityDrawer.tsx`
- Create: `frontend/src/features/dashboard/DashboardPage.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: Task 6 typed client.
- Produces: a responsive dashboard and `applyDashboardAction(action: DashboardAction)` hook consumed by chat.

- [ ] **Step 1: Write the dashboard interaction test**

Mock `/meta` and `/dashboard`; assert KPI values, chart heading, Top 10 rows, and a request containing the updated date range after the filter is submitted.

- [ ] **Step 2: Verify the component test fails**

Run: `cd frontend && npm test -- --run src/features/dashboard/DashboardPage.test.tsx`  
Expected: module-not-found failure.

- [ ] **Step 3: Implement filters, query hook, cards, charts, and tables**

Use semantic controls, accessible labels, chart summaries, skeletons, empty states, retry buttons, stable query keys, and an abortable API client. Add previous-period deltas without recomputing backend values.

- [ ] **Step 4: Implement quality drawer and responsive layout**

Show raw, cleaned, repaired, duplicate, and quarantined counts with rule descriptions. At widths below 900px use one column and horizontal-safe tables.

- [ ] **Step 5: Run tests and production build**

Run: `cd frontend && npm test -- --run && npm run typecheck && npm run build`  
Expected: PASS and `frontend/dist/index.html` exists.

- [ ] **Step 6: Commit dashboard**

```bash
git add frontend/src
git commit -m "feat: build restaurant operations dashboard"
```

### Task 8: AI chat, evidence, and dashboard linking

**Files:**
- Create: `frontend/src/features/chat/AiAssistant.tsx`
- Create: `frontend/src/features/chat/ChatMessage.tsx`
- Create: `frontend/src/features/chat/EvidenceCard.tsx`
- Create: `frontend/src/features/chat/SuggestionChips.tsx`
- Create: `frontend/src/features/chat/AiAssistant.test.tsx`
- Modify: `frontend/src/features/dashboard/DashboardPage.tsx`

**Interfaces:**
- Consumes: Task 5 chat response and Task 7 `applyDashboardAction`.
- Produces: conversational history, evidence disclosure, follow-up context, and “应用到看板” behavior.

- [ ] **Step 1: Write chat interaction tests**

Submit “牛肉poke 六月卖了多少钱？”, assert the answer and evidence label render, expand evidence, click “应用到看板”, and assert the dashboard action callback receives June dates and a product highlight.

- [ ] **Step 2: Verify chat tests fail**

Run: `cd frontend && npm test -- --run src/features/chat/AiAssistant.test.tsx`  
Expected: module-not-found failure.

- [ ] **Step 3: Implement assistant and evidence UI**

Provide five prompt chips, pending animation, error recovery, mode badge, bounded history, evidence details, supported/unsupported states, and an aria-live answer region.

- [ ] **Step 4: Wire dashboard actions and run full frontend checks**

Run: `cd frontend && npm test -- --run && npm run typecheck && npm run build`  
Expected: PASS.

- [ ] **Step 5: Commit AI experience**

```bash
git add frontend/src/features
git commit -m "feat: connect ai evidence to dashboard filters"
```

### Task 9: Production container, CI, and end-to-end proof

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`
- Create: `.env.example`
- Create: `.github/workflows/ci.yml`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/e2e/dashboard.spec.ts`
- Modify: `backend/app/main.py`
- Modify: `frontend/package.json`

**Interfaces:**
- Consumes: all application tasks.
- Produces: one production image, one compose command, CI checks, and an end-to-end browser proof.

- [ ] **Step 1: Write the browser smoke test**

Test loading the KPI cards, changing dates, opening data quality, asking a required question, expanding evidence, and applying the response to dashboard filters.

- [ ] **Step 2: Add multi-stage Docker build**

Build `frontend/dist` in a Node stage, install backend dependencies in a Python stage, copy the immutable data, import SQLite during image build or startup, serve `/assets` plus SPA fallback from FastAPI, and expose port 8000.

- [ ] **Step 3: Add CI**

Run backend pytest, frontend Vitest, TypeScript checking, Vite production build, and Docker build on pushes and pull requests.

- [ ] **Step 4: Run container and smoke test**

Run: `docker compose up --build -d`  
Expected: `/api/v1/health` returns HTTP 200.  
Run: `cd frontend && npx playwright install chromium && npm run test:e2e`  
Expected: PASS.

- [ ] **Step 5: Commit production packaging**

```bash
git add Dockerfile docker-compose.yml .dockerignore .env.example .github frontend backend/app/main.py
git commit -m "ci: package and verify the full stack"
```

### Task 10: Submission documentation, visual QA, and publishing

**Files:**
- Modify: `README.md`
- Create: `AI_USAGE.md`
- Create: `DEMO.md`
- Create: `docs/DATA_QUALITY.md`
- Create: `docs/screenshots/dashboard.png`

**Interfaces:**
- Consumes: verified application behavior and generated data-quality summary.
- Produces: evaluator-facing setup, architecture, proof, screenshot, deployment details, and public GitHub repository.

- [ ] **Step 1: Write evaluator-facing documents**

README must contain the three-step Docker start, local development commands, architecture diagram, stack rationale, metric definitions, cleaning counts, AI modes, tests, and deployment URL. AI_USAGE must include a real prompt, a concrete AI mistake, the detection test, the fix, and human-owned decisions. DEMO must script three required questions, the May follow-up, and one unsupported question.

- [ ] **Step 2: Run complete verification from a clean process**

Run: `python -m pytest backend/tests -q`  
Expected: all tests pass.  
Run: `cd frontend && npm test -- --run && npm run typecheck && npm run build`  
Expected: all checks pass.  
Run: `docker compose build`  
Expected: image builds successfully.

- [ ] **Step 3: Perform visual QA**

Open the production application at desktop and mobile widths, verify no overflow or clipped controls, exercise loading/error/empty states, and save the final desktop screenshot to `docs/screenshots/dashboard.png`.

- [ ] **Step 4: Commit submission materials**

```bash
git add README.md AI_USAGE.md DEMO.md docs
git commit -m "docs: prepare full-stack assignment submission"
```

- [ ] **Step 5: Publish**

Verify `gh auth status`. Create a new public repository named `moneki-fullstack-dashboard` under the authenticated account when it does not already exist, add it as `submission`, push the current history to `submission/main`, and print the public URL. If GitHub authentication or repository creation fails, copy the complete Git repository to `Desktop/moneki-fullstack-dashboard` without deleting the working repository.

- [ ] **Step 6: Final acceptance**

Verify the public/default branch contains the original assignment commit plus all focused commits, no secret appears in tracked files, the README commands match the repository, and the published page or local Docker service answers the three required questions with database-backed evidence.
