# Project Brief — P-030

**AI Agent đề xuất & rà soát thiết kế kiến trúc hệ thống**
VinUni AI20K Build Phase · Cohort 3 & 4 · 4 thành viên · 6 tuần

---

## Vấn đề

Đội phát triển rà soát design doc dựa vào kinh nghiệm cá nhân. Hệ quả:

- **Không nhất quán** — cùng một tài liệu, hai người rà soát cho hai kết quả khác nhau
- **Không có nguồn dẫn** — "chỗ này thấy rủi ro" nhưng vi phạm nguyên tắc nào của công ty thì không chỉ ra được
- **Không truy vết** — sáu tháng sau sự cố, không trả lời được ai đã duyệt và duyệt trên cơ sở nào
- **Nút cổ chai** — kiến trúc sư giỏi thì ít, họ bận thì tài liệu bị duyệt qua loa cho kịp tiến độ

Chi phí sửa một quyết định kiến trúc sai tăng vọt qua từng giai đoạn: sửa trên giấy là một dòng, sửa sau khi lên production là sự cố cộng di trú dữ liệu.

## Giải pháp

Một AI Agent nhận file `spec.yaml` mô tả thiết kế, đối chiếu với kho nguyên tắc kiến trúc nội bộ, và trả về báo cáo rà soát theo **4 chiều**: bảo mật, độ sẵn sàng, khả năng mở rộng, chi phí.

Với mỗi rủi ro, agent đưa ra **2–3 phương án khắc phục kèm bảng so sánh đánh đổi** theo chi phí, độ trễ, khả năng mở rộng và hiệu năng.

**Agent không quyết định.** Nó dừng lại và chờ kiến trúc sư duyệt từng mục.

## Người dùng

| Vai trò | Làm gì |
|---|---|
| **SUBMITTER** — lập trình viên, tech lead | Nộp `spec.yaml`, đọc kết quả, sửa và nộp lại |
| **ARCHITECT** — người phê duyệt thiết kế | Chạy rà soát, quyết định từng phát hiện, phê duyệt |

## Ba điểm khác biệt

**1. Luật chạy trước, mô hình chạy sau.** Đầu vào YAML có cấu trúc nên ~70% lỗi bắt được bằng luật xác định — `replicas: 1` là SPOF, đó là một câu `if`, không cần suy luận. Mô hình chỉ làm phần nó giỏi: giải thích và đề xuất.

**2. Không bịa — kiểm tra cơ học, không phải dặn dò trong prompt.** Mỗi phát hiện phải trỏ tới một `yaml_path` có thật với giá trị khớp, và một mã nguyên tắc tra được trong DB. Không đạt thì bị gắn nhãn "cần kiểm chứng", tách riêng khỏi kết quả chính.

**3. Số liệu chi phí không do LLM sinh.** Chi phí và độ trễ trong bảng đánh đổi tính bằng công thức từ bảng `cost_reference` trong DB. Nếu agent nói "+62 USD/tháng" thì con số đó tra ngược được.

## Phạm vi MVP 

Có: đăng nhập 2 vai trò · upload `spec.yaml` · rà soát 4 chiều theo các mục checklist · trích dẫn nguyên tắc nội bộ · bảng so sánh phương án · quy trình duyệt HITL có lưu vết · deploy Docker có Live URL · Sinh bản nháp kiến trúc từ NL · phát hiện anti-pattern

## Cách đo

| Chỉ tiêu | Mục tiêu | Cách đo |
|---|---|---|
| Độ bao phủ lỗi | ≥ 70% | Bộ golden set 5 file YAML — 2 bản sạch, 3 bản cài sẵn lỗi có đáp án |
| Báo động giả | ≤ 2 / file sạch | Cùng bộ golden set |
| Tỷ lệ đã xác minh | ≥ 95% | Cột `grounded_ratio` |
| Thời gian rà soát | ≤ 120 s | Cột `duration_ms` |
| Chi phí | ≤ $0.05 / lượt | Cột `cost_usd` |

## Công nghệ

`FastAPI` · `LangGraph` · `gpt-4o-mini` (mặc định) + `gpt-4o` (node tổng hợp) · `PostgreSQL + pgvector` · `React.js ` · `Docker`
Hạ tầng: Render (API) · Vercel (Web) · Supabase (DB) — toàn bộ dùng gói miễn phí

## Lộ trình

| Tuần | Kết quả |
|---|---|
| 1 | Luồng rà soát chạy thông qua Swagger, chưa có UI |
| 2 | MVP hoàn chỉnh, có Live URL |
| 3 | Sinh diagram C4 từ YAML, phát hiện anti-pattern |
| 4 | RAGAS, xuất báo cáo |
| 5 | Đo đạc, 10 deliverables, video demo |
