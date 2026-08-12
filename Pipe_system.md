# Kiến trúc Dự án (Clean Architecture)

Dự án này đã được tối ưu hóa theo mô hình phân lớp rõ ràng (Separation of Concerns). Mô hình này giúp cho dự án dễ dàng bảo trì, mở rộng và đặc biệt hữu ích khi có nhiều lập trình viên cùng tham gia.

Dưới đây là cây thư mục trong `src/` và ý nghĩa của từng lớp:

```text
src/
├── api/                  # Tầng 1: Giao tiếp & Tiếp nhận (Controllers)
│   └── routes.py         # Chứa các endpoint API (ví dụ: POST /webhook/github). Nó chỉ làm nhiệm vụ tiếp khách, nhận request và trả về response.
│
├── services/             # Tầng 2: Não bộ nghiệp vụ (Business Logic)
│   ├── github_events.py  # Xử lý logic giải mã Webhook, tính toán xem file nào bị xóa/sửa/thêm.
│   ├── ingest.py         # Trái tim của hệ thống: chấm điểm, kiểm thử YAML và biến YAML thành Graph.
│   ├── validation.py     # Các lớp màng lọc 5 tầng (check dung lượng, schema, security, owner...).
│   └── llm.py            # Chứa các prompt gọi AI.
│
├── repositories/         # Tầng 3: Tương tác Database (Data Access)
│   ├── catalog_repository.py      # Chuyên thực thi lệnh SQL để ghi file YAML vào bảng `input_json`.
│   └── github_file_repository.py  # Chuyên thực thi lệnh SQL để ghi sự kiện Webhook vào 3 bảng Log.
│
├── models/               # Khung xương Dữ liệu (Schemas & DB Models)
│   ├── schemas.py        # Các class Pydantic định nghĩa đầu vào/đầu ra của API (Ví dụ: ApiResponse, Issue).
│   └── tables.py         # Các class SQLAlchemy định nghĩa cấu trúc bảng trong Database.
│
├── core/                 # Hạ tầng & Cấu hình (Infrastructure)
│   ├── config.py         # Nơi tập trung TẤT CẢ biến môi trường (.env) và các hằng số cấu hình hệ thống.
│   ├── db.py             # Nơi tạo ống nước kết nối với PostgreSQL Database, định nghĩa `session_scope`.
│   ├── errors.py         # Quản lý lỗi tập trung, định nghĩa các mã lỗi (STORAGE_FAILURE...).
│   ├── logging.py        # Cấu hình log ra màn hình Console.
│   └── store.py          # Bộ nhớ đệm (In-memory Cache) chia sẻ dùng chung toàn hệ thống.
│
├── agents/               # Tầng AI & Tự động hóa (Agents)
│   ├── graph.py          # Khai báo luồng LangGraph.
│   └── state.py          # Quản lý trạng thái (memory) của Agent.
│
└── main.py               # Trạm phát điện (Entrypoint) khởi động toàn bộ ứng dụng FastAPI.
```

> [!TIP]
> **Quy tắc làm việc với cấu trúc này:**
>
> - Nếu bạn muốn sửa đường dẫn URL API -> Sửa ở `api/`
> - Nếu bạn muốn đổi luật kiểm thử YAML -> Sửa ở `services/`
> - Nếu bạn muốn thay đổi câu lệnh SELECT/INSERT SQL -> Sửa ở `repositories/`
> - Nếu bạn muốn thêm cột mới vào Database -> Sửa ở `models/tables.py`
> - Nếu bạn muốn đổi thông tin kết nối DB hoặc Token -> Sửa ở `core/config.py` (và file `.env`)

## Luồng hoạt động: `POST /api/v1/catalogs` (upload nhiều file)

```
Client gửi multipart/form-data field "files" (1..N file)
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ api/routes.py :: upload_catalogs()                            │
│   đọc từng UploadFile → bytes thô, KHÔNG validate ở đây        │
└─────────────────────────────────────────────────────────────┘
        │  uploads: list[(filename, content, content_type)]
        ▼
┌─────────────────────────────────────────────────────────────┐
│ services/ingest.py :: ingest_catalogs_batch()                 │
│   for mỗi file:                                                │
│     try: ingest_catalog(file)  ◄── xem chi tiết bên dưới       │
│     except CriticalError: raise      (dừng CẢ batch)          │
│     except AppError: gắn vào results[], issues[]  (file khác   │
│                                        vẫn tiếp tục xử lý)     │
│   gộp results → ApiResponse (schemas.success/warning)          │
└─────────────────────────────────────────────────────────────┘
```

Bên trong mỗi lần gọi `ingest_catalog()` (1 file):

```
┌─────────────────────────────────────────────────────────────┐
│ services/validation.py :: run_validation_pipeline()            │
│   L1 basic_input    filename an toàn? đuôi đúng? size ≤ giới hạn? │
│   L2 security        RAW BYTES: magic bytes, YAML bomb, tag nguy hiểm │
│   L3 file_integrity   UTF-8 decode, YAML syntax, duplicate key │
│   L4 schema           đủ section specVersion/metadata/spec?     │
│   L5 data             business rules → catalog_to_graph.parse_document() │
│                        → (nodes, edges, root_id) + spec_version │
│   → ValidatedUpload { filename, parsed: ParsedFile, warnings } │
└─────────────────────────────────────────────────────────────┘
        │ (raise AppError nếu lỗi ở tầng nào đó — dừng NGAY tại file này)
        ▼
┌─────────────────────────────────────────────────────────────┐
│ services/ingest.py :: ingest_catalog()                         │
│   Bước 2: _check_cross_file_conflicts()                        │
│            → store.all_parsed() so với file mới qua merge_documents │
│            → 2 file cùng provides 1 API? → HumanReviewRequiredError │
│   Bước 3: _save_graph_document()                                │
│            → catalog_merge.merge_documents([parsed])            │
│            → { nodes, edges, information, diagnostics }         │
│            → repositories/catalog_repository.save(nodes=, edges=, │
│                        information=, diagnostics=)               │
│                        (tự dựng thêm file_json = {nodes, edges}) │
│   Bước 4: store.put(...)   cập nhật cache RAM (SAU khi DB ghi xong) │
│   Bước 5: _build_ingest_response()  → ApiResponse (success/warning) │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ repositories/catalog_repository.py :: save()                   │
│   SELECT theo _FILENAME_COLUMN (JSON path trong cột information)│
│   → có dòng cũ: UPDATE 5 cột      → không có: INSERT dòng mới  │
│   Postgres bảng input_json: id | nodes | edges | information |  │
│                              diagnostics | file_json            │
└─────────────────────────────────────────────────────────────┘
```

### Luồng phụ: webhook GitHub push

```
POST /api/v1/catalogs/webhook/github
        │
        ▼
services/github_events.py :: handle_push()
   tải từng file .yaml thay đổi trong push → gọi ingest_catalog() (1 file)
   trong loop tuần tự — cùng pattern "1 file lỗi không chặn cả push"
   mà ingest_catalogs_batch() giờ tái dùng
```

### Luồng đọc: `GET /api/v1/catalogs`

```
api/routes.py :: list_catalogs()
   → services/ingest.py :: list_catalogs()
   → core/store.py :: store.list(query)   (đọc CACHE, không chạm DB)
```

Cache này được nạp lại lúc khởi động server (`main.py` lifespan → `store.load_from_db()` → `catalog_repository.all_documents()` → dựng lại từng `StoredCatalog` từ 5 cột DB).

> [!NOTE]
> **Nguyên tắc kiến trúc xuyên suốt:** mỗi tầng chỉ biết đúng việc của mình — `routes.py` không biết business logic, `validation.py`/`catalog_to_graph.py` không biết SQLAlchemy, chỉ `catalog_repository.py` được chạm DB, và mọi response luôn đi qua `schemas.success()/warning()/from_error()` để giữ đúng 1 hình dạng `ApiResponse` cho mọi endpoint.

## Cấu trúc file JSON chuẩn (document sinh ra từ 1 catalog)

Đây là hình dạng dict mà `catalog_merge.merge_documents()` trả về — cũng chính là thứ được tách ra 4 cột JSONB (`nodes`, `edges`, `information`, `diagnostics`) khi lưu vào bảng `input_json`. Ví dụ thật, sinh trực tiếp từ `data/01-simple-notification-worker.catalog.yaml`:

```json
{
  "nodes": {
    "component:notification/notification-worker": {
      "id": "component:notification/notification-worker",
      "kind": "component",
      "namespace": "notification",
      "name": "notification-worker",
      "declared_by": "01-simple-notification-worker.catalog.yaml",
      "spec": {
        "service_key": "notification-core.notification-worker",
        "display_name": "Notification Worker",
        "description": "Consumer nền, đọc yêu cầu gửi thông báo từ Kafka và đẩy SMS/push cho khách hàng.",
        "system": "notification-core",
        "domain": "Notification",
        "type": "worker",
        "has_api_surface": false,
        "review": { "branch": "main" },
        "members": [
          { "user_email": "v.hangnt10@vinsmartfuture.tech", "role": "techlead" },
          { "user_email": "v.namdv3@vinsmartfuture.tech", "role": "maintainer" }
        ]
      }
    },
    "resource:notification/notification-postgres": {
      "id": "resource:notification/notification-postgres",
      "kind": "resource",
      "namespace": "notification",
      "name": "notification-postgres",
      "declared_by": null,
      "spec": null
    },
    "system:notification/notification-core": {
      "id": "system:notification/notification-core",
      "kind": "system",
      "namespace": "notification",
      "name": "notification-core",
      "declared_by": null,
      "spec": null
    }
  },
  "edges": [
    {
      "id": "component:notification/notification-worker|partOf|system:notification/notification-core",
      "source": "component:notification/notification-worker",
      "target": "system:notification/notification-core",
      "relation": "partOf",
      "protocol": null,
      "reason": "Component này là một phần của system notification-core",
      "declared_by": "component:notification/notification-worker",
      "yaml_path": "spec.topology[0]"
    },
    {
      "id": "component:notification/notification-worker|subscribes|topic:notification/notification.send-request",
      "source": "component:notification/notification-worker",
      "target": "topic:notification/notification.send-request",
      "relation": "subscribes",
      "protocol": "Kafka",
      "reason": "Nhận yêu cầu gửi thông báo do các service khác đẩy vào",
      "declared_by": "component:notification/notification-worker",
      "yaml_path": "spec.topology[3]"
    }
  ],
  "information": {
    "schemaVersion": "1.1",
    "specVersion": "vsf-idp.io/v2",
    "scope": {
      "kind": "merged",
      "root": null,
      "sources": [
        {
          "file": "01-simple-notification-worker.catalog.yaml",
          "root": "component:notification/notification-worker"
        }
      ]
    },
    "generatedAt": "2026-08-12T10:00:00+07:00"
  },
  "diagnostics": {
    "errors": [],
    "warnings": [
      {
        "code": "TOPIC_NO_PUBLISHER",
        "message": "topic:notification/notification.send-request được 1 component subscribe tới nhưng chưa có ai provides/publishes",
        "subject": "topic:notification/notification.send-request"
      }
    ]
  }
}
```

### Ý nghĩa từng khối

| Khối           | Kiểu                     | Ý nghĩa                                                                                                                                                                                                                                                                                                         |
| --------------- | ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `nodes`       | `dict[node_id, object]` | Mọi node trong đồ thị, khoá bằng`id` (`{kind}:{namespace}/{name}`). Node "self" (component tự khai báo) có `spec` đầy đủ; node được tham chiếu qua nhưng chưa có file khai báo riêng (`resource`, `system`, `topic`, `api` "stub") có `spec: null`, `declared_by: null`. |
| `edges`       | `list[object]`          | Mỗi phần tử là 1 quan hệ`source → target`. `source` luôn là component tự khai báo ("X provides/depends on Y"). `relation` tra theo `REF_KIND_MAP` (`partOf`, `dependsOn`, `provides`, `consumes`, `publishes`, `subscribes`).                                                       |
| `information` | `object`                | Metadata KHÔNG phải đồ thị:`schemaVersion` (hằng số hệ thống), `specVersion` (giá trị người dùng khai — không còn bị so sánh cứng), `scope` (file nguồn + node gốc), `generatedAt` (thời điểm nạp).                                                                             |
| `diagnostics` | `{errors, warnings}`    | Kết quả validate Layer 5 —`errors` khiến file bị từ chối (không tới được bước lưu), `warnings` không chặn nhưng vẫn hiển thị cho người dùng.                                                                                                                                          |

### Ánh xạ sang bảng `input_json` (Postgres)

Khi lưu, `catalog_repository.save()` tách 4 khối trên thành 4 cột riêng, và tự dựng thêm 1 cột gộp:

| Cột            | Nội dung                                                                                                                                                                                                                          |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`          | BIGSERIAL, khoá chính                                                                                                                                                                                                            |
| `nodes`       | = khối`nodes` ở trên                                                                                                                                                                                                          |
| `edges`       | = khối`edges` ở trên                                                                                                                                                                                                          |
| `information` | = khối`information` ở trên                                                                                                                                                                                                    |
| `diagnostics` | = khối`diagnostics` ở trên                                                                                                                                                                                                    |
| `file_json`   | `{"nodes": ..., "edges": ...}` — bản gộp chỉ 2 khối `nodes`+`edges`, tự dựng lại từ 2 cột trên mỗi lần ghi, dùng để trả nguyên khối cho client tải xuống mà không lộ `information`/`diagnostics` |

> [!TIP]
> Tra cứu 1 catalog theo tên file dùng đường dẫn JSON `information -> 'scope' -> 'sources' -> 0 ->> 'file'` (xem `catalog_repository.py :: information_filename()` / `_FILENAME_COLUMN`) — không có cột `filename` riêng, tên file luôn nằm bên trong `information`.
