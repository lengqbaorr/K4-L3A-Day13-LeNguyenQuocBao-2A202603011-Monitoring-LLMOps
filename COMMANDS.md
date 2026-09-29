# Danh sách lệnh chạy / kiểm tra

Chạy từ thư mục gốc repo, dùng PowerShell.

## 0. Mở môi trường (mỗi terminal mới)

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu chưa có venv/cài lại dependency:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env      # rồi điền key Langfuse, KHÔNG commit .env
```

## 1. Khởi động dịch vụ

```powershell
# Terminal 1 — API (cần cho load test / incident / chat)
uvicorn app.main:app --reload --env-file .env

# Terminal 2 — Dashboard 6 panel (evidence 11)
streamlit run scripts/dashboard_app.py
```

Kiểm tra nhanh:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing      # {"ok":true,...}
Invoke-WebRequest http://127.0.0.1:8000/metrics -UseBasicParsing     # p50/p95/p99, ttft, cost...
Invoke-WebRequest http://127.0.0.1:8501 -UseBasicParsing             # dashboard, HTTP 200
```

## 2. Tạo dữ liệu log

```powershell
python scripts/load_test.py                      # 10 request mặc định
python scripts/load_test.py --concurrency 5      # tạo burst, đủ data cho dashboard
python scripts/load_test.py --challenge --concurrency 5   # chạy theo challenge (sau khi inject)
```

> Trước khi đo điểm chính thức: **xoay log cũ** (validator đọc toàn bộ file),
> lưu baseline xong thì chuyển ra ngoài repo để không bị git track:
>
> ```powershell
> Move-Item data\logs.jsonl "$env:TEMP\logs.baseline.jsonl"
> ```
>
> rồi restart API → chạy load test.

## 3. Validator & test (bắt buộc)

```powershell
python scripts/validate_logs.py          # mục tiêu >= 80/100 (hiện 100/100)
python scripts/validate_dashboard.py     # mục tiêu "HỢP LỆ: 6/6 panel"
python -m pytest -q                      # toàn bộ tests phải pass; review hiện có 29 tests
```

## 4. Trace và prompt version

```powershell
python scripts/inspect_traces.py --min-traces 10              # liệt kê trace + token/cost
python scripts/inspect_traces.py --correlation-id req-08ca71e9   # truy 1 request
python scripts/inspect_traces.py --since-minutes 30

python scripts/prompt_versioning.py status        # xem version + labels hiện tại
python scripts/prompt_versioning.py bootstrap     # tạo v1 (baseline + production)
python scripts/prompt_versioning.py create-v2     # tạo v2 (candidate)
python scripts/prompt_versioning.py promote       # production -> v2
python scripts/prompt_versioning.py rollback      # production -> v1
```

Sau khi đổi label trong `.env` (`LANGFUSE_PROMPT_LABEL=production|candidate|baseline`) phải **restart API** rồi chạy 1 request để trace gắn đúng version:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/chat -Method Post -ContentType "application/json" `
  -Body '{"user_id":"student-01","session_id":"s-demo","feature":"qa","message":"What is the refund policy?"}' -UseBasicParsing
```

## 5. Incident / challenge

```powershell
python scripts/inject_incident.py                          # bật incident từ config/challenge.json (rag_slow)
python scripts/inject_incident.py --scenario tool_fail      # practice
python scripts/inject_incident.py --scenario rag_slow --disable   # tắt
```

Chuỗi điều tra chuẩn:

```powershell
# 1) metric
Invoke-WebRequest http://127.0.0.1:8000/metrics -UseBasicParsing
# 2) log: tìm correlation_id bất thường
Select-String -Path data\logs.jsonl -Pattern '"latency_ms": 26' | Select-Object -First 3
# 3) trace cùng correlation_id
python scripts/inspect_traces.py --correlation-id req-3a8a436c
```

## 6. Kiểm tra cuối (trước khi commit/push)

```powershell
python -m pytest -q
python scripts/validate_logs.py
python scripts/validate_dashboard.py
python scripts/inspect_traces.py --min-traces 10
git status --short
git log -1 --oneline
```

Rà soát tên file có thể chứa bí mật (kiểm tra từng kết quả; README có placeholder hợp lệ):

```powershell
git grep -l -E "sk-lf-|pk-lf-|sk-ant-"            # chỉ in tên file, tránh in secret
git ls-files | Select-String "\.env$|logs\.jsonl|\.venv"   # phải rỗng
```

## 7. Git nộp bài

```powershell
git add .
git commit -m "feat: logging, pii, tracing, dashboard, slo, alerts, report"
git push origin HEAD
git log -1 --oneline        # lấy SHA nộp lên VLearn
```

Không commit: `.env`, `data/logs.jsonl`, `.venv/`, ảnh chưa kiểm tra, evidence của người khác.
