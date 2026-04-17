# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Đọc file `01-localhost-vs-production/develop/app.py`, tìm được **5 vấn đề**:

1. **API key hardcode trong code** (dòng 17-18): `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` và `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"`. Nếu push lên GitHub public, key và password bị lộ ngay lập tức.

2. **Không có config management** (dòng 21-22): `DEBUG = True` và `MAX_TOKENS = 500` được hardcode. Không thể thay đổi giữa các môi trường (dev/staging/production) mà không sửa code.

3. **Dùng print() thay vì proper logging** (dòng 33-34): `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` — vừa dùng print thay vì structured logging, vừa **log ra secret** (API key), rất nguy hiểm trong production.

4. **Không có health check endpoint**: Không có `/health` hay `/ready`. Khi deploy lên cloud, platform không biết agent có đang sống hay đã crash → không thể tự restart.

5. **Port và host cố định, không đọc từ environment** (dòng 51-53):
   - `host="localhost"` → chỉ chạy được trên local, container bên ngoài không kết nối được (cần `0.0.0.0`)
   - `port=8000` → hardcode, trong khi Railway/Render inject PORT qua env var
   - `reload=True` → debug reload bật cứng trong production, gây overhead và bảo mật kém

### Exercise 1.2: Chạy basic version

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
# Server chạy tại http://localhost:8000
```

Test:
```bash
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

**Quan sát:** App chạy được và trả về response. Nhưng KHÔNG production-ready vì:
- Không bảo mật (ai cũng gọi được)
- Không health check (platform không monitor được)
- Secrets lộ trong code và logs
- Không graceful shutdown (mất data khi restart)

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|----------------|----------------------|---------------------|
| Config | Hardcode trong code (`DEBUG = True`, `MAX_TOKENS = 500`) | Đọc từ env vars qua `Settings` dataclass (`os.getenv()`) | Cho phép thay đổi config giữa dev/staging/prod mà không sửa code. Tuân thủ 12-Factor principle #3 |
| Secrets | `api_key = "sk-abc123"` trong source | `os.getenv("OPENAI_API_KEY")`, không có giá trị mặc định nhạy cảm | Tránh lộ secrets khi push code lên Git. Secret chỉ tồn tại trong env, không bao giờ trong codebase |
| Port | Cố định `port=8000`, `host="localhost"` | `host=settings.host` (mặc định `0.0.0.0`), `port=settings.port` (từ `PORT` env var) | Cloud platforms inject PORT tự động. `0.0.0.0` cho phép nhận kết nối từ bên ngoài container |
| Health check | Không có | `GET /health` (liveness) + `GET /ready` (readiness) + `GET /metrics` | Platform dùng health check để biết khi nào cần restart container. Load balancer dùng readiness để route traffic |
| Logging | `print()`, log ra cả secrets | Structured JSON logging (`logging` module), KHÔNG log secrets | JSON logs dễ parse bởi log aggregator (Datadog, Loki). Không log secrets tránh rò rỉ qua log system |
| Shutdown | Tắt đột ngột (Ctrl+C) | Graceful shutdown — bắt SIGTERM, hoàn thành request hiện tại trước khi tắt | Tránh mất data/request khi platform deploy version mới hoặc scale down |
| CORS | Không có | Cấu hình `CORSMiddleware` với `allowed_origins` từ env | Kiểm soát domain nào được gọi API, tránh request từ nguồn không mong muốn |
| Reload | `reload=True` luôn bật | `reload=settings.debug` — chỉ bật khi DEBUG=true | Hot reload trong production gây overhead, restart không kiểm soát, và có thể lộ lỗi |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11` (full Python distribution, khoảng ~1 GB)
2. **Working directory:** `/app` (được set bằng `WORKDIR /app`)
3. **Tại sao COPY requirements.txt trước?** Docker layer cache — khi code thay đổi nhưng requirements không đổi, Docker không cần cài lại dependencies. Layer `RUN pip install` được cache, chỉ rebuild layer COPY code phía sau. Tiết kiệm thời gian build đáng kể.
4. **CMD vs ENTRYPOINT:** CMD là lệnh mặc định khi container start, có thể bị override khi `docker run <image> <other-cmd>`. ENTRYPOINT là lệnh cố định không bị override dễ dàng. CMD thường dùng khi muốn linh hoạt, ENTRYPOINT khi muốn container luôn chạy 1 lệnh cụ thể.

### Exercise 2.2: Build và run

```bash
# Từ project root
docker build -f 02-docker/develop/Dockerfile -t agent-develop .
docker run -p 8000:8000 agent-develop

# Kiểm tra image size
docker images agent-develop
# SIZE thực tế build trên máy: 1.66 GB (do dùng python:3.11 full + layer utils/)
```

### Exercise 2.3: Multi-stage build

Đọc `02-docker/production/Dockerfile`:

- **Stage 1 (builder):** Cài build tools (gcc, libpq-dev) và pip install tất cả dependencies với flag `--user` vào `/root/.local`. Stage này nặng nhưng KHÔNG được deploy.
- **Stage 2 (runtime):** Dùng `python:3.11-slim` (nhỏ hơn nhiều), tạo non-root user `appuser`, chỉ COPY `/root/.local` (packages đã build) từ stage 1 và source code. Không có gcc, build tools.
- **Tại sao image nhỏ hơn?** Vì stage 2 chỉ chứa Python slim + packages + code. Không có build tools, package managers, caches. Image giảm từ 1.66 GB xuống còn 236 MB (giảm ~86%).

So sánh size:
```bash
docker build -f 02-docker/production/Dockerfile -t agent-production .
docker images | grep agent
# agent-develop     1.66 GB  (single-stage, python:3.11 full)
# agent-production  236 MB   (multi-stage, python:3.11-slim)
# Giảm: 1424 MB (~86%)
```

### Exercise 2.4: Docker Compose stack

Đọc `02-docker/production/docker-compose.yml`, architecture gồm **4 services**:

```
                    ┌──────────┐
    Port 80/443 →   │  Nginx   │  (Reverse proxy + Load balancer)
                    └────┬─────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │Agent 1 │ │Agent 2 │ │Agent ..│  (FastAPI, scale replicas)
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
             └──────────┼──────────┘
                        │
              ┌─────────┼─────────┐
              ▼                   ▼
         ┌─────────┐        ┌─────────┐
         │  Redis  │        │ Qdrant  │
         └─────────┘        └─────────┘
```

- **agent**: FastAPI app, đọc env vars, depends_on redis + qdrant healthy
- **redis**: Session cache + rate limiting, maxmemory 256MB, LRU policy, persistent volume
- **qdrant**: Vector database cho RAG, persistent volume
- **nginx**: Reverse proxy, load balance giữa các agent instances, port 80/443

Communication: Tất cả trong `internal` network (bridge). Chỉ nginx expose port ra ngoài. Agent không expose port trực tiếp.

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

**Steps thực hiện:**
```bash
cd 03-cloud-deployment/railway

# 1. Install Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Init project
railway init

# 4. Set env vars
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key

# 5. Deploy
railway up

# 6. Get public URL
railway domain
```

**Test deployed agent:**
```bash
# Health check
curl https://lab12-agent-production.up.railway.app/health
# Expected: {"status":"ok","uptime_seconds":...,"platform":"Railway",...}

# Ask endpoint (cần X-API-Key)
curl https://lab12-agent-production.up.railway.app/ask -X POST \
  -H "X-API-Key: my-secret-api-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is cloud deployment?"}'
```

- **URL:** https://lab12-agent-production.up.railway.app
- **Platform:** Railway (Dockerfile builder, healthcheck `/health`, 30s timeout)
- **Verified:**
  - `GET /health` → 200 `{"status":"ok","version":"1.0.0","environment":"production"}`
  - `POST /ask` không có API key → 401
  - `POST /ask` có `X-API-Key: my-secret-api-key-2024` → 200 trả về câu trả lời mock
- **Screenshot:** `screenshots/dashboard.png`, `screenshots/health.png`, `screenshots/test.png`

### Exercise 3.2: So sánh railway.toml vs render.yaml

| Feature | railway.toml | render.yaml |
|---------|-------------|-------------|
| Format | TOML | YAML |
| Builder | `builder = "NIXPACKS"` (hoặc DOCKERFILE) | `runtime: python` hoặc `runtime: docker` |
| Start command | `startCommand = "uvicorn ..."` | `startCommand: uvicorn ...` |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Env vars | Set qua CLI hoặc Dashboard | Định nghĩa trong YAML, secrets set qua Dashboard (`sync: false`) |
| Auto deploy | Mặc định khi push | `autoDeploy: true` |
| Region | Chọn trong Dashboard | `region: singapore` trong YAML |
| Secrets | Chỉ qua CLI/Dashboard | `generateValue: true` để auto-generate |
| Đặc biệt | `restartPolicyType`, `restartPolicyMaxRetries` | `plan: free/starter`, có thể khai báo Redis add-on |

**Nhận xét:** render.yaml mạnh hơn ở Infrastructure as Code — có thể define cả Redis service, auto-generate secrets. railway.toml đơn giản hơn, phù hợp deploy nhanh.

### Exercise 3.3: GCP Cloud Run (Optional)

Đọc `cloudbuild.yaml` — CI/CD pipeline gồm 4 bước:
1. **Test:** Chạy pytest trong container Python
2. **Build:** Build Docker image, tag bằng COMMIT_SHA + latest, dùng layer cache
3. **Push:** Push image lên Google Container Registry (GCR)
4. **Deploy:** Deploy lên Cloud Run với min 1 / max 10 instances, 512Mi RAM, secrets từ Secret Manager

Đọc `service.yaml` — Knative Service definition:
- Auto-scale 1→10 instances
- Concurrency 80 requests/instance
- Health checks: livenessProbe `/health`, startupProbe `/ready`
- Secrets từ GCP Secret Manager (không hardcode)

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

Đọc `04-api-gateway/develop/app.py`:

- **API key được check ở đâu?** Trong function `verify_api_key()` — là một FastAPI dependency. Được inject vào endpoint `/ask` qua `Depends(verify_api_key)`. Check header `X-API-Key`.
- **Điều gì xảy ra nếu sai key?**
  - Không có key → HTTP 401 "Missing API key"
  - Sai key → HTTP 403 "Invalid API key"
- **Làm sao rotate key?** Thay đổi env var `AGENT_API_KEY` và restart app. Không cần sửa code.

Test:
```bash
# Không có key → 401
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'

# Có key → 200
curl http://localhost:8000/ask -X POST \
  -H "X-API-Key: demo-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```

### Exercise 4.2: JWT authentication

Đọc `04-api-gateway/production/auth.py` — JWT flow:

1. **Login:** POST `/auth/token` với `{"username":"student","password":"demo123"}` → server verify credentials → tạo JWT token chứa `{sub: username, role: user/admin, iat, exp}`
2. **Dùng token:** Gửi header `Authorization: Bearer <token>` → server decode JWT bằng `SECRET_KEY` + `HS256` → extract username + role
3. **Token expiry:** 60 phút. Sau đó trả 401 "Token expired"
4. **Lợi thế so với API Key:** Stateless (không cần query DB mỗi request), chứa role-based info, có expiry tự động

```bash
# Lấy token
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "demo123"}'

# Dùng token
TOKEN="<token>"
curl -H "Authorization: Bearer $TOKEN" \
  -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
```

### Exercise 4.3: Rate limiting

Đọc `04-api-gateway/production/rate_limiter.py`:

- **Algorithm:** Sliding Window Counter — dùng `deque` để lưu timestamps của mỗi request. Loại bỏ timestamps cũ hơn window (60s). Đếm số còn lại trong window.
- **Limit:** User: 10 req/min, Admin: 100 req/min (2 singleton instances `rate_limiter_user` và `rate_limiter_admin`)
- **Bypass cho admin:** Admin dùng `rate_limiter_admin` (100 req/min) thay vì `rate_limiter_user` (10 req/min). Phân biệt qua `role` trong JWT token.
- **Response khi hit limit:** HTTP 429 với headers `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `Retry-After`

### Exercise 4.4: Cost guard implementation

Đọc `04-api-gateway/production/cost_guard.py`:

```python
# Giải thích approach:
# 1. Mỗi user có UsageRecord theo ngày (input_tokens, output_tokens, request_count)
# 2. Trước khi gọi LLM: check_budget() kiểm tra:
#    - Global daily budget ($10/ngày) → 503 nếu vượt
#    - Per-user daily budget ($1/ngày) → 402 nếu vượt
#    - Warning khi dùng >= 80% budget
# 3. Sau khi gọi LLM: record_usage() ghi nhận tokens đã dùng
# 4. Cost tính theo: (input_tokens/1000) * $0.00015 + (output_tokens/1000) * $0.0006
# 5. Reset tự động đầu ngày mới (check day string)
#
# Trong production: thay in-memory dict bằng Redis
# để nhiều instances chia sẻ usage data
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

2 endpoints đã implement trong `05-scaling-reliability/develop/app.py`:

```python
@app.get("/health")
def health():
    # Liveness probe - "Agent còn sống không?"
    # Trả về status, uptime, version, checks (memory...)
    # Platform gọi định kỳ → non-200 = restart container
    return {"status": "ok", "uptime_seconds": ..., "checks": {...}}

@app.get("/ready")
def ready():
    # Readiness probe - "Sẵn sàng nhận request chưa?"
    # Trả 503 khi đang startup/shutdown
    # Load balancer dùng để quyết định route traffic
    if not _is_ready:
        raise HTTPException(503, "Agent not ready")
    return {"ready": True, "in_flight_requests": _in_flight_requests}
```

**Khác nhau:** `/health` fail → platform restart container. `/ready` fail → load balancer ngừng route traffic vào instance đó nhưng KHÔNG restart.

### Exercise 5.2: Graceful shutdown

```python
# Implementation trong 05-scaling-reliability/develop/app.py:
# 1. Bắt SIGTERM signal (platform gửi khi muốn dừng container)
# 2. Set _is_ready = False → /ready trả 503 → LB ngừng route traffic mới
# 3. Chờ _in_flight_requests giảm về 0 (tối đa 30 giây)
# 4. Đóng connections và exit

# uvicorn hỗ trợ: timeout_graceful_shutdown=30
# Khác với SIGKILL: SIGTERM có thể catch được, SIGKILL thì không
```

Test:
```bash
python app.py &
PID=$!
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Long task"}' &
kill -TERM $PID
# Quan sát: Request hoàn thành trước khi agent tắt
```

### Exercise 5.3: Stateless design

**Anti-pattern (Stateful):**
```python
# State trong memory — MẤT khi restart, KHÔNG share giữa instances
conversation_history = {}  # ❌
```

**Correct (Stateless):**
```python
# State trong Redis — persist qua restart, share giữa tất cả instances
# Trong 05-scaling-reliability/production/app.py:
def save_session(session_id, data, ttl_seconds=3600):
    _redis.setex(f"session:{session_id}", ttl_seconds, json.dumps(data))

def load_session(session_id):
    data = _redis.get(f"session:{session_id}")
    return json.loads(data) if data else {}
```

**Tại sao quan trọng khi scale:**
- Instance 1 nhận request 1 → lưu session trong memory
- Instance 2 nhận request 2 → KHÔNG có session! Bug!
- Với Redis: bất kỳ instance nào cũng đọc được session

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
```

Kết quả:
- 3 agent instances được start, mỗi instance có INSTANCE_ID riêng
- Nginx round-robin phân tán requests giữa 3 instances
- Response có field `served_by` cho thấy instance nào xử lý
- Nếu 1 instance die → `proxy_next_upstream` chuyển sang instance khác

Nginx config dùng `upstream agent_cluster` → `server agent:8000` → Docker DNS tự resolve tất cả replicas.

### Exercise 5.5: Test stateless

```bash
python test_stateless.py
```

Script tạo 1 session, gửi 5 requests liên tiếp. Quan sát:
- `served_by` thay đổi giữa các requests (round-robin)
- Conversation history vẫn liên tục dù instance khác nhau xử lý
- Kết luận: **Session preserved across all instances via Redis**
