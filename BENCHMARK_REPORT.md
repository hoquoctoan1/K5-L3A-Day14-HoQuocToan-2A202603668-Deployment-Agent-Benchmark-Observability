# Benchmark & Observability Report — Day 14

**Họ tên:** Ho Quoc Toan  
**Ngày chạy:** 25/11/2026 (GMT+7)  
**Môi trường:** Windows, Python 3.13.7, virtualenv `.venv-benchmark`, agent một process Uvicorn, mock-llm-small. CP8 chạy Docker Desktop Engine 29.9.3 (8 CPU, 8,264,507,392 byte RAM); mỗi container agent giới hạn 0.5 CPU/256 MB. Docker được tìm ngoài PATH và khởi động thành công. Đây là phép đo local/container, chưa phải kết quả cloud.

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

Đã chạy stack thực với Prometheus 3.16.0, Grafana 13.2.4, Jaeger 2.23.0, Locust 2.47.0, Nginx 1.28. Dữ liệu API/log nằm trong `reports/observability_scale1_evidence.json`, `observability_scale3_evidence.json` và hai file `jaeger_*_trace.json`. Tiện ích thu trace dùng API `/api/v3` theo [tài liệu Jaeger](https://www.jaegertracing.io/docs/2.23/architecture/apis/), đã kiểm chứng trên service chạy thật. **Người dùng yêu cầu bỏ screenshot**; bằng chứng API/log không thay thế yêu cầu ảnh trong rubric, nên phần ảnh còn thiếu.

### 4.1 Screenshot cần bổ sung

- [ ] Grafana có tải và Golden Signals.
- [ ] Jaeger trace chậm và span chậm nhất.
- [ ] Jaeger trace lỗi có exception.
- [ ] Prometheus Alerts thấy ít nhất **2 alert cùng firing** theo CHECKPOINTS/RUBRIC.

### 4.2 Thí nghiệm phá hệ thống đã chạy

| Thay đổi | Alert firing | Thời gian tới firing | Metric phản ánh |
|---|---|---|---|
| A: MOCK_ERROR_RATE=0.2, slow giữ 0.03 | AgentHighErrorRate | 83.2 s | Error rate /ask |
| B: giữ error 0.2, thêm MOCK_SLOW_RATE=0.3 | AgentHighErrorRate + AgentHighLatencyP95 | 83.2 s / 143.7 s | Latency p95 và error rate |

Thí nghiệm A dùng 100 users, 2 phút. `reports/chaos_error_only_alerts.json` lưu snapshot trước khi đổi cấu hình: error/latency đều inactive; cost alert đã firing từ tải benchmark nên **không** tính thời gian firing của cost là kết quả fault mới. Timer tính từ trước lệnh recreate agent, poll mỗi 5 giây nên thời gian có độ phân giải khoảng 5 giây cộng độ trễ truy vấn. CSV lỗi còn ghi các 502 trong khoảng 08:21:34–08:21:45 UTC khi Nginx chờ cập nhật DNS sau recreate; HTTP 503 tiếp diễn do mock error. Vì vậy tổng failure rate giai đoạn A bao gồm cả transient lúc đổi cấu hình, không đồng nhất với chính xác 20% lỗi mock.

Thí nghiệm B dùng cùng tải trong 4 phút, thêm độ chậm vào cấu hình lỗi của A. Trước B đã ngừng tải và poll 9 lần cho tới khi error/latency inactive, chỉ cost còn firing. `reports/chaos_alerts.json` lưu toàn bộ quá trình inactive → pending → firing; `reports/observability_evidence.json` có snapshot **cả error và latency cùng firing**. Giữ nguyên `for: 1m` cho error, `for: 2m` cho latency, scrape/evaluation mỗi 5 giây. Không sửa rule để làm alert nhanh hơn. Đây là hai cấu hình thí nghiệm có kiểm soát (A lỗi; B thêm chậm), chưa phải phép đo riêng hoàn toàn độc lập ảnh hưởng từng fault trên mọi metric. Test `promtool test rules` thực trả `SUCCESS` trong `reports/alert_rules_test.txt`.

Đổi v1 có thể giảm chất lượng mà latency/error/cost vẫn khỏe. Cần eval trên golden dataset trong CI, canary/shadow evaluation và lấy mẫu câu trả lời thực tế để phát hiện regression ngữ nghĩa. Hạ tầng khỏe không đảm bảo câu trả lời đúng.

Từ PromQL lúc tải 3 instance (`observability_scale3_evidence.json`): p95 = 1.19647 s, average = 0.34752 s. Khoảng cách cho thấy đuôi request chậm; histogram Prometheus nội suy bucket nên p95 không cần bằng percentile Locust trên toàn bộ lần chạy. RPS mỗi instance là 19.9455, 16.6728 và 16.6035; cả ba đều nhận tải, chưa hoàn toàn đều ở thời điểm lấy mẫu (instance đầu có lịch sử chạy lâu hơn). Input = 4094.1494 token/s, output = 2137.9999 token/s; retrieval thêm context khiến input nhiều hơn. Gọi public `/metrics` thực trả **404**; Prometheus scrape nội bộ để tránh lộ thông tin vận hành. Grafana API trả database `ok` và dashboard UID `day14-agent-overview` có tồn tại; chưa quan sát UI theo yêu cầu bỏ ảnh.

### 4.3 Phân tích trace và log tương ứng

Trace chậm nhất **trong 200 trace trả về ở lần lấy mẫu cuối** (không khẳng định là chậm nhất toàn bộ lịch sử):

- `trace_id`: `ef3c41d5adecbb562ad72e5e4817876d`
- Tổng thời gian: **1867.875145 ms**.
- Thành phần chậm nhất: span `chat mock-llm-small`, **1658.772637 ms**, **88.81%** tổng trace. Đây là child thực hiện LLM; không dùng enclosing HTTP/agent.run có thời gian bao trùm để kết luận nút thắt.
- Nguồn raw OTLP: `reports/jaeger_slow_trace.json`; log khớp trong `reports/observability_evidence.json`:

```json
{"ts":"2026-11-25T08:27:10.579887+00:00","level":"INFO","service":"observable-agent","instance":"e898582085f5","event":"llm_call","trace_id":"ef3c41d5adecbb562ad72e5e4817876d","span_id":"1533a887746ad23b","request_id":"07475f34c235","model":"mock-llm-small","agent_version":"v2","input_tokens":74,"output_tokens":37,"cost_usd":0.000033,"llm_ms":1658.6}
```

Trace lỗi `8d5c385cf4153c323723874dc52ccddb` có span LLM status code ERROR (OTLP code 2), event `exception` với loại `utils.mock_llm.LLMError`; HTTP 503. Nguồn `reports/jaeger_error_trace.json`, log cùng ID:

```json
{"ts":"2026-11-25T08:27:09.297170+00:00","level":"INFO","service":"observable-agent","instance":"e898582085f5","event":"llm_error","trace_id":"8d5c385cf4153c323723874dc52ccddb","span_id":"778e566df29ac637","request_id":"4b930b42a60b","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

## 5. Benchmark scaling

Locust headless **100 users, spawn rate 10/s, 2 phút**, model nhỏ, error 0.01, slow 0.03; cùng workload có `/ask` trọng số 10 và `/health` trọng số 1, wait 0.5–2 giây. Nguồn: hàng **Aggregated** trong `benchmark-results/scale_1_stats.csv` và `scale_3_stats.csv`; percentile Locust là xấp xỉ. CSV là lần ghi định kỳ cuối, có thể lệch nhẹ bảng console lúc shutdown; báo cáo dùng đúng CSV đã nộp.

| Instance | RPS | p50 ms | p95 ms | p99 ms | Failures / requests |
|---|---:|---:|---:|---:|---|
| 1 | 41.9922 | 460 | 3500 | 5900 | 45 / 4973 |
| 3 | 60.6462 | 220 | 1200 | 1800 | 60 / 7189 |

Riêng `/ask`: 1 instance RPS 38.2346, p50 500 ms, p95 3500 ms, p99 5900 ms, 45/4528 lỗi; 3 instance RPS 54.9688, p50 220 ms, p95 1300 ms, p99 1900 ms, 60/6516 lỗi. Tăng instance cải thiện p95 rõ ở lần chạy này. Throughput không tăng 3 lần vì số user và thời gian nghỉ cố định, đồng thời vẫn dùng chung máy Docker và các service quan sát. Mỗi agent bị giới hạn 0.5 CPU; kết quả phù hợp việc thêm capacity giảm chờ, nhưng chưa profiling để khẳng định nút thắt duy nhất. Lỗi được quan sát là HTTP 503 từ mock upstream.

## 6. Kết luận

1. p99 phát hiện request chậm mà average che khuất; cần đo cả tỷ lệ lỗi.
2. Retrieval tăng tokens nhưng cải thiện cost/câu đúng; quality gate kiểm tra cả accuracy lẫn regression.
3. Concurrency cao có thể làm latency tăng nhanh khi throughput chững lại; cần profiling và so sánh scale bằng cùng workload.

Nếu triển khai thật, bổ sung saturation/queue depth, lỗi Redis, budget burn rate và đánh giá chất lượng có lấy mẫu. CP7 và phần đo API/log, traces, alert, scaling CP8 đã có dữ liệu thực; ảnh được bỏ theo yêu cầu người dùng, cloud chưa triển khai. Đã commit dữ liệu trước khi dọn stack bằng `docker compose -p k5-day14-observability down -v` và dừng hai server benchmark v1/v2; không tác động container ngoài bài lab.
