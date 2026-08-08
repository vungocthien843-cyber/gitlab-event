# PRD — P-030

**AI Agent đề xuất & rà soát thiết kế kiến trúc hệ thống**

---

## 1. Mục tiêu

Chuẩn hoá việc rà soát thiết kế kiến trúc: từ phụ thuộc kinh nghiệm cá nhân thành một quy trình lặp lại được, có checklist cố định, có nguồn dẫn, có lưu vết.

**Phi mục tiêu:**

- Không thay thế kiến trúc sư. Agent là vòng lọc đầu tiên.
- Không tự động áp dụng bất kỳ thay đổi nào vào tài liệu.
- Không tích hợp Jira / Confluence / GitHub PR.

## 2. Personas

| | SUBMITTER | ARCHITECT |
|---|---|---|
| Là ai | Lập trình viên, tech lead vừa viết xong thiết kế | Người chịu trách nhiệm phê duyệt trước khi đội bắt tay code |
| Đau ở đâu | Chờ review lâu; feedback không rõ căn cứ | Đọc thủ công tốn thời gian; dễ sót; không nhớ tiêu chí |
| Cần gì | Biết thiết kế sai chỗ nào, sửa thế nào | Danh sách rủi ro có ưu tiên, có nguồn, để tập trung vào phần khó |

## 3. User stories

### US-01 · Nộp thiết kế
> Là **SUBMITTER**, tôi muốn tải lên `spec.yaml` để hệ thống kiểm tra thiết kế của tôi.

**Acceptance criteria**
- [ ] Upload file `.yaml` 
- [ ] Sai lược đồ → trả lỗi 422 kèm **đường dẫn trường sai** và mô tả
- [ ] File trùng → trả 409 kèm ID bản đã có
- [ ] Thành công → chuyển tới trang chi tiết, hiển thị YAML đã tô màu cú pháp

### US-02 · Chạy rà soát
> Là **ARCHITECT**, tôi muốn chạy rà soát tự động trên một thiết kế đã nộp.

**Acceptance criteria**
- [ ] SUBMITTER không thấy nút này
- [ ] Bấm → trả về ngay (202), không chờ; trạng thái `queued`
- [ ] Màn hình hiển thị tiến độ theo node đang chạy, cập nhật mỗi 3 giây
- [ ] Lỗi → trạng thái `failed` kèm thông báo đọc được, có nút chạy lại

### US-03 · Đọc báo cáo
> Là **cả hai vai trò**, tôi muốn xem rủi ro được nhóm theo chiều và sắp theo mức độ.

**Acceptance criteria**
- [ ] Phát hiện nhóm theo 4 chiều, sắp theo severity (critical → info)
- [ ] Mỗi phát hiện có: mức độ, mã checklist, tiêu đề, `yaml_path`, giá trị quan sát, giá trị kỳ vọng
- [ ] Click phát hiện → cột phải cuộn tới đúng dòng YAML và **highlight**
- [ ] Mở rộng → lý do, mã nguyên tắc bị vi phạm, bảng phương án
- [ ] Phát hiện chưa xác minh nằm ở mục riêng "Cần kiểm chứng"

### US-04 · So sánh phương án
> Là **ARCHITECT**, tôi muốn thấy các cách khắc phục kèm đánh đổi để chọn cho đúng.

**Acceptance criteria**
- [ ] Phát hiện từ mức `high` trở lên có 2–3 phương án
- [ ] Mỗi phương án hiển thị: chi phí (USD/tháng), độ trễ thêm (ms), mở rộng (1–5), hiệu năng (1–5), vận hành (1–5)
- [ ] Chi phí và độ trễ **tra từ bảng `cost_reference`**, không do mô hình sinh
- [ ] Phương án khuyến nghị được đánh dấu, kèm lý do bằng một câu
- [ ] Nếu không phương án nào đạt → nói rõ, không chọn bừa

### US-05 · Quyết định (HITL)
> Là **ARCHITECT**, tôi muốn duyệt hoặc bác bỏ từng phát hiện kèm lý do.

**Acceptance criteria**
- [ ] Ba nút: Chấp nhận / Bác bỏ / Sửa đổi, kèm ô ghi chú
- [ ] SUBMITTER gọi API này → 403
- [ ] Quyết định là **bản ghi mới**, không sửa bản cũ; lưu người + thời điểm
- [ ] Khi mọi phát hiện đã có quyết định → review chuyển `approved`
- [ ] Thanh tiến độ "đã xử lý x/y"

### US-06 · Tra cứu nguyên tắc
> Là **cả hai vai trò**, tôi muốn xem kho nguyên tắc nội bộ.

**Acceptance criteria**
- [ ] Danh sách nguyên tắc, lọc theo phân loại và mức bắt buộc (MUST/SHOULD/MAY)
- [ ] Mỗi mục có mã, tiêu đề, nội dung, ví dụ vi phạm, ví dụ tuân thủ, nguồn

## 4. Yêu cầu chức năng

| Mã | Yêu cầu | Ưu tiên |
|---|---|---|
| FR-01 | Đăng ký, đăng nhập JWT, 2 vai trò | P0 |
| FR-02 | Upload và validate `spec.yaml` theo lược đồ Pydantic | P0 |
| FR-03 | Rule engine: Các luật xác định chạy trên cây YAML | P0 |
| FR-04 | Truy xuất nguyên tắc nội bộ (pgvector, 4 truy vấn × top-k) | P0 |
| FR-05 | Rà soát 4 chiều bằng LLM, chạy song song | P0 |
| FR-06 | Xác minh grounding: `yaml_path` + giá trị + mã nguyên tắc | P0 |
| FR-07 | Sinh 2–3 phương án cho phát hiện ≥ high | P0 |
| FR-08 | Chấm đánh đổi 4 trục; chi phí & độ trễ tính từ `cost_reference` | P0 |
| FR-09 | HITL: quyết định từng phát hiện, có lưu vết | P0 |
| FR-10 | Kho nguyên tắc: duyệt, lọc, nạp lại | P1 |
| FR-11 | Sinh diagram C4 (Mermaid) từ `components` bằng template | P2 |
| FR-12 | Phát hiện anti-pattern (AP-01…05) | P2 |
| FR-13 | Xuất báo cáo Markdown / PDF | P2 |

## 5. Yêu cầu phi chức năng

| Mã | Chỉ tiêu |
|---|---|
| NFR-01 | Rà soát ≤ 120 s với file ≤ 200 dòng |
| NFR-02 | API đọc p95 ≤ 400 ms (không tính thời gian đánh thức Render) |
| NFR-03 | `grounded_ratio` ≥ 95% |
| NFR-04 | Độ bao phủ ≥ 70% trên golden set |
| NFR-05 | Báo động giả ≤ 2 / file sạch |
| NFR-06 | Chi phí ≤ $0.05 / lượt rà soát |
| NFR-07 | TLS mọi chặng, kể cả kết nối DB (`sslmode=require`) |
| NFR-08 | Mật khẩu bcrypt cost 12; không secret trong mã nguồn |
| NFR-09 | Mọi lượt gọi mô hình ghi lại token + độ trễ (bảng `agent_runs`) |
| NFR-10 | Máy sạch chỉ cần Docker + `.env`, cài đặt ≤ 10 phút |

## 6. Đầu vào / đầu ra

**Đầu vào:** File `spec.yaml`

**Đầu ra:** File json


## 7. Rủi ro

| Rủi ro | Mức | Xử lý |
|---|---|---|
| Người dùng viết sai lược đồ YAML | Cao | Lỗi chỉ rõ đường dẫn trường sai; file mẫu có chú thích; editor có gợi ý |
| Mô hình trả JSON sai định dạng | Cao | Structured output + Pydantic; retry 2 lần; lần 3 đổi sang `gpt-4o` |
| Hết quota API lúc demo | Thấp | 2 API key; giữ sẵn 1 review đã chạy trong seed; video dự phòng |

## 8. Ngoài phạm vi

Đọc tài liệu tự do · sơ đồ dạng ảnh · fine-tuning · phân quyền theo dự án · hàng đợi phân tán (Celery/Redis) · cộng tác thời gian thực · tích hợp hệ thống ngoài
