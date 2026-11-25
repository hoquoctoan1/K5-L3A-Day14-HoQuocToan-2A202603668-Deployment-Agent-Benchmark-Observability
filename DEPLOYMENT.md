# Deployment Information

Trạng thái: **chưa deploy**, chưa có URL public hoặc ảnh cloud. File này là hướng dẫn thực thi, không phải bằng chứng deploy thành công.

Người dùng xác nhận chưa có tài khoản/phiên đăng nhập Railway hoặc Render. Kiểm tra local đầy đủ đã đạt PASS 12/12 (`reports/production_linux.txt`); kết quả này không thay thế bốn phép kiểm tra public URL.

## Phạm vi

Deploy thư mục `06-lab-complete/` với Dockerfile của Part 6. Cần Redis trên cùng nền tảng; cấp `REDIS_URL` của Redis đó cho agent. Chọn Railway hoặc Render. Không cần triển khai cả hai để có phần so sánh cấu hình.

## Các biến cần đặt

`AGENT_API_KEY` (secret), `REDIS_URL` (secret connection string), `PORT` (platform cấp), `ENVIRONMENT=production`, `RATE_LIMIT_PER_MINUTE`, `DAILY_BUDGET_USD`; các tùy chọn giá token/log theo `.env.example`. Đây là danh sách cần đặt, **chưa xác nhận đã đặt trên cloud**.

## Triển khai

Railway: đăng nhập tài khoản, tạo project và service Redis; cấu hình root directory `06-lab-complete`, dùng Dockerfile, cấp biến môi trường rồi deploy và tạo public domain.

Render: dùng Blueprint ở `06-lab-complete/render.yaml`, xác nhận build context/root directory đúng cấu hình; cấp secret và Redis, đợi deploy hoàn tất. Chỉ chọn tài nguyên miễn phí/trial phù hợp, không tự nâng gói trả phí.

## Tự kiểm tra sau deploy

Đặt BASE thành URL thực và AGENT_API_KEY bằng secret trong terminal (không lưu vào file tracked):

```bash
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -d '{"question":"Hello"}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST "$BASE/ask" -H 'Content-Type: application/json' -H "X-API-Key: $AGENT_API_KEY" -d '{"question":"Hello"}'
```

Kỳ vọng lần lượt 200, 200, 401, 200. Sau đó chạy checker `--public-url "$BASE"` từ Part 6, lưu output thật. Chưa chạy bốn kiểm tra này.

## Bằng chứng còn thiếu

- URL public thật và kết quả bốn HTTP checks.
- `screenshots/dashboard.png`, `screenshots/running.png`, `screenshots/test.png`, không để lộ key/token.
- Xác nhận repo Public, tên lớp L3A/L3B đúng theo yêu cầu; tên repo hiện tại chưa theo chính xác mẫu SUBMISSION. Không tự suy đoán lớp hoặc đổi repo từ xa.
