# Deployment Information

## Public URL

**https://day14-production-agent.onrender.com**

## Platform

**Render** (Blueprint `06-lab-complete/render.yaml`), region Singapore, free plan.

| Service | Loại | Vai trò |
|---|---|---|
| `day14-production-agent` | Web Service (Docker, `rootDir: 06-lab-complete`) | Agent Part 6 |
| `day14-agent-redis` | Key Value (Redis) | Rate limit, cost guard, state; chỉ truy cập qua private network (`ipAllowList: []`) |

Gói free của Render tự ngủ sau khoảng 15 phút không có request; lần gọi đầu sau đó mất khoảng 1 phút để khởi động lại.

## Test Commands

Đặt `BASE` là URL trên và `AGENT_API_KEY` là key lấy từ tab Environment của Render (chỉ đặt trong terminal, không ghi vào file):

```bash
BASE=https://day14-production-agent.onrender.com

# 1. Health check → 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"

# 2. Readiness (Redis kết nối được) → 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"

# 3. /ask không có key → 401
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -d '{"question":"Hello"}'

# 4. /ask có key → 200
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" \
  -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Chạy cả 4 kiểm tra cùng rate limit bằng script: `python scripts/verify_public_url.py "$BASE"` (key đọc từ biến môi trường, được che trong output; kết quả ghi ra `reports/public_url_checks.json`).

## Kết quả kiểm tra

| Kiểm tra | Kỳ vọng | Kết quả |
|---|---|---|
| `GET /health` | 200 | ✅ 200 `{"status":"healthy","environment":"production"}` |
| `GET /ready` | 200 | ✅ 200 `{"status":"ready"}` |
| `POST /ask` không key | 401 | ✅ 401 |
| `POST /ask` có key | 200 | ⏳ chờ chạy với key thật |
| Rate limit | 429 | ⏳ chờ chạy với key thật |

Checker gốc chạy đầy đủ (Linux container, Docker thật) kèm `--public-url https://day14-production-agent.onrender.com`: **PASS 12/12, 44/44 checks**, gồm `Public URL: GET /health → 200`. Bằng chứng: `reports/production_public_url.txt`.

## Environment Variables Set

Đặt trên Render qua Blueprint, không ghi trong code:

| Biến | Nguồn |
|---|---|
| `AGENT_API_KEY` | Render tự sinh (`generateValue: true`), secret |
| `REDIS_URL` | Tham chiếu `connectionString` của `day14-agent-redis` (`fromService`) |
| `ENVIRONMENT` | `production` |
| `RATE_LIMIT_PER_MINUTE` | Đặt trong Blueprint |
| `DAILY_BUDGET_USD` | `1.0` |
| `PORT` | Render cấp tự động; app đọc biến này |

## Screenshots

- [Deployment dashboard](screenshots/dashboard.png) — ảnh học viên chụp trên Render lúc deploy: Blueprint tạo Key Value + web service, log service nhận health check 200
- [Service running](screenshots/running.png) — `/health` và `/ready` của URL public
- [Test results](screenshots/test.png) — `curl -i` thật tới URL public (200 / 200 / 401) và tóm tắt checker `--public-url` PASS 44/44
