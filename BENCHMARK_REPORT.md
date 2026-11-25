# Benchmark & Observability Report — Day 14

**Họ tên:** Ho Quoc Toan  
**Ngày chạy:** 25/11/2026 (GMT+7)  
**Môi trường:** Windows, Python 3.13.7, virtualenv `.venv-benchmark`, agent một process Uvicorn, mock-llm-small. Docker chưa có trong PATH; WSL bị từ chối truy cập. Đây là phép đo local, chưa phải kết quả production.

## 1. SLO của agent

| SLI | SLO | Lý do |
|---|---|---|
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của load_test.py, giới hạn thời gian chờ phần lớn người dùng |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của load_test.py |
| Accuracy golden dataset | ≥ 85% trong CI; 100% bản KB cuối | CI chặn chất lượng thấp; bài lab yêu cầu 23/23 |

## 2. Benchmark hiệu năng

Mỗi lần 300 request, một warm-up không tính vào báo cáo. Concurrency dùng `http://localhost:8002`, `AGENT_VERSION=v2`, `MOCK_ERROR_RATE=0.01`, `MOCK_SLOW_RATE=0.03`; các biến latency còn lại dùng mặc định. Các phép đo chạy lần lượt. JSON gốc nằm trong `reports/`.

### 2.1 Concurrency vs latency

| Concurrency | RPS | p50 ms | p95 ms | p99 ms | Error rate | SLO |
|---|---:|---:|---:|---:|---:|---|
| 1 | 3.83 | 207.1 | 264.7 | 1702.1 | 1.67% | PASS |
| 10 | 32.26 | 214.6 | 459.4 | 1714.0 | 0% | PASS |
| 50 | 35.95 | 525.5 | 4297.0 | 6191.3 | 1% | FAIL |
| 100 | 36.04 | 1058.5 | 5823.4 | 6292.3 | 1.33% | FAIL |

RPS tăng mạnh từ 1 lên 10 rồi gần như đứng lại; p95 tăng mạnh ở 50/100. Đây là kết quả toàn bộ đường HTTP trên máy chạy lab, gồm client, server, logging và scheduling Windows. Chưa có profiling nên chưa kết luận riêng LLM là nút thắt. Không ngoại suy kết quả này thành năng lực cloud.

Lệnh từ gốc repo (thay C bằng 1, 10, 50, 100):

```powershell
.venv-benchmark/Scripts/python 06-lab-complete/benchmark-observability/develop/load_test.py --url http://localhost:8002 --requests 300 --concurrency C --out reports/load_v2_cC.json
```

### 2.2 Tail latency

Mỗi hàng dùng process mới, cổng 8003, concurrency 20, 300 request; error rate mock vẫn 0.01. Chạy lại bằng `python 06-lab-complete/benchmark-observability/develop/run_tail_comparison.py` với môi trường đã cài requirements.

| MOCK_SLOW_RATE | avg ms | p95 ms | p99 ms |
|---|---:|---:|---:|
| 0 | 241.4 | 465.3 | 589.8 |
| 0.03 | 269.0 | 527.4 | 1716.3 |
| 0.1 | 322.3 | 1684.3 | 1715.8 |

Từ 0 lên 0.03, average tăng 27.6 ms nhưng p99 tăng 1126.5 ms. Một số ít request chậm bị pha loãng trong average; p99 phản ánh đuôi phân bố. Khi tỷ lệ chậm lên 10%, p95 cũng lọt vào nhóm chậm. SLO nên dựa trên percentile và error rate; vẫn theo dõi average để hiểu toàn bộ phân bố. Các lần đo dùng ngẫu nhiên, không cùng seed; 300 request chưa đủ để suy ra p99 ổn định lâu dài.

## 3. Benchmark chất lượng

Đã chạy v1/v2 trước khi thay KB, giữ nguyên dataset. Eval baseline dùng `MOCK_ERROR_RATE=0`; eval bản sửa dùng 0.01 và retry mặc định 1. Mọi bản dùng slow rate mặc định 0.03. Latency eval bao gồm request đầu lạnh và tail ngẫu nhiên, nên chênh lệch p95 giữa ba lần chưa chứng minh KB làm nhanh hơn.

| Chỉ số | v1 | v2 gốc | v2 sửa KB |
|---|---:|---:|---:|
| Accuracy | 1/23 (4.35%) | 21/23 (91.30%) | 23/23 (100%) |
| Avg tokens/câu | 57.9 | 108.8 | 113.7 |
| Tổng cost USD | 0.000415 | 0.000758 | 0.000790 |
| Cost/câu đúng USD | 0.00041475 | 0.00003607 | 0.00003436 |
| Quality gate | FAIL (80%) | PASS (80%, so với v1) | PASS (100%, so với v2) |

| ID sai ở v2 gốc | Keyword thiếu | Sửa |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm tài liệu JWT so với API key vào KNOWLEDGE_BASE |
| scaling-03 | cpu, memory, custom metrics | Thêm tài liệu Kubernetes HPA |

Sửa cùng tài liệu ở develop và production để tránh hai phiên bản trả lời khác nhau. Bản cuối không có regression (`quality_gate.regressions=[]` trong `reports/eval_v2_fixed.json`). Retrieval tăng prompt/token và cost mỗi câu, nhưng chi phí mỗi câu **đúng** giảm nhiều so với v1.

`.github/workflows/eval.yml` khởi động v2 trên Ubuntu/Python 3.11, chờ `/ready`, chạy eval với `--min-accuracy 0.85`, rồi lưu artifact. Exit code 1 làm job fail; cần bật branch protection yêu cầu job `eval` để thực sự chặn merge. Chưa chạy GitHub Actions từ máy này. Local đã chạy gate 100% với baseline v2 thành công.

Metric thêm: histogram `agent_question_length_chars` với bucket 20/50/100/200/500/1000/2000; đã xác nhận có series `_count` qua `/metrics`. Không đưa độ dài hoặc nội dung câu hỏi vào label để tránh cardinality cao. Counter ví dụ `llm_requests_total`; Gauge `agent_in_flight_requests`; Histogram `http_request_duration_seconds`. Dùng URL thật làm label sẽ sinh time series mới cho từng URL bot quét; route template và `unmatched` giữ số label hữu hạn.

## 4. Observability stack (production)

**Chưa thực hiện:** thiếu Docker và chưa truy cập được WSL. Không có screenshot Grafana/Jaeger/Prometheus, trace_id thực nghiệm hoặc thời gian alert firing. Phần CP8 chưa hoàn thành.

### 4.1 Screenshot cần bổ sung

- [ ] Grafana có tải và Golden Signals.
- [ ] Jaeger trace chậm và span chậm nhất.
- [ ] Jaeger trace lỗi có exception.
- [ ] Prometheus Alerts thấy ít nhất **2 alert cùng firing** theo CHECKPOINTS/RUBRIC.

### 4.2 Thí nghiệm cần chạy

| Thay đổi | Alert firing | Thời gian tới firing | Panel |
|---|---|---|---|
| MOCK_ERROR_RATE=0.2 | Chưa đo | Chưa đo | Chưa quan sát |
| MOCK_SLOW_RATE=0.3 hoặc LLM_MODEL=mock-llm-large | Chưa đo | Chưa đo | Chưa quan sát |

Đổi v1 có thể giảm chất lượng mà latency/error/cost vẫn khỏe. Cần eval trên golden dataset trong CI, canary/shadow evaluation và lấy mẫu câu trả lời thực tế để phát hiện regression ngữ nghĩa. Hạ tầng khỏe không đảm bảo câu trả lời đúng.

Các câu hỏi Exercise 7.4 chưa có số đo dashboard: cần đọc p95/avg thực tế, so RPS từng instance để đánh giá chia tải. Về thiết kế, retrieval thêm context làm input tokens thường lớn hơn output; cần kiểm tra panel để xác nhận trên lần chạy. Nginx chặn public `/metrics` để tránh lộ thông tin vận hành; Prometheus scrape trực tiếp agent nội bộ.

### 4.3 Trace cần bổ sung

Chưa có trace_id, tổng thời gian, span chiếm thời gian lớn nhất hoặc dòng log JSON khớp trace. Không điền số ước lượng.

## 5. Benchmark scaling

Chưa chạy Locust headless 100 users/2 phút vì thiếu Docker. Chưa có `scale_1_stats.csv`/`scale_3_stats.csv`; chưa kết luận hiệu quả scale.

| Instance | RPS | p50 | p95 | p99 | Failures |
|---|---|---|---|---|---|
| 1 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |
| 3 | Chưa đo | Chưa đo | Chưa đo | Chưa đo | Chưa đo |

## 6. Kết luận

1. p99 phát hiện request chậm mà average che khuất; cần đo cả tỷ lệ lỗi.
2. Retrieval tăng tokens nhưng cải thiện cost/câu đúng; quality gate kiểm tra cả accuracy lẫn regression.
3. Concurrency cao có thể làm latency tăng nhanh khi throughput chững lại; cần profiling và so sánh scale bằng cùng workload.

Nếu triển khai thật, bổ sung saturation/queue depth, lỗi Redis, budget burn rate và đánh giá chất lượng có lấy mẫu. Báo cáo này hoàn thành phần đo CP7; CP8 và bằng chứng production vẫn đang chờ môi trường.
