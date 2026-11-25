# Kế hoạch và bảng quản lý Day 14

Theo README (điều chỉnh K5), RULES, CHECKPOINTS, SUBMISSION và RUBRIC. Mục tiêu: hoàn thành bài trong đúng đường dẫn, bằng chứng thật, commit riêng sau mỗi task đã kiểm tra. Không sửa checker hoặc golden dataset; không commit secret.

| Giai đoạn | Task / phụ trách | Sản phẩm và điều kiện hoàn thành | Trạng thái |
|---|---|---|---|
| 0 — Khảo sát | T0 / điều phối | Đọc yêu cầu, kiểm tra môi trường, tạo bảng này | Hoàn thành |
| 1 — Final project | T1 / agent production | Config, auth, Redis, rate limit, cost guard, health/ready, JSON log, shutdown trong Part 6; kiểm tra khả dụng | Xong `ca2547f`; kiểm tra Linux PASS `c4da508` |
| 1 — Đóng gói | T2 / agent packaging | Multi-stage Dockerfile, Compose Redis, dockerignore, Railway/Render config | Xong `018add7`, runtime `ed7c3fc` |
| 2 — Kiến thức và bằng chứng | T3 / điều phối | MISSION_ANSWERS Part 1–5, AI log, kết quả chạy thực tế; phần chưa chạy đánh dấu rõ | Local xong: HTTP `2132484`, image/scaling `d551852`, Compose đầy đủ `e41b976`; cloud Part3 còn chờ |
| 3 — Benchmark | T4 / agent benchmark | Baseline eval v1/v2 trước sửa; histogram, sửa KB, fixed eval 23/23, CI gate; JSON thực | Xong `e14db2e`, `013d0e5`; fixed 23/23, CI chưa chạy remote |
| 3 — Load test | T5 / agent benchmark | 4 concurrency và 3 slow rate; 300 requests/lần; báo cáo khớp JSON | Xong `ee50ae6`, `cb5aa26`; c50/c100 vi phạm SLO |
| 4 — Kiểm tra đầy đủ | T6 / điều phối + production | Checker đầy đủ PASS 12/12 trên Linux + Docker; image size, Part 2/5 runtime | Xong Part6 `c4da508` PASS12/12,43/43; image/scaling `d551852` |
| 5 — Cloud | T7 / điều phối | Deploy Part 6 + Redis, public URL, 4 HTTP checks, 3 ảnh và DEPLOYMENT.md | Xong: Render `e773daf`, URL https://day14-production-agent.onrender.com; checker `--public-url` PASS 44/44; 3 ảnh `3f56f1d` |
| 6 — Observability | T8 / benchmark + điều phối | Locust scale 1/3 CSV, Grafana, trace chậm/lỗi + log, ≥2 alert firing cùng ảnh | API/log và CSV xong `606c40f`; scale `d3ee988`/`61ca7f4`; error-only `ac6bc62`; 4 ảnh Part 7 đã chụp (Chrome headless) |
| 7 — Đóng gói bài | T9 / điều phối | Soát rubric, secret, đủ file/ảnh, cập nhật bảng và commit kết quả | Xong: đủ JSON/CSV/7 ảnh, số liệu khớp, repo public; còn học viên tự xác nhận AI log |

## Quy trình commit

Mỗi agent chỉ sửa và stage các file được giao. Sau khi hoàn thành một task và kiểm tra phù hợp, commit ngay, báo hash + kết quả cho điều phối. Không stage toàn repo vì các agent dùng chung workspace. Điều phối tích hợp tuần tự và cập nhật bảng; không push hoặc nộp LMS tự động.

## Môi trường ghi nhận

- Python Windows 3.13.7; README yêu cầu Python 3.11+ và Linux/WSL để kiểm tra SIGTERM.
- `docker --version`: không tìm thấy lệnh trong PATH.
- `wsl --list --quiet`: `Wsl/E_ACCESSDENIED` trong phiên hiện tại.
- Repository ban đầu sạch; commit đầu: `83e677f`.
- Chưa có bằng chứng public URL hoặc phiên cloud. Không điền URL, số đo hay ảnh giả.

Cập nhật: tìm thấy Docker Desktop tại `%LOCALAPPDATA%/Programs/DockerDesktop`, đã khởi động daemon 29.9.3. WSL truy cập ngoài sandbox được nhưng chỉ có distro docker-desktop, không có Python. Dùng runner Python Linux trong Docker để kiểm tra signal thật. Không dùng kết quả Windows `--skip-docker` thiếu Redis ban đầu làm kết quả cuối.

Một lượt cài dependency ban đầu dùng nhầm interpreter Python ở bài Day9 ngoài workspace. Agent đã khôi phục pydantic/pydantic-core/python-dotenv về phiên bản trước đó; các package mới cài thêm vẫn có trong interpreter đó. Các lần chạy tiếp dùng `.venv-benchmark` riêng và Linux container. Không có code bài Day9 bị sửa.

Ban đầu người dùng chọn bỏ qua ảnh do không chụp được cửa sổ trình duyệt; về sau đã chụp đủ (xem mục cuối).

## Điều kiện kết thúc

Bài chỉ hoàn thành toàn bộ khi có PASS 12/12 bản đầy đủ, URL cloud qua 4 kiểm tra CP6, đủ JSON/CSV/7 ảnh theo SUBMISSION và báo cáo khớp bằng chứng. Hoàn thành code không đồng nghĩa hoàn thành bài nộp.

## Kết quả bàn giao local

- Part 6: `reports/production_linux.txt` có PASS12/12,43/43; checker và golden dataset giữ nguyên so với commit gốc.
- Part 1/4: HTTP thật xác nhận query200/JSON422, thiếu auth401, 10 request200 rồi429; không lưu token.
- Part 2/5: image production giảm85.62%; full agent/Redis/Qdrant/Nginx200; ba instance giữ đủ10 message cùng session.
- CP7: đủ10 JSON benchmark/eval; fixed23/23, không regression; c50/c100 vi phạm SLO được ghi đúng.
- CP8: scale1/3 CSV, Grafana/PromQL API, trace chậm/lỗi khớp log, promtoolSUCCESS. Hai alert mới cùngfiring; error83.2s, latency143.7s; cost alert có sẵn không tính là hiệu quả fault mới.
- Rà soát: JSON parse thành công, CSV tổng hợp khớp báo cáo; `git diff --check` sạch; không có `.env` thật trong tracked files/lịch sử commit.
- AI log nằm trong MISSION_ANSWERS; học viên chưa tự xác nhận đọc hiểu hoặc chạy lại.

## Hoàn thiện bài nộp

Lớp **L3A**. Repo public: `https://github.com/hoquoctoan1/K5-L3A-Day14-HoQuocToan-2A202603668-Deployment-Agent-Benchmark-Observability`. Người dùng chọn giữ tên này (khác mẫu SUBMISSION ở `Day14` và `-Agent-`), chấp nhận rủi ro trừ điểm tên repo.

- Ảnh Part 7 (4): chụp bằng Chrome headless từ stack chạy thật; chaos riêng cho ảnh alert (error 94.7 s, latency 149.9 s), bằng chứng `reports/screenshot_run/`, `reports/chaos_screenshot_alerts.json`.
- Deploy Render bằng Blueprint `06-lab-complete/render.yaml` (web + Key Value, free, Singapore). Học viên tự đăng nhập và tạo Blueprint. `/health` 200, `/ready` 200, `/ask` không key 401; checker gốc với `--public-url` PASS 12/12, 44/44 (`reports/production_public_url.txt`).
- Ảnh deploy (3): `dashboard.png` ghép từ ảnh học viên chụp trên Render; `running.png` và `test.png` từ request thật tới URL public.
- `RATE_LIMIT_PER_MINUTE` trên Render chỉnh từ 60 về 10 cho khớp `.env.example` và yêu cầu đề (Blueprint tự đồng bộ khi push).

## Còn lại

1. `/ask` có key → 200 và rate limit → 429 trên URL public chưa chạy: cần key thật từ Render (chỉ đặt trong biến môi trường, không ghi vào file), rồi chạy `python scripts/verify_public_url.py https://day14-production-agent.onrender.com`.
2. Học viên tự đọc lại code/báo cáo và tự ghi phần xác nhận trong AI log (`MISSION_ANSWERS.md`), rồi nộp link repo trên LMS.
