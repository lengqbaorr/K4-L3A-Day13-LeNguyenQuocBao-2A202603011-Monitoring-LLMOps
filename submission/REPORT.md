# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

## 1. Thông tin học viên

- **Họ và tên:** Lê Nguyễn Quốc Bảo
- **MSSV:** 2A202603011
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/lengqbaorr/K4-L3A-Day13-LeNguyenQuocBao-2A202603011Monitoring-LLMOps
- **Commit tại thời điểm kiểm tra code:** `4fa9bb1` — `Lab day 13`. Tài liệu này được cập nhật sau commit đó; SHA nộp cuối lấy bằng `git rev-parse HEAD` sau khi commit/push và ghi trên LMS.
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`, cohort K4, incident `rag_slow`.

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest | [01-pytest.png](evidence/01-pytest.png) |
| Log validator | [02-log-validator.png](evidence/02-log-validator.png) |
| Dashboard validator | [03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| Structured log | [04-structured-log.png](evidence/04-structured-log.png) |
| PII redaction | [05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Trace list | [06-trace-list.png](evidence/06-trace-list.png) |
| Trace waterfall | [07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [08-trace-metadata.png](evidence/08-trace-metadata.png) |
| Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| Prompt rollback | [Trước](evidence/10-prompt-rollback.png), [sau](evidence/10b-prompt-rollback.png) |
| Dashboard runtime | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [12-incident-metric.png](evidence/12-incident-metric.png) |
| Incident log | [13-incident-log.png](evidence/13-incident-log.png) |
| Incident trace | [14-incident-trace.png](evidence/14-incident-trace.png) |

Các đường dẫn trên là index artifact; kết luận kỹ thuật bên dưới phân biệt kết quả kiểm tra local, thông tin trong evidence và điểm chưa xác minh trên Langfuse.

## 3. Kết quả kỹ thuật

Kiểm tra lại ngày 29/09/2026 trên working tree. Không còn output baseline độc lập để đối chứng, nên không tự điền số liệu trước khi sửa code.

| Nội dung | Baseline | Kết quả kiểm tra hiện tại | Phạm vi |
|---|---|---|---|
| `validate_logs.py` | Chưa lưu output đối chứng | **100/100** | 140 dòng, 68 correlation ID, không thiếu field/enrichment |
| `validate_dashboard.py` | Chưa lưu output đối chứng | **6/6 panel** | Kiểm tra contract YAML, không thay thế dashboard runtime |
| `pytest` | Chưa lưu output đối chứng | **29 passed** | Chạy bằng `python -m pytest -q` |
| Traces | Chưa lưu output đối chứng | **11 trace có AGENT/RETRIEVER/GENERATION** trong evidence 06 | Số lượng thuộc cửa sổ 120 phút lúc chụp, không phải tổng hiện tại của project |
| PII leak | Chưa lưu output đối chứng | **0 record bị validator phát hiện** | Theo bốn detector của validator; không phải bảo đảm tuyệt đối mọi loại PII |
| Latency P95 / TTFT P95 | Chưa lưu output đối chứng | **2652 ms / 50 ms** | Tính trên 63 `response_sent` của log hiện tại, gồm cả incident |
| Retrieval success | Chưa lưu output đối chứng | **63/63 = 100%** | Các record có `tool_success`; fallback cũng được tính thành công |

Log hiện tại trải từ `2026-09-29T02:29:30.250030Z` tới `2026-09-29T08:11:33.340743Z`. Ảnh validator 02 thuộc lần đo trước với 87 dòng; không dùng ảnh đó làm bằng chứng cho số lượng 140 dòng của lần kiểm tra này. Dashboard mặc định dùng 60 phút gần nhất nên không nhất thiết bằng thống kê toàn file.

Lệnh tái hiện từ thư mục gốc, sau khi cài requirements và cấu hình `.env`:

```powershell
# Terminal 1
uvicorn app.main:app --reload --env-file .env
# Terminal 2
streamlit run scripts/dashboard_app.py
# Terminal 3
python scripts/load_test.py --concurrency 5
python -m pytest -q
python scripts/validate_logs.py
python scripts/validate_dashboard.py
```

## 4. Logging và PII

[Middleware](../app/middleware.py) xóa context trước mỗi request, nhận header hợp lệ theo `req-[0-9a-f]{8}` hoặc tạo ID mới bằng UUID. ID được bind vào context, lưu trong `request.state` và trả về header `x-request-id`; `x-response-time-ms` đo thời gian ở middleware. Context được dọn trong `finally`.

[Handler `/chat`](../app/main.py) bind `user_id_hash`, `session_id`, `feature`, `model`, `env` và correlation ID trước `request_received`. Log `response_sent` có latency, TTFT, token, cost, quality và trạng thái retrieval; lỗi được ghi bằng `request_failed`.

[PII scrubber](../app/pii.py) nhận diện email, điện thoại Việt Nam, CCCD, thẻ thanh toán và thêm một số pattern passport/địa chỉ. `user_id` được SHA-256 rồi cắt 12 ký tự. `summarize_text` redact trước khi cắt preview; [processor `scrub_event`](../app/logging_config.py) xử lý các giá trị string trong dict/list trước `JsonlFileProcessor` và JSON renderer. Các field hệ thống trong `SAFE_KEYS` được giữ nguyên.

Evidence 05 có input giả và bốn marker redaction của request `req-a1b2c3d4`. Tests kiểm tra các định dạng PII và thứ tự processor; validator hiện không phát hiện leak trong log. Trace không tự đi qua processor log: input/output preview được scrub riêng, còn `session_id` và `feature` hiện vẫn truyền trực tiếp vào trace, nên chỉ dùng định danh test không chứa PII và cần bổ sung bảo vệ nếu triển khai ngoài lab.

## 5. Tracing và prompt versioning

[LabAgent](../app/agent.py) dùng root `lab-agent-run` loại `agent`, hai child `rag-retrieval` loại `retriever` và `llm-generate` loại `generation`. Root tắt capture input/output tự động. Retrieval ghi query preview đã scrub và số document; generation ghi model, preview, usage input/output, cost và managed prompt.

`correlation_id` được truyền qua `propagate_attributes` và metadata để nối với log. Prompt `day13-chat` giữ ba biến `feature`, `docs`, `message`; [prompt resolver](../app/prompt_management.py) lấy label từ `.env`, ghi version thật từ Langfuse, và đánh dấu `local`/`local-fallback` nếu không dùng được managed prompt.

Evidence 09 thể hiện v1 có `baseline`, `production`; v2 có `candidate`, `latest` tại thời điểm chụp. Một trace v1 được ghi trong evidence 06/07 là `5dffb832fe14dfcca0cdce7d095c2d93`, correlation ID `req-a1b2c3d4`, label `production`.

Quy trình promote/rollback:

```powershell
python scripts/prompt_versioning.py status
python scripts/prompt_versioning.py promote
# Restart API rồi gửi cùng input khi LANGFUSE_PROMPT_LABEL=production
python scripts/prompt_versioning.py rollback
# Restart API, gửi lại input và kiểm tra version thật trong trace
python scripts/prompt_versioning.py status
```

Hai request xuất hiện trong evidence rollback là `req-d3d3ec0a` và `req-a7173e46`; log xác nhận response nhưng không chứa prompt version. Do đó chưa thể dùng riêng hai response để xác nhận chúng thuộc v2/v1. Trace ID và version trước/sau cần lấy từ Langfuse và đối chiếu trước khi khẳng định rollback thành công. Trace incident trong evidence 14 ghi v3/production; version này thuộc thời điểm khác với ảnh danh sách v1/v2, không được tự diễn giải thành v1.

## 6. Dashboard, SLO và alerts

[Dashboard Streamlit](../scripts/dashboard_app.py) đọc `data/logs.jsonl`, dùng contract [dashboard.yaml](../config/dashboard.yaml), mặc định 60 phút và refresh 30 giây. Sáu panel gồm latency P50/P95/P99 và TTFT P95; traffic; errors và retrieval success; cost; tokens input/output; quality proxy. Error rate theo phút lấy số `request_failed` chia số `request_received`. Tests có tình huống hai request/một lỗi bằng 50% và trường hợp chưa có log.

[SLO](../config/slo.yaml) đặt mục tiêu **99.5% request thành công với latency ≤ 3000 ms trong 28 ngày**:

```text
SLI = số response_sent có latency_ms <= 3000 / số request_received
Error budget = 100% - 99.5% = 0.5% số request
Ví dụ: 100.000 request cho phép tối đa 500 request xấu.
```

Request xấu gồm request chậm quá ngưỡng hoặc không thành công; khi tính cửa sổ cần xử lý request còn đang chạy ở biên. Không đổi budget theo request thành 201,6 phút downtime. P95 dưới 3000 ms cũng chưa đủ chứng minh 99.5% request tốt. Ngưỡng 3000 ms giữ theo contract và tách biệt ngưỡng điều tra challenge 2000 ms.

Ba alert theo [config](../config/alert_rules.yaml) và [runbook](../docs/alerts.md):

| Alert | Điều kiện | Duration | Severity | Owner |
|---|---|---|---|---|
| latency-high | P95 latency > 3000 ms | 5m | warning | llmops-oncall |
| error-rate-high | request_failed / request_received > 2% | 5m | critical | api-oncall |
| retrieval-degraded | tỷ lệ tool_success < 90% | 10m | warning | rag-oncall |

Kênh khai báo là Slack `#day13-oncall`; chưa có engine thực thi/gửi thông báo. Cost panel tổng hợp cửa sổ 60 phút, chưa chứng minh guardrail chi phí ngày 2.5 USD. Quality là heuristic để quan sát thay đổi, không phải đánh giá chất lượng bởi con người.

## 7. Điều tra challenge

- **Challenge:** `day13-k4-l3a-monitoring-llmops-v1`, incident `rag_slow`, chạy workload `--challenge --concurrency 5`.
- **Khoảng điều tra từ log:** 29/09/2026, **09:26:46.13–09:26:56.76 UTC** (16:26:46–16:26:56 giờ Việt Nam), evidence 12.
- **Triệu chứng (metric):** `/metrics` latency_p95 = 2654 ms > ngưỡng challenge 2000 ms; ttft_p95 = 50 ms không đổi; error_breakdown rỗng. Cả 5 request `monitoring` có `latency_ms` 2652–2654 ms. Load test đo client-side 8.0–13.3 s do request bị xếp hàng (sleep đồng bộ chặn event loop).
- **Request đại diện (log, evidence 13):** `req-715cf7de`, `request_received` 09:26:46.135584Z, `response_sent` 09:26:48.790040Z; latency 2652 ms, TTFT 50 ms, tokens 35/148, cost 0.002325 USD, `tool_name=retrieval`.
- **Trace liên quan (evidence 14):** `e67c3b75cfc06a1f5be79df91df560ba`, cùng correlation ID, prompt `day13-chat@1[production]`. Waterfall: `lab-agent-run` 2654 ms → `rag-retrieval` **2501 ms** (94%), `llm-generate` 152 ms.
- **Root cause:** span retrieval chậm; source [retrieve](../app/mock_rag.py) `time.sleep(2.5)` khi `rag_slow` bật — khớp 2501 ms trên span.
- **Kiểm chứng fix:** sau `inject_incident.py --disable`, chạy lại cùng workload: `latency_ms` server về ~156 ms, client 331–818 ms.
- **Phân tích:** handler async gọi agent đồng bộ, retrieval/LLM có sleep đồng bộ nên có thể chặn event loop và tăng thời gian chờ client khi gửi đồng thời. TTFT 50 ms chỉ đo trong FakeLLM; TTFT không đổi không tự chứng minh toàn bộ thời gian tới token đầu tiên của người dùng không đổi.
- **Fix action:** tắt incident, gửi lại cùng workload; latency hồi phục từ 2652 ms về ~156 ms (đo ở trên).
- **Preventive measure:** theo dõi latency đầu-cuối và retrieval span; khi triển khai thực tế dùng timeout, I/O bất đồng bộ hoặc chuyển tác vụ blocking ra worker/thread phù hợp. Cần kiểm chứng tải sau thay đổi.

```powershell
python scripts/inject_incident.py --scenario rag_slow --disable
python scripts/load_test.py --challenge --concurrency 5
```

Incident 2652 ms vượt ngưỡng điều tra 2000 ms nhưng chưa vượt alert 3000 ms và diễn ra ngắn hơn 5 phút. Không khẳng định `latency-high` đã fire. Chuỗi điều tra cần metric đúng khoảng thời gian → log có correlation ID → waterfall cùng trace; không dùng việc bật incident làm bằng chứng metric.

## 8. Giải thích và tự đánh giá

**Quyết định kỹ thuật:** scrub trước khi serialize/ghi file và tắt auto-capture input/output của root trace. Cách này giảm rủi ro ghi raw message; vẫn phải kiểm tra metadata riêng vì logging và tracing là hai đường xuất dữ liệu khác nhau.

**Lỗi và cách xử lý:** dashboard từng tính error rate trên tập chỉ chứa `request_received`, khiến biểu đồ luôn 0%. Đã sửa tử số lấy `request_failed`, mẫu số lấy `request_received` theo phút và thêm test hai request/một lỗi → 50%. Dashboard cũng xử lý được file log chưa tồn tại, giúp chạy mới không crash.

**Metrics → Logs → Traces:** metric thu hẹp loại triệu chứng và thời gian; log chỉ ra request cụ thể; trace dùng cùng correlation ID để phân biệt retrieval, LLM và phần còn lại. Cần phân biệt latency client, middleware và agent trước khi so sánh số liệu.

**Prompt version/token/cost/SLO:** version truy nguyên cấu hình đã chạy; đổi label production hỗ trợ quay về version cũ mà không sửa source. Cache prompt có thể trì hoãn hiệu lực, nên lab restart API để xác minh. Token/cost là ước lượng của fake model phục vụ giám sát, không phải hóa đơn nhà cung cấp. SLO định nghĩa request tốt và budget giúp lượng hóa số request xấu chấp nhận được.

**Bài học:** validator pass chứng minh một phần contract; kết luận vận hành cần số đo runtime nối được bằng ID và thời gian. Không thay thế bằng tên file ảnh hoặc cấu hình alert.

**Hạn chế:** fake LLM/RAG; heuristic quality; metrics trong bộ nhớ; logs local; alert chưa gửi Slack; session/feature trên trace chưa được scrub riêng; công cụ inspect chỉ đọc một trang observations và ngưỡng min-traces xét tổng số trace. Thông tin baseline, trace v2/rollback và thời lượng span cần đối chiếu bằng artifact thực tế trước khi chốt báo cáo.

## 9. Checklist trước khi nộp

- [x] Tests/validators đã chạy trên working tree: 29 tests, 100/100, 6/6.
- [x] Report có liên kết source/config/runbook và giải thích giới hạn số đo.
- [ ] Đối chiếu các trace ID/version và kết luận incident với project Langfuse cá nhân.
- [ ] Chốt tên file/link evidence thực tế và kiểm tra ảnh mở được trên GitHub.
- [ ] Đọc lại, xác nhận nội dung tự đánh giá và bổ sung baseline nếu còn artifact gốc.
- [ ] Rà secret, PII, file runtime trước khi commit.
- [ ] Commit/push bài cuối, chạy lại checks nếu có thay đổi code và nộp URL/SHA trên LMS.
