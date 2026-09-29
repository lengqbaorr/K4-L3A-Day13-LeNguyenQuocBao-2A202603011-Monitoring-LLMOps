# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa vào tên hàm/implementation nội bộ. Cấu hình máy ở [`config/alert_rules.yaml`](../config/alert_rules.yaml); ngưỡng và error budget giải thích trong [`config/slo.yaml`](../config/slo.yaml).

Kênh thông báo chung: Slack `#day13-oncall`.

Các alert hiện là cấu hình và quy trình xử lý cho lab, chưa có engine gửi Slack thực tế. Không coi việc khai báo YAML là bằng chứng alert đã fire. Sau mitigation, chạy lại cùng workload, kiểm tra metric hồi phục và đối chiếu log/trace trước khi đóng sự cố.

## Alert 1

- Tên: `latency-high`
- Severity: warning
- Duration: 5m (ngưỡng phải vượt 3000 ms liên tục 5 phút mới fire)
- Kênh thông báo: Slack `#day13-oncall`
- SLI/SLO liên quan: `fast_successful_requests`: 99.5% request thành công với latency ≤ 3000 ms trong 28 ngày. P95 là tín hiệu alert, không phải công thức SLI.
- Điều kiện và thời gian duy trì: `p95(response_sent.latency_ms) > 3000` kéo dài ≥ 5 phút
- Ảnh hưởng tới người dùng: phản hồi chậm hơn bình thường. TTFT trong lab chỉ đo bên trong FakeLLM, nên không bao gồm retrieval hoặc thời gian chờ trước khi gọi LLM.
- Ba bước kiểm tra đầu tiên:
  1. Mở dashboard, đọc panel **Latency** — p50 có dịch không hay chỉ p95/p99 (chỉ tail tăng nghĩa là một nhóm request bị kẹt).
  2. Lọc `data/logs.jsonl` theo `latency_ms > 3000`, lấy 1 `correlation_id` bất thường và xem `feature`/`model` của request đó.
  3. Mở trace cùng `correlation_id`, so sánh thời gian `rag-retrieval` và `llm-generate` để biết bước nào chiếm phần lớn latency.
- Mitigation tạm thời: hạ concurrency của load test/client, tắt incident practice đang mở (`POST /incidents/rag_slow/disable` nếu đang bật), hoặc tăng số worker nếu đang chạy nhiều instance.
- Owner: llmops-oncall

## Alert 2

- Tên: `error-rate-high`
- Severity: critical
- Duration: 5m
- Kênh thông báo: Slack `#day13-oncall`
- SLI/SLO liên quan: `fast_successful_requests` + guardrail `error_rate_pct_max: 2`
- Điều kiện và thời gian duy trì: tỷ lệ `request_failed` / `request_received` > 2% kéo dài ≥ 5 phút
- Ảnh hưởng tới người dùng: một phần request trả HTTP 500, người dùng không nhận được câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xem panel **Errors** trên dashboard và breakdown theo `error_type`.
  2. Lọc log `event == "request_failed"` trong khoảng thời gian alert, lấy `correlation_id` và đọc `payload.detail`.
  3. Mở trace của `correlation_id` đó — nếu span `rag-retrieval` lỗi (ví dụ `Vector store timeout`) thì kiểm tra sự cố `tool_fail` đang bật qua `/health`.
- Mitigation tạm thời: tắt sự cố đang bật (`POST /incidents/tool_fail/disable`), restart API nếu state lỗi còn sót, gửi lại request bị lỗi cho người dùng.
- Owner: api-oncall

## Alert 3

- Tên: `retrieval-degraded`
- Severity: warning
- Duration: 10m
- Kênh thông báo: Slack `#day13-oncall`
- SLI/SLO liên quan: guardrail `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: `tool_success` = true dưới 90% số request có giá trị trong 10 phút
- Ảnh hưởng tới người dùng: retrieval lỗi có thể khiến request trả HTTP 500. Trong implementation hiện tại, fallback document vẫn được tính là thành công; retrieval success không chứng minh câu trả lời đúng và không nhất thiết giảm khi quality giảm.
- Ba bước kiểm tra đầu tiên:
  1. Đọc panel **Errors** (thành phần retrieval success) và panel **Quality** — cả hai có giảm cùng lúc không.
  2. Lọc log `tool_success == false`, lấy `correlation_id` và kiểm tra `feature` liên quan.
  3. Mở span `rag-retrieval` trong trace tương ứng, xem `doc_count = 0` hay span báo lỗi.
- Mitigation tạm thời: kiểm tra `/health`, tắt `tool_fail` bằng `python scripts/inject_incident.py --scenario tool_fail --disable` nếu đây là lỗi mô phỏng. Với hệ thống thật, khôi phục datasource hoặc chuyển sang replica khỏe. Chỉ rollback prompt khi trace chứng minh vấn đề liên quan prompt; rollback không sửa được lỗi kết nối retrieval.
- Owner: rag-oncall
