# Bộ test lỗi — Catalog YAML → Graph JSON

Bộ file này để đưa vào hệ thống test, phủ mọi loại lỗi đã xác định. **Không gộp
được tất cả vào một file** vì hai lý do kỹ thuật:

1. Lỗi cú pháp YAML (tầng 1) làm parser **dừng ngay** — nếu để chung file thì mọi
   lỗi tầng sau không được kiểm tới.
2. Lỗi merge (tầng 5) chỉ lộ khi có **nhiều file** — một file không tạo ra được.

Nên bộ test chia theo mục đích. Chạy `python run-testset.py` để kiểm tự động.

---

## Các file và lỗi tương ứng

### `A-invalid-fields.catalog.yaml` — tầng 2, 3, 4 (parse được, gom lỗi)
File parse được nên validator chạy hết, gom **13 lỗi** cùng lúc. Đây là file
chứng minh cơ chế thu-thập-hết, không fail-fast.

| Mã lỗi | Trường gây lỗi |
|---|---|
| `UNSUPPORTED_VERSION` | `specVersion: wrong-version-here` |
| `INVALID_FORMAT` | `system` có chữ hoa, `namespace` có space, `id` có gạch dưới |
| `INVALID_ENUM` | `type: microservice`, `role: owner` |
| `TOO_LONG` | `domain` > 128 ký tự |
| `MISSING_TECHLEAD` | không member nào role techlead |
| `DUPLICATE` | email trùng (sau lowercase) |
| `INVALID_REF` | `resource:noslashhere` thiếu `/` |
| `UNKNOWN_KIND` | `database:n/mydb` kind không hỗ trợ |
| `DUPLICATE_EDGE` | hai ref `resource:n/shared-cache` giống hệt |
| `SYSTEM_MISMATCH` | system ref khác `metadata.system` |

**Điểm mù** (cố ý để trong file, parser hiện KHÔNG bắt):
- Email `not-a-valid-email` — sai định dạng nhưng lọt.
- `protocol: FTP` — protocol lạ nhưng lọt.

### `B-missing-required.catalog.yaml` — tầng 2 (thiếu trường)
Tách riêng vì lỗi "thiếu" dễ bị lỗi khác che. Ra **5 `REQUIRED`** + 2 warning.

| Mã lỗi | Nguyên nhân |
|---|---|
| `REQUIRED` ×5 | thiếu `domain`, `id`, `name`, `review.branch`, và `members` sai kiểu |
| `MISSING_PROVIDES_API` (warn) | `type: service` nhưng không khai `providesApis` |
| `MISSING_SYSTEM_REF` (warn) | (phát sinh kèm) |

### `C-broken-syntax.catalog.yaml` — tầng 1 (FAIL-FAST)
Cú pháp YAML vỡ (indent sai + key trùng). Parser dừng ngay, chỉ ra **1 lỗi
`YAML_SYNTAX`**. Mọi lỗi khác trong file KHÔNG được kiểm — đúng bản chất fail-fast.

### `D1` + `D2` + `D3` — tầng 5 (chỉ lộ khi MERGE)
**Từng file riêng đều HỢP LỆ (0 lỗi).** Phải merge cả ba mới lộ:

| Mã lỗi | Cơ chế |
|---|---|
| `DEPENDENCY_CYCLE` | D1 dependsOn payment-component; D2 consumes order-api; order-api provides order-component → vòng khép kín |
| `DUPLICATE_DECLARATION` | D1 và D3 cùng khai báo `component:order/order-service` |
| `AMBIGUOUS_OWNER` | D1 và D3 cùng `provides` `api:order/order-service` |
| `API_NO_PROVIDER` (warn) | D1 gọi `pricing/promo-service` nhưng không ai provides |
| `TOPIC_NO_PUBLISHER` (warn) | D2 subscribe `shipping.dispatched` nhưng không ai publishes |

---

## Tầng 6 — điểm mù đã biết (parser CHƯA bắt)

Đã xác nhận bằng test. Nằm rải trong file A và có thể thêm khi cần:

- Email sai định dạng → lọt (cần regex email)
- `protocol` lạ (FTP, XYZ) → lọt (cần enum protocol → warning)
- `reason` rỗng chuỗi `''` → lọt
- `providesApis` thiếu `protocol` → lọt
- **Typo field** (`onwers:` thay `owners:`) → báo nhầm "thiếu members", nguyên nhân
  thật là gõ sai (cần strict unknown-field → reject)

## Tầng 7 — không công cụ nào bắt được (cần người review)

- `reason` mô tả sai chiều quan hệ (chỉ lộ gián tiếp qua `DEPENDENCY_CYCLE`)
- Khai thiếu / thừa dependency so với code thật
- `reason` copy-paste nhầm nội dung
- Quyết định vận hành sai (datastore không replica cho service trọng yếu)

---

## Cách chạy

```bash
python run-testset.py
```

Script tự parse từng file, merge bộ D, và in bảng lỗi thực tế để đối chiếu với
bảng trên. Nếu số lỗi lệch so với kỳ vọng → parser đã đổi hành vi.
