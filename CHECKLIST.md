# Checklist công việc còn lại (học viên)

Trạng thái kiểm tra ngày 2026-09-29: **chưa sẵn sàng nộp**. Code chính đã có; kiểm tra local đạt 29 tests, log validator 100/100 (87 dòng, 42 correlation ID, không phát hiện PII theo validator), dashboard contract 6/6. Có 4/14 file evidence dự kiến; chưa xác minh trực tiếp trace/prompt trên Langfuse trong lần review này.

## Ưu tiên sau review

1. **PII trên trace:** `app/agent.py` truyền `session_id` và `feature` trực tiếp vào `propagate_attributes`/metadata/tags. Hai trường này nhận chuỗi tùy ý từ API; cần scrub hoặc giới hạn định dạng trước khi gửi Langfuse. Scrubber của log không bảo vệ trace. Thêm kiểm tra với PII giả trong hai trường này.
2. **Kiểm tra trace:** `inspect_traces.py --min-traces 10` hiện xét tổng số trace, chưa bắt buộc 10 trace đủ span; chỉ đọc một trang observations nên có thể thiếu span/trace. Đối chiếu waterfall và lưu danh sách tối thiểu 10 trace hợp lệ; đừng dùng riêng chữ ĐẠT làm bằng chứng.
3. **Sửa diễn giải report/config:** SLO là tỷ lệ request tốt, không phải tỷ lệ uptime; 0.5% tương ứng 500 request xấu/100.000 request, không mặc nhiên là 201,6 phút downtime. P95 dưới ngưỡng chưa chứng minh budget còn nguyên. Alert 3000 ms/5m không fire cho incident 2655 ms kéo dài khoảng 14 giây; ngưỡng challenge là 2000 ms. Giữ nguyên challenge và dashboard contract, giải thích khác biệt này.
4. **Đối chiếu số đo:** TTFT hiện chỉ đo bên trong FakeLLM, không gồm retrieval/queue. Cost panel đo cửa sổ 60 phút, không chứng minh guardrail chi phí ngày. Retrieval trả fallback vẫn ghi success; runbook không nên khẳng định quality giảm chắc chắn làm retrieval success giảm.
5. **Evidence và report:** thu 10 evidence còn thiếu; chụp lại dashboard sau sửa error chart, ưu tiên hai ảnh dễ đọc. Cập nhật pytest từ 28 thành 29 trong report sau khi lưu output mới; đổi đường dẫn dạng backtick thành Markdown link. Baseline/trace IDs trong report phải có bằng chứng thật; không suy ra từ source.
6. **Nộp bài:** thay đổi còn ở working tree, HEAD hiện là `8c19544` (starter). Chưa có commit chứa bài hoàn thiện. Tên remote hiện không đúng mẫu trong `docs/SUBMISSION.md`; kiểm tra và đổi tên trên GitHub trước nộp. Chốt commit, chạy lại checks, lưu evidence và nộp SHA trên LMS; không thể tự ghi chính SHA của một commit vào nội dung của nó.

## Dọn code đã thực hiện

- Sửa error chart luôn 0% do chỉ đếm `request_received`; kiểm tra bằng dữ liệu 2 request/1 lỗi → 50%.
- Dashboard không còn crash khi chưa có log; test dùng file tạm, không phụ thuộc log cá nhân.
- Bỏ `LogRecord` không được dùng (schema chấm vẫn ở `config/logging_schema.json`), biến màu và cờ `has_generation` không dùng, biến env audit chưa có implementation; tái sử dụng template prompt có sẵn.
- Giữ tài liệu đề, public tests, mock LLM/RAG, dữ liệu mẫu và scripts phục vụ demo/chấm. `.env`, `.venv`, cache và log runtime đã được Git ignore; không cần xóa môi trường làm việc để nộp sạch.
- Không thay đổi `config/challenge.json`, không xóa log lỗi hoặc evidence cũ. Ảnh dashboard hiện có đủ sáu panel nhưng chữ nhỏ và thuộc phiên bản trước sửa.

## A. Chụp evidence (đặt vào `submission/evidence/`)

| # | Tên file | Ở đâu | Nội dung phải thấy | Trạng thái |
|---|---|---|---|---|
| 01 | `01-pytest.txt` | đã tạo bằng lệnh | `29 passed` sau review | ✅ |
| 02 | `02-log-validator.txt` | đã tạo bằng lệnh | `Estimated Score: 100/100` | ✅ |
| 03 | `03-dashboard-validator.txt` | đã tạo bằng lệnh | `HỢP LỆ: 6/6 panel` | ✅ |
| 04 | `04-structured-log.png` | mở `data/logs.jsonl` (VS Code) | dòng `response_sent` có `ts`, `event`, `correlation_id`, `model`, `env`, `feature`, `latency_ms` | ⬜ |
| 05 | `05-pii-redaction.png` | `data/logs.jsonl` | dòng có `[REDACTED_EMAIL]`, `[REDACTED_PHONE_VN]`, `[REDACTED_CREDIT_CARD]` | ⬜ |
| 06 | `06-trace-list.png` | Langfuse → Traces | ≥10 trace của bạn, có `correlation_id` | ⬜ |
| 07 | `07-trace-waterfall.png` | mở trace `67a100527d7d1cd86bacf27226b0ce6b` | root `lab-agent-run` → `rag-retrieval` → `llm-generate` | ⬜ |
| 08 | `08-trace-metadata.png` | tab Metadata của trace trên | `correlation_id=req-08ca71e9`, model, prompt v1/production, token, cost, **không có PII** | ⬜ |
| 09 | `09-prompt-versions.png` | Langfuse → Prompts → `day13-chat` | v1 = `baseline`+`production`, v2 = `candidate` | ⬜ |
| 10 | `10-prompt-rollback.png` | cùng trang prompt | **2 ảnh trước/sau**: trước = `production` ở v1 → báo AI chạy `promote` → sau = `production` ở v2 → AI `rollback` về v1 | ⬜ |
| 11 | `11-dashboard-overview.png` | `http://127.0.0.1:8501` | Đã có ảnh; cần chụp lại sau sửa error chart, tăng độ dễ đọc | ⚠️ |
| 12 | `12-incident-metric.png` | dashboard (panel Latency) hoặc `/metrics` | đỉnh ~2655 ms trong 03:27:53–03:28:07 UTC | ⬜ |
| 13 | `13-incident-log.png` | `data/logs.jsonl` | dòng `req-3a8a436c` với `latency_ms=2652` | ⬜ |
| 14 | `14-incident-trace.png` | trace `487087c5e65350b23e0150e811d716d6` | span `rag-retrieval` 2.501 s, `llm-generate` 0.151 s | ⬜ |

> Lưu ý: nếu muốn chụp lại **12** thì phải chạy lại incident (xem mục C) vì window dashboard chỉ 60 phút.

## B. Bổ sung vào `submission/REPORT.md`

- [ ] Điền **Commit SHA cuối** vào mục §1 (sau khi commit lần cuối).
- [ ] Kiểm tra mọi đường dẫn evidence trong §2 mở được (đường dẫn tương đối `evidence/...`).
- [ ] Đọc lại §8, chuẩn bị lời giải thích khi demo (Metrics → Logs → Traces, prompt rollback, error budget).

## C. Các bước khi cần chụp lại evidence incident

```powershell
python scripts/inject_incident.py
python scripts/load_test.py --challenge --concurrency 5
# -> chụp 12, 13, 14 trong vòng 60 phút
python scripts/inject_incident.py --scenario rag_slow --disable
```

## D. Nộp bài

- [ ] Chạy lại bộ lệnh trong `COMMANDS.md` (mục **Kiểm tra cuối**) trên commit cuối.
- [ ] Rà soát: không có `.env`, `.venv/`, `data/logs.jsonl`, secret, PII thô trong git.
- [ ] `git add` → `git commit` → `git push`.
- [ ] Nộp **URL repo** + **commit SHA cuối** trên VLearn LMS/Codelabs trước 23:59:59 ngày học (Asia/Ho_Chi_Minh).
- [ ] Demo được luồng Metrics → Logs → Traces → Root cause.
