# Alert và Runbook

Mỗi alert dựa trên triệu chứng người dùng hoặc SLO, không dựa vào tên hàm/implementation nội bộ. Cấu hình máy ở [`config/alert_rules.yaml`](../config/alert_rules.yaml); ngưỡng và error budget giải thích trong [`config/slo.yaml`](../config/slo.yaml).

Kênh thông báo chung: Slack `#day13-oncall`.

## Alert 1

- Tên: `latency-high`
- Severity: warning
- Duration: 5m (ngưỡng phải vượt 3000 ms liên tục 5 phút mới fire)
- Kênh thông báo: Slack `#day13-oncall`
- SLI/SLO liên quan: `fast_successful_requests` (p95 ≤ 3000 ms, window 28d)
- Điều kiện và thời gian duy trì: `p95(response_sent.latency_ms) > 3000` kéo dài ≥ 5 phút
- Ảnh hưởng tới người dùng: phản hồi chậm hơn bình thường, người dùng cảm thấy hệ thống "ì"; TTFT vẫn có thể bình thường nếu bottleneck ở bước retrieval hoặc hàng đợi.
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
- Ảnh hưởng tới người dùng: câu trả lời thiếu ngữ cảnh, quality proxy giảm (`quality_score` trung bình < 0.75) dù error rate vẫn bình thường — người dùng nhận câu trả lời sai thay vì báo lỗi.
- Ba bước kiểm tra đầu tiên:
  1. Đọc panel **Errors** (thành phần retrieval success) và panel **Quality** — cả hai có giảm cùng lúc không.
  2. Lọc log `tool_success == false`, lấy `correlation_id` và kiểm tra `feature` liên quan.
  3. Mở span `rag-retrieval` trong trace tương ứng, xem `doc_count = 0` hay span báo lỗi.
- Mitigation tạm thời: bật lại truy vấn dự phòng/corpus, chuyển traffic sang replica khác, hoặc rollback prompt `production` về version trước (`python scripts/prompt_versioning.py rollback`) nếu nghi ngờ prompt mới làm câu trả lời lệch.
- Owner: rag-oncall
