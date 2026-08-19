# Moneki Streaming and Public Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add honest, test-covered SSE chat streaming, publish the completed project to the user's public GitHub repository, and deploy the same Docker image to a verified public Render URL.

**Architecture:** `ChatService` remains the only producer of business answers and evidence. A small backend streaming adapter serializes that existing result into SSE events; a focused frontend parser consumes those events and the assistant renders partial text before committing the final structured response. The production build remains a single FastAPI-hosted Docker image and uses Render's injected `PORT`.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, React 19, TypeScript 5.9, Vite 7, Vitest, Testing Library, Playwright, Docker, Render Blueprint, GitHub CLI.

**Spec:** `docs/superpowers/specs/2026-08-20-streaming-public-deployment-design.md`

## Global Constraints

- Default deployment uses `AI_MODE=mock` and requires no API key.
- All answer numbers must still come from SQLite through `AnalyticsService` and the existing whitelist tools.
- The UI must say “数据库规则分析” or “本地规则”; it must not claim that deterministic chunks are model tokens.
- `POST /api/v1/chat` remains backward compatible; the new endpoint is `POST /api/v1/chat/stream` with `text/event-stream`.
- The production app remains one same-origin Docker service with a local fallback port of `8000`.
- No secret, token, private email, generated cache, or local database is committed.
- Every behavior change follows red-green-refactor and every completion claim needs fresh command output.

---

### Task 1: Preserve and Commit the Completed Defect Fixes

**Files:**
- Modify: `backend/app/ai/mock_planner.py`
- Modify: `backend/app/ai/service.py`
- Modify: `backend/tests/ai/test_chat_contract.py`
- Modify: `frontend/src/features/chat/AiAssistant.tsx`
- Modify: `frontend/src/features/chat/AiAssistant.test.tsx`
- Modify: `frontend/src/features/chat/EvidenceCard.tsx`
- Create: `frontend/src/features/chat/EvidenceCard.test.tsx`
- Modify: `frontend/src/features/dashboard/DashboardPage.tsx`
- Modify: `frontend/src/features/dashboard/DashboardPage.test.tsx`
- Modify: `frontend/src/test/setup.ts`

**Interfaces:**
- Consumes: existing `ChatService.answer(ChatRequest) -> ChatResponse` and dashboard/data-quality API hooks.
- Produces: a clean, regression-tested baseline for the streaming work.

- [ ] **Step 1: Run the focused regression tests already written for the fixes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/ai/test_chat_contract.py -q
Set-Location frontend
npm test -- --run src/features/chat/AiAssistant.test.tsx src/features/chat/EvidenceCard.test.tsx src/features/dashboard/DashboardPage.test.tsx
Set-Location ..
```

Expected: all selected tests pass; no Recharts zero-size warning appears.

- [ ] **Step 2: Review only the intended defect-fix diff**

Run:

```powershell
git diff --check
git diff -- backend/app/ai/mock_planner.py backend/app/ai/service.py backend/tests/ai/test_chat_contract.py frontend/src/features/chat frontend/src/features/dashboard/DashboardPage.tsx frontend/src/features/dashboard/DashboardPage.test.tsx frontend/src/test/setup.ts
```

Expected: fixes cover contextless follow-up handling, data-quality retry/error state, truthful placeholder, evidence units, and test-environment chart sizing.

- [ ] **Step 3: Commit the verified baseline**

```powershell
git add -- backend/app/ai/mock_planner.py backend/app/ai/service.py backend/tests/ai/test_chat_contract.py frontend/src/features/chat/AiAssistant.tsx frontend/src/features/chat/AiAssistant.test.tsx frontend/src/features/chat/EvidenceCard.tsx frontend/src/features/chat/EvidenceCard.test.tsx frontend/src/features/dashboard/DashboardPage.tsx frontend/src/features/dashboard/DashboardPage.test.tsx frontend/src/test/setup.ts
git commit -m "fix: close dashboard and assistant defects"
```

### Task 2: Add the Backend SSE Contract

**Files:**
- Create: `backend/app/ai/streaming.py`
- Modify: `backend/app/api/routes_chat.py`
- Create: `backend/tests/api/test_chat_stream.py`

**Interfaces:**
- Consumes: `ChatService.answer(request: ChatRequest) -> ChatResponse`.
- Produces: `split_answer(answer: str, max_chars: int = 12) -> list[str]`, `encode_sse(event: str, payload: dict[str, object]) -> str`, and `stream_chat_response(response: ChatResponse, delay_seconds: float = 0.015) -> AsyncIterator[str]`.

- [ ] **Step 1: Write failing stream contract tests**

Add tests that post the existing fixture question and parse frames by blank lines:

```python
def _events(body: str) -> list[tuple[str, dict]]:
    parsed = []
    for frame in body.strip().split("\n\n"):
        lines = frame.splitlines()
        name = next(line[7:] for line in lines if line.startswith("event: "))
        data = json.loads(next(line[6:] for line in lines if line.startswith("data: ")))
        parsed.append((name, data))
    return parsed


def test_chat_stream_emits_deltas_and_the_same_structured_result(api_client):
    request = {"message": "牛肉poke 五月卖了多少钱？", "history": []}
    expected = api_client.post("/api/v1/chat", json=request).json()
    with api_client.stream("POST", "/api/v1/chat/stream", json=request) as response:
        body = "".join(response.iter_text())
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"
    events = _events(body)
    names = [name for name, _ in events]
    assert names[0:2] == ["start", "status"]
    assert names[-2:] == ["result", "done"]
    assert "".join(data["text"] for name, data in events if name == "delta") == expected["answer"]
    assert next(data["response"] for name, data in events if name == "result") == expected
```

Also test empty input still returns HTTP 422 before streaming and an unsupported question ends with empty evidence.
Patch `split_answer` to raise in a focused unit test and assert the generator emits an `error` event without a trailing `done` event.

- [ ] **Step 2: Run the new tests and verify red**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/api/test_chat_stream.py -q`

Expected: FAIL with 404 for `/api/v1/chat/stream`.

- [ ] **Step 3: Implement the focused streaming adapter**

Create `backend/app/ai/streaming.py` with deterministic framing:

```python
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from app.ai.models import ChatResponse


def split_answer(answer: str, max_chars: int = 12) -> list[str]:
    chunks: list[str] = []
    current = ""
    for character in answer:
        current += character
        if len(current) >= max_chars or character in "，。！？；":
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return chunks


def encode_sse(event: str, payload: dict[str, object]) -> str:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


async def stream_chat_response(
    response: ChatResponse,
    delay_seconds: float = 0.015,
) -> AsyncIterator[str]:
    yield encode_sse("start", {})
    yield encode_sse("status", {"message": "正在查询可信经营数据…"})
    try:
        for chunk in split_answer(response.answer):
            yield encode_sse("delta", {"text": chunk})
            if delay_seconds:
                await asyncio.sleep(delay_seconds)
        yield encode_sse("result", {"response": response.model_dump(mode="json")})
        yield encode_sse("done", {})
    except Exception:
        yield encode_sse("error", {"message": "流式传输中断，请重试。"})
```

Modify `routes_chat.py` so the route computes `response = service.answer(request)` once and returns `StreamingResponse(stream_chat_response(response), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`.

- [ ] **Step 4: Run backend stream and full backend tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/api/test_chat_stream.py -q
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Expected: all tests pass; the concatenated deltas equal the final answer exactly.

- [ ] **Step 5: Commit the backend stream**

```powershell
git add -- backend/app/ai/streaming.py backend/app/api/routes_chat.py backend/tests/api/test_chat_stream.py
git commit -m "feat: stream verified chat responses over SSE"
```

### Task 3: Build a UTF-8-Safe Frontend SSE Parser

**Files:**
- Create: `frontend/src/api/chatStream.ts`
- Create: `frontend/src/api/chatStream.test.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/types.ts`

**Interfaces:**
- Consumes: SSE events `start`, `status`, `delta`, `result`, `done`, and `error`.
- Produces: `streamChat(message: string, history: ChatMessage[], options: { signal?: AbortSignal; onEvent: (event: ChatStreamEvent) => void }): Promise<ChatResponse>` and `api.askStream` with the same signature.

- [ ] **Step 1: Write failing parser tests with split Chinese bytes**

Mock `fetch` with a `ReadableStream<Uint8Array>` whose chunks split in the middle of the UTF-8 bytes for “牛肉”. Assert:

```typescript
const seen: ChatStreamEvent[] = [];
const result = await streamChat('问题', [], { onEvent: (event) => seen.push(event) });

expect(seen.filter((event) => event.type === 'delta')).toEqual([
  { type: 'delta', text: '牛' },
  { type: 'delta', text: '肉' },
]);
expect(result.answer).toBe('牛肉');
```

Add separate tests for a frame split across chunks, an HTTP 422 response, an `error` event, and EOF before a `result` event.

- [ ] **Step 2: Run the parser test and verify red**

Run: `Set-Location frontend; npm test -- --run src/api/chatStream.test.ts`

Expected: FAIL because `chatStream.ts` does not exist.

- [ ] **Step 3: Implement the stream types and parser**

Add this discriminated union to `types.ts`:

```typescript
export type ChatStreamEvent =
  | { type: 'start' }
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'result'; response: ChatResponse }
  | { type: 'done' }
  | { type: 'error'; message: string };
```

Implement `chatStream.ts` with `new TextDecoder()` and `decoder.decode(value, { stream: true })`. Keep a string buffer, normalize CRLF to LF, consume only complete `\n\n` frames, parse the `event:` and `data:` lines, call `onEvent`, store the `result.response`, throw on `error`, and throw `StreamProtocolError('流式响应未正常完成')` if EOF arrives without both `result` and `done`.

Define the options beside the parser so the API client and component share one callback contract:

```typescript
export interface ChatStreamOptions {
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}
```

In `client.ts`, expose:

```typescript
askStream: (
  message: string,
  history: ChatMessage[],
  options: ChatStreamOptions,
) => streamChat(message, history.slice(-8), options),
```

- [ ] **Step 4: Run parser tests, typecheck, and commit**

```powershell
Set-Location frontend
npm test -- --run src/api/chatStream.test.ts
npm run typecheck
Set-Location ..
git add -- frontend/src/api/chatStream.ts frontend/src/api/chatStream.test.ts frontend/src/api/client.ts frontend/src/api/types.ts
git commit -m "feat: parse chat SSE streams safely"
```

Expected: parser tests and typecheck pass.

### Task 4: Render Partial Answers in the Assistant

**Files:**
- Modify: `frontend/src/features/chat/AiAssistant.tsx`
- Modify: `frontend/src/features/chat/AiAssistant.test.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/e2e/dashboard.spec.ts`

**Interfaces:**
- Consumes: `api.askStream(..., { signal, onEvent })` from Task 3.
- Produces: partial answer text, status copy, cancellation, retry, and unchanged final evidence/dashboard actions.

- [ ] **Step 1: Replace the component mock with a controllable stream and write failing tests**

Mock `api.askStream` so it emits status and two deltas before resolving:

```typescript
vi.mocked(api.askStream).mockImplementation(async (_message, _history, options) => {
  options.onEvent({ type: 'status', message: '正在查询可信经营数据…' });
  options.onEvent({ type: 'delta', text: '牛肉poke' });
  options.onEvent({ type: 'delta', text: '营业额为 ¥12,345.67。' });
  options.onEvent({ type: 'result', response });
  options.onEvent({ type: 'done' });
  return response;
});
```

Assert the partial text appears while the promise is unresolved, the mode label reads `数据库规则分析`, final evidence still expands, the stop button aborts the signal, and a rejected stream restores the question for retry.
Add a second-request test that submits another question while the first promise is unresolved and verifies the first request's `AbortSignal` becomes aborted.

- [ ] **Step 2: Run the component test and verify red**

Run: `Set-Location frontend; npm test -- --run src/features/chat/AiAssistant.test.tsx`

Expected: FAIL because the component still calls `api.ask` and has no streaming state.

- [ ] **Step 3: Implement minimal streaming UI state**

Add `pendingAnswer` and `pendingStatus`. During `onEvent`, append only delta text and replace status text. Render the pending assistant message as:

```tsx
<ChatMessage role="assistant">
  {pendingAnswer ? <p>{pendingAnswer}</p> : <span className="thinking-dots" aria-label={pendingStatus}><i /><i /><i /></span>}
  <span className="answer-badge streaming">流式传输 · 数据库规则分析</span>
  <button type="button" className="stop-stream-button" onClick={() => controllerRef.current?.abort()}>
    停止
  </button>
</ChatMessage>
```

On success, append the final `ChatResponse` once. On abort, restore the question without showing a network error. In `finally`, clear pending text/status only for the active controller. Keep existing evidence and dashboard-action rendering unchanged.
Remove the `pendingQuestion` early return and the pending-state disable from the composer/suggestion controls so a newly submitted question first aborts the old controller and then starts its own stream.

- [ ] **Step 4: Update the browser test to prove the stream endpoint is used**

Listen for the response whose URL ends with `/api/v1/chat/stream`, click the starter question, and assert its `content-type` contains `text/event-stream` before checking final answer, evidence, and dashboard linkage.

- [ ] **Step 5: Run frontend tests, typecheck, build, and commit**

```powershell
Set-Location frontend
npm test -- --run
npm run typecheck
npm run build
Set-Location ..
git add -- frontend/src/features/chat/AiAssistant.tsx frontend/src/features/chat/AiAssistant.test.tsx frontend/src/styles.css frontend/e2e/dashboard.spec.ts
git commit -m "feat: render streaming assistant answers"
```

Expected: all component tests, typecheck, and the production build pass.

### Task 5: Make the Docker Image Render-Compatible

**Files:**
- Modify: `Dockerfile`
- Create: `render.yaml`
- Create: `backend/tests/test_deployment_contract.py`

**Interfaces:**
- Consumes: Render-provided `PORT`; local default is `8000`.
- Produces: a free Docker web service named `moneki-fullstack-dashboard` with health path `/api/v1/health` and `AI_MODE=mock`.

- [ ] **Step 1: Write a failing deployment contract test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_and_render_blueprint_share_the_runtime_contract():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "${PORT:-8000}" in dockerfile
    assert "os.environ.get('PORT', '8000')" in dockerfile
    assert "runtime: docker" in blueprint
    assert "plan: free" in blueprint
    assert "healthCheckPath: /api/v1/health" in blueprint
    assert "value: mock" in blueprint
```

- [ ] **Step 2: Run the deployment test and verify red**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/test_deployment_contract.py -q`

Expected: FAIL because `render.yaml` is missing and the Docker command hardcodes port 8000.

- [ ] **Step 3: Implement Docker and Render configuration**

Change the Docker health check and command to:

```dockerfile
HEALTHCHECK --interval=20s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/v1/health', timeout=2)"

CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}"]
```

Create `render.yaml`:

```yaml
services:
  - type: web
    name: moneki-fullstack-dashboard
    runtime: docker
    plan: free
    healthCheckPath: /api/v1/health
    envVars:
      - key: AI_MODE
        value: mock
```

- [ ] **Step 4: Verify configuration and commit**

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_deployment_contract.py -q
git diff --check
git add -- Dockerfile render.yaml backend/tests/test_deployment_contract.py
git commit -m "chore: prepare Render deployment"
```

Expected: deployment contract passes. If Docker is available, additionally run `docker build -t moneki-dashboard:local .` and start it with `-e PORT=8090 -p 8090:8090` before checking `/api/v1/health`.

### Task 6: Document Streaming and the Honest AI Boundary

**Files:**
- Modify: `README.md`
- Modify: `AI_USAGE.md`
- Modify: `DEMO.md`
- Modify: `.env.example`

**Interfaces:**
- Consumes: the final endpoint and Render behavior from Tasks 2–5.
- Produces: evaluator-facing setup, API, demo, and deployment instructions that match the application.

- [ ] **Step 1: Update README behavior and API examples**

Replace the old “不将流式打字动画伪装成模型流式协议” statement with an honest statement that `/chat/stream` is real SSE transport while the content is deterministic database-rule output. Add:

```bash
curl -N -X POST "http://localhost:8000/api/v1/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message":"牛肉poke 六月卖了多少钱？","history":[]}'
```

Document `start → status → delta* → result → done`, the free Render cold start, the health URL, and that no API key is needed.

- [ ] **Step 2: Update AI usage and demo evidence**

In `AI_USAGE.md`, distinguish “provider-ready” from “enabled online” and record why no paid model was used. In `DEMO.md`, add a step telling reviewers to observe partial answer growth and then inspect the final evidence card.

- [ ] **Step 3: Verify documentation has no stale claims and commit**

Run:

```powershell
rg -n "不.*流式|29 项|7 项|真实大模型|OpenAI API Key" README.md AI_USAGE.md DEMO.md .env.example
git diff --check
git add -- README.md AI_USAGE.md DEMO.md .env.example
git commit -m "docs: explain streaming and deployment modes"
```

Expected: no claim says the public deployment uses a live model or fake animation; test counts are either current or described without brittle fixed totals.

### Task 7: Run the Complete Local Quality Gate

**Files:**
- Modify only if a verification failure exposes a real defect; use a failing regression test before any fix.

**Interfaces:**
- Consumes: all implementation tasks.
- Produces: fresh passing evidence before publication.

- [ ] **Step 1: Run backend, frontend, type, and build gates**

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
Set-Location frontend
npm test -- --run
npm run typecheck
npm run build
Set-Location ..
```

Expected: every command exits 0.

- [ ] **Step 2: Run the real browser flow**

Run `npm run test:e2e` from `frontend`. Expected: desktop and mobile projects pass the dashboard, data-quality, streamed answer, evidence, and apply-to-dashboard flow.

- [ ] **Step 3: Inspect repository hygiene**

```powershell
git status --short
git diff --check HEAD
git grep -nE "sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}" -- . ":(exclude)docs/superpowers/plans/*"
git ls-files | Select-String -Pattern "(^|/)(\.env$|node_modules|dist|__pycache__|var/.*\.db$)"
```

Expected: no secrets or generated artifacts are tracked, and only intentional documentation metadata remains uncommitted.

### Task 8: Publish the Public GitHub Repository

**Files:**
- Git remotes and GitHub repository metadata only.

**Interfaces:**
- Consumes: clean verified HEAD and authenticated GitHub CLI account `yanhoushuo-cpu`.
- Produces: `https://github.com/yanhoushuo-cpu/moneki-fullstack-dashboard` with remote default branch `main`.

- [ ] **Step 1: Verify identity, scope, and repository availability**

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth status
git status --short
git log --oneline --decorate -8
& "C:\Program Files\GitHub CLI\gh.exe" repo view yanhoushuo-cpu/moneki-fullstack-dashboard
```

Expected: authenticated as `yanhoushuo-cpu`; if `repo view` returns 404, create it in the next step. If it exists, verify it belongs to the same account and reuse it without overwriting unrelated history.

- [ ] **Step 2: Create the public repository and preserve the assignment remote**

For a new repository:

```powershell
git remote rename origin upstream
& "C:\Program Files\GitHub CLI\gh.exe" repo create yanhoushuo-cpu/moneki-fullstack-dashboard --public --description "可审计的门店销售数据看板：FastAPI、React、SQLite 与 SSE 问数助手"
git remote add origin https://github.com/yanhoushuo-cpu/moneki-fullstack-dashboard.git
git push -u origin HEAD:main
& "C:\Program Files\GitHub CLI\gh.exe" repo edit yanhoushuo-cpu/moneki-fullstack-dashboard --default-branch main
```

Expected: `upstream` still points to `MorrisPRC/moneki-fullstack-assignment`; `origin/main` points to the user's public repository.

- [ ] **Step 3: Verify GitHub contents and CI**

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" repo view yanhoushuo-cpu/moneki-fullstack-dashboard --web
& "C:\Program Files\GitHub CLI\gh.exe" run list --repo yanhoushuo-cpu/moneki-fullstack-dashboard --limit 3
```

Wait for the pushed `main` workflow and inspect failures with `gh run view <run-id> --log-failed`; fix only with a reproduced local test, then push the focused commit.

### Task 9: Deploy to Render and Verify the Public Site

**Files:**
- Modify: `README.md` after the final Render URL is known.

**Interfaces:**
- Consumes: public GitHub `main`, root `render.yaml`, and Dockerfile.
- Produces: a public HTTPS Render service and a README link to that exact service.

- [ ] **Step 1: Create the Render service from the public repository**

Open Render Dashboard, choose **New → Blueprint**, select `yanhoushuo-cpu/moneki-fullstack-dashboard`, and apply the root `render.yaml`. If Render requests authentication or GitHub authorization, pause only for the user to complete that login, then continue without changing the design.

Expected settings: Docker runtime, free plan, `AI_MODE=mock`, health path `/api/v1/health`, branch `main`.

- [ ] **Step 2: Wait for deployment and diagnose from logs if needed**

Expected log milestones: frontend Vite build succeeds, Python package installs, ETL creates `/app/var/moneki.db`, Uvicorn binds to Render's `PORT`, and the health check becomes green.

- [ ] **Step 3: Verify the public API and stream**

Using the exact HTTPS URL shown by Render, run:

```powershell
$renderUrl = "https://moneki-fullstack-dashboard.onrender.com"
Invoke-RestMethod "$renderUrl/api/v1/health"
curl.exe -N -X POST "$renderUrl/api/v1/chat/stream" -H "Content-Type: application/json" -d '{"message":"牛肉poke 六月卖了多少钱？","history":[]}'
```

Expected: health reports a ready database; the stream visibly contains multiple `delta` events followed by `result` and `done`.

- [ ] **Step 4: Perform browser acceptance on the deployed site**

Verify desktop and narrow viewport: KPI values load, date/store filters work, data-quality drawer opens and retries correctly, the answer grows incrementally, evidence units are correct, and “应用到看板” changes the dates.

- [ ] **Step 5: Add the exact live URL and finalize publication**

Add a prominent “在线体验” link and free-tier cold-start note to `README.md`, then run:

```powershell
git add -- README.md
git commit -m "docs: add live dashboard URL"
git push origin HEAD:main
& "C:\Program Files\GitHub CLI\gh.exe" run list --repo yanhoushuo-cpu/moneki-fullstack-dashboard --limit 1
```

After CI and Render auto-deploy finish, re-run the health, stream, and browser checks against the final revision.
