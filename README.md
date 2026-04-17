# Day 12 — Deployment: Đưa Agent Lên Cloud

> **AICB-P1 · VinUniversity 2026**  
> Repository thực hành đi kèm bài giảng Day 12.  
> Mỗi phần có ví dụ **cơ bản** (hiểu concept) và **chuyên sâu** (production-ready).

---

## Nộp Bài — Submission Summary

| Mục | Link |
|---|---|
| **Deployed URL** | https://lab12-agent-production.up.railway.app |
| **Health check** | https://lab12-agent-production.up.railway.app/health |
| **Mission answers** | [MISSION_ANSWERS.md](MISSION_ANSWERS.md) (Part 1–5, 19 exercises) |
| **Deployment info** | [DEPLOYMENT.md](DEPLOYMENT.md) |
| **Screenshots** | [screenshots/](screenshots/) (dashboard, health, test) |
| **Main source** | [06-lab-complete/](06-lab-complete/) |

---

## Hướng Dẫn Chấm — Reproduction Guide

Grader clone repo về máy sạch → chạy local và test deployed URL theo các bước dưới.

### 1. Prerequisites

- Python 3.11+
- Docker Desktop (tùy chọn, chỉ cần nếu muốn build image)
- `curl` hoặc PowerShell `Invoke-RestMethod`

### 2. Test Deployed URL (không cần clone)

```bash
# a) Health check — không cần auth
curl https://lab12-agent-production.up.railway.app/health

# b) Auth required — trả về 401
curl -X POST https://lab12-agent-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"test"}'

# c) Với API key — trả về 200
curl -X POST https://lab12-agent-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-api-key-2024" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is Docker?"}'
```

PowerShell (Windows) dùng `Invoke-RestMethod` để tránh escape JSON:
```powershell
Invoke-RestMethod -Uri https://lab12-agent-production.up.railway.app/ask `
  -Method Post `
  -Headers @{"X-API-Key"="my-secret-api-key-2024"} `
  -ContentType "application/json" `
  -Body '{"question":"What is Docker?"}'
```

### 3. Chạy Lab 06 trên máy local

```bash
git clone <repo-url>
cd day12-agent-deployment/06-lab-complete

# Virtual env (khuyến nghị)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# Set env vars tối thiểu (production mode bắt buộc 2 key này khác default)
# Windows PowerShell:
$env:AGENT_API_KEY="my-secret-api-key-2024"
$env:JWT_SECRET="local-test-jwt-secret"
$env:ENVIRONMENT="production"
# macOS/Linux:
export AGENT_API_KEY=my-secret-api-key-2024
export JWT_SECRET=local-test-jwt-secret
export ENVIRONMENT=production

# Chạy từ folder 06-lab-complete
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test ở terminal khác
curl http://localhost:8000/health
```

### 4. Chạy kiểm tra production-readiness

```bash
cd 06-lab-complete
# Windows cần encoding UTF-8 cho emoji
# PowerShell: $env:PYTHONIOENCODING="utf-8"
python check_production_ready.py
# Expected: 20/20 checks passed (100%)
```

### 5. Build Docker (tùy chọn)

```bash
# Từ project root
cd day12-agent-deployment

# Image single-stage (basic) — ~1.66 GB
docker build -f 02-docker/develop/Dockerfile -t agent-develop .

# Image multi-stage (production) — ~236 MB
docker build -f 02-docker/production/Dockerfile -t agent-production .

docker images | grep agent
```

### 6. Biến môi trường bắt buộc (production)

| Var | Mặc định | Bắt buộc? |
|---|---|---|
| `AGENT_API_KEY` | `dev-key-change-me` | ✅ phải khác mặc định |
| `JWT_SECRET` | `dev-jwt-secret` | ✅ phải khác mặc định |
| `ENVIRONMENT` | `development` | set `production` khi deploy |
| `PORT` | `8000` | Railway/Render tự inject |
| `RATE_LIMIT_PER_MINUTE` | `20` | tùy |
| `DAILY_BUDGET_USD` | `5.0` | tùy |

Nếu chạy với `ENVIRONMENT=production` mà không set `AGENT_API_KEY` và `JWT_SECRET`, app sẽ fail khi khởi động (xem `app/config.py:43`).

---

## Cấu Trúc Project

```
day12-agent-deployment/
├── 01-localhost-vs-production/     # Section 1: Dev ≠ Production
│   ├── develop/                      #   Agent "đúng kiểu localhost"
│   └── production/                   #   12-Factor compliant agent
│
├── 02-docker/                      # Section 2: Containerization
│   ├── develop/                      #   Dockerfile đơn giản
│   └── production/                   #   Multi-stage + Docker Compose stack
│
├── 03-cloud-deployment/            # Section 3: Cloud Options
│   ├── railway/                    #   Deploy Railway (< 5 phút)
│   ├── render/                     #   Deploy Render + render.yaml
│   └── production-cloud-run/         #   GCP Cloud Run + CI/CD
│
├── 04-api-gateway/                 # Section 4: Security
│   ├── develop/                      #   API Key authentication
│   └── production/                   #   JWT + Rate Limiting + Cost Guard
│
├── 05-scaling-reliability/         # Section 5: Scale & Reliability
│   ├── develop/                      #   Health check + graceful shutdown
│   └── production/                   #   Stateless + Redis + Nginx LB
│
├── 06-lab-complete/                # Lab 12: Production-ready agent
│   └── (full project kết hợp tất cả)
│
└── utils/                          # Mock LLM dùng cho lesson 01-05 (demo offline)
```

---

## 🚀 Bắt Đầu Nhanh

**Muốn thử ngay?** → [QUICK_START.md](QUICK_START.md) (5 phút)

**Muốn học kỹ?** → [CODE_LAB.md](CODE_LAB.md) (3-4 giờ)

## Cách Học

| Bước | Làm gì |
|------|--------|
| 0 | **[Khuyến nghị]** Đọc [QUICK_START.md](QUICK_START.md) để thử nhanh |
| 1 | Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu chi tiết |
| 2 | Chạy ví dụ **basic** trước — hiểu concept |
| 3 | So sánh với ví dụ **advanced** — thấy sự khác biệt |
| 4 | Tự làm Lab 06 từ đầu trước khi xem solution |
| 5 | Tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md) khi cần |
| 6 | Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md) khi gặp lỗi |

---

## Yêu Cầu

```bash
python 3.11+
docker & docker compose
```

Mỗi folder có `requirements.txt` riêng.

- **Lesson 01–05** (folder `01-` đến `05-`): dùng mock LLM — học concept deployment không cần API key.
- **Lab 06 (`06-lab-complete/`)** — bài nộp production: gọi **OpenAI API thật** (`gpt-4o-mini`), yêu cầu `OPENAI_API_KEY`.

---

## Sections

| # | Folder | Concept chính |
|---|--------|--------------|
| 1 | `01-localhost-vs-production` | Dev/prod gap, 12-factor, secrets |
| 2 | `02-docker` | Dockerfile, multi-stage, docker-compose |
| 3 | `03-cloud-deployment` | Railway, Render, Cloud Run |
| 4 | `04-api-gateway` | Auth, rate limiting, cost protection |
| 5 | `05-scaling-reliability` | Health check, stateless, rolling deploy |
| 6 | `06-lab-complete` | **Full production agent** |

---

## 📚 Lab Materials

Chúng tôi đã chuẩn bị đầy đủ tài liệu hướng dẫn:

### Cho Sinh Viên

| Tài liệu | Mô tả | Thời gian |
|----------|-------|-----------|
| **[CODE_LAB.md](CODE_LAB.md)** | Hướng dẫn lab chi tiết từng bước | 3-4 giờ |
| **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** | Cheat sheet các lệnh và patterns | Tra cứu |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Giải quyết lỗi thường gặp | Khi cần |

### Cho Giảng Viên

| Tài liệu | Mô tả |
|----------|-------|
| **[INSTRUCTOR_GUIDE.md](INSTRUCTOR_GUIDE.md)** | Hướng dẫn chấm điểm và đánh giá |

### Cách Sử Dụng

1. **Trước lab:** Đọc [CODE_LAB.md](CODE_LAB.md) để hiểu tổng quan
2. **Trong lab:** Làm theo từng Part, tham khảo [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **Gặp lỗi:** Xem [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Sau lab:** Nộp Part 6 Final Project để chấm điểm
