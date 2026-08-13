"""
Test cho luồng input processing.

Chia theo TẦNG validate — mỗi tầng phải có ít nhất một test chứng minh nó chặn
được đúng thứ nó sinh ra để chặn, và một test chứng minh nó KHÔNG chặn nhầm
input hợp lệ.

Nhóm test quan trọng nhất là `TestContract`: nó kiểm tra tính chất đúng cho MỌI
response (status khớp severity, luôn có request_id, lỗi thì can_continue=False).
Loại test này bắt được cả những lỗi ở endpoint chưa ai nghĩ tới khi viết test.
"""

from __future__ import annotations

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.core import config
from src.core import db as core_db
from src.core.store import store
from src.main import app
from src.repositories import catalog_repository
from src.services import ingest

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


def make_yaml(
    *,
    sid: str = "order-service",
    namespace: str = "order",
    system: str = "order-system",
    stype: str = "worker",
    topology: str | None = None,
) -> str:
    """Mặc định sinh ra file SẠCH TUYỆT ĐỐI — không lỗi, không cảnh báo.

    Dùng `worker` chứ không `service` cho mặc định: component có API surface mà
    khai providesApis thì luôn kèm cảnh báo AWAITING_SPEC_INGEST (đúng theo luật
    nghiệp vụ). Test "thành công sạch" cần một fixture không có cảnh báo nào,
    nếu không nó không phân biệt được success với warning.
    """
    default_topology = f"""
    - ref: system:{namespace}/{system}
    - ref: resource:{namespace}/order-db"""
    return f"""specVersion: vsf-idp.io/v2
metadata:
  domain: commerce
  system: {system}
  namespace: {namespace}
spec:
  type: {stype}
  id: {sid}
  name: Order Service
  description: Handles order lifecycle
  owners:
    members:
      - user: alice@example.com
        role: techlead
  review:
    branch: main
  topology:{topology if topology is not None else default_topology}
"""


VALID_YAML = make_yaml()

# Hợp lệ nhưng thiếu ref 'system' và thiếu providesApis -> chỉ ra WARNING.
WARNING_YAML = make_yaml(topology="\n    - ref: resource:order/order-db")

# Sai luật nghiệp vụ: id không phải slug, thiếu techlead.
INVALID_DATA_YAML = """specVersion: vsf-idp.io/v2
metadata:
  domain: commerce
  system: order-system
  namespace: order
spec:
  type: service
  id: Order_Service
  name: Order Service
  owners:
    members:
      - user: bob@example.com
        role: member
  review:
    branch: main
  topology:
    - ref: system:order/order-system
"""


def upload(name: str, text: str | bytes, content_type: str = "application/x-yaml"):
    data = text.encode("utf-8") if isinstance(text, str) else text
    return client.post("/api/v1/catalogs", files=[("files", (name, data, content_type))])


def upload_many(pairs: list[tuple[str, str | bytes]]):
    files = []
    for name, yaml_text in pairs:
        data = yaml_text.encode("utf-8") if isinstance(yaml_text, str) else yaml_text
        files.append(("files", (name, data, "application/x-yaml")))
    return client.post("/api/v1/catalogs", files=files)


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Dựng một SCHEMA RIÊNG trên chính Postgres thật, xoá sạch lúc xong.

    Vì sao không dùng SQLite cho nhanh: bảng dùng JSONB và BIGSERIAL, còn phép
    tra cứu dựa trên toán tử JSON của Postgres. Test trên một engine khác là test
    một hệ thống không tồn tại — nó xanh trong khi production vẫn hỏng.

    Vì sao là schema riêng chứ không phải bảng riêng: `DROP SCHEMA ... CASCADE`
    dọn được mọi thứ test tạo ra trong đúng một câu, kể cả những thứ thêm vào sau
    này. Và không có đường nào để một câu lệnh trong test chạm tới `ai20k_db`.
    """
    if not config.DATABASE_URL:
        pytest.fail(
            "Thiếu DATABASE_URL. Bộ test chạy trên Postgres thật (schema riêng), "
            "không có bản giả lập — hãy đặt biến này trong .env."
        )

    schema = os.getenv("TEST_DB_SCHEMA", "ai20k_db_test")
    if schema == (config.DB_SCHEMA or config.DB_SCHEMA_FALLBACK):
        pytest.fail(
            f"TEST_DB_SCHEMA trùng schema production ('{schema}'). "
            "Test sẽ TRUNCATE bảng nên phải nằm ở schema khác."
        )

    core_db.configure(config.DATABASE_URL, schema)
    core_db.init_db()

    yield

    with core_db.get_engine().begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
    core_db.dispose()


@pytest.fixture(autouse=True)
def isolate():
    """Mỗi test bắt đầu với bảng rỗng và cache rỗng."""
    _truncate()
    store.clear()
    yield
    store.clear()


def _truncate() -> None:
    with core_db.get_engine().begin() as conn:
        conn.execute(text("TRUNCATE TABLE input_json RESTART IDENTITY"))


def stored(filename: str) -> dict | None:
    """Tài liệu JSON đang nằm trong bảng cho file này (None nếu không có)."""
    return catalog_repository.find(filename)


def row_count() -> int:
    return catalog_repository.count()


# ─────────────────────────────────────────────────────────────────────────────
# Contract — tính chất phải đúng cho mọi response
# ─────────────────────────────────────────────────────────────────────────────


class TestContract:
    ALL_REQUESTS = [
        lambda: upload("order-service.yaml", VALID_YAML),
        lambda: upload("warn.yaml", WARNING_YAML),
        lambda: upload("bad.txt", "x"),
        lambda: upload("empty.yaml", ""),
        lambda: upload("broken.yaml", "specVersion: vsf-idp.io/v2\n"),
        lambda: upload("../evil.yaml", VALID_YAML),
        lambda: client.get("/api/v1/catalogs"),
        lambda: client.delete("/api/v1/catalogs/khong-ton-tai.yaml"),
        lambda: client.get("/duong-dan-khong-ton-tai"),
    ]

    @pytest.mark.parametrize("call", ALL_REQUESTS)
    def test_moi_response_deu_dung_hinh_dang(self, call):
        body = call().json()
        for field in (
            "status", "severity", "code", "message",
            "can_continue", "next_action", "stage", "request_id", "issues", "details",
        ):
            assert field in body, f"thiếu field '{field}'"
        assert body["message"], "message không được rỗng"
        assert body["request_id"], "request_id không được rỗng"

    @pytest.mark.parametrize("call", ALL_REQUESTS)
    def test_status_luon_khop_severity(self, call):
        """status suy ra từ severity — hai field này không bao giờ được lệch."""
        body = call().json()
        expected = {
            "none": "success", "low": "warning",
            "validation": "error", "critical": "error",
        }[body["severity"]]
        assert body["status"] == expected

    @pytest.mark.parametrize("call", ALL_REQUESTS)
    def test_loi_thi_khong_bao_gio_cho_di_tiep(self, call):
        body = call().json()
        if body["status"] == "error":
            assert body["can_continue"] is False
            assert body["code"] is not None
            assert body["next_action"] != "proceed"

    def test_request_id_trong_body_khop_header(self):
        r = upload("order-service.yaml", VALID_YAML)
        assert r.headers["X-Request-ID"] == r.json()["request_id"]

    def test_request_id_do_client_gui_duoc_giu_nguyen(self):
        r = client.get("/api/v1/catalogs", headers={"X-Request-ID": "trace-abc-123"})
        assert r.json()["request_id"] == "trace-abc-123"


# ─────────────────────────────────────────────────────────────────────────────
# Luồng thành công
# ─────────────────────────────────────────────────────────────────────────────


class TestHappyPath:
    def test_file_hop_le_tra_success_va_luu_db(self):
        r = upload("order-service.yaml", VALID_YAML)
        assert r.status_code == 201

        body = r.json()
        assert body["status"] == "success"
        assert body["severity"] == "none"
        assert body["code"] is None
        assert body["can_continue"] is True
        assert body["next_action"] == "proceed"
        assert body["stage"] == "done"
        assert body["issues"] == []
        result = body["details"]["results"][0]
        assert result["root"] == "component:order/order-service"
        assert result["node_count"] > 0

        assert result["output_file"] == "order-service.json"
        assert isinstance(result["record_id"], int)

        graph = stored("order-service.yaml")
        assert graph is not None
        assert graph["nodes"]["component:order/order-service"]["spec"]["type"] == "worker"

    def test_duoi_yml_va_hau_to_catalog_deu_duoc(self):
        assert upload("payment.catalog.yml", make_yaml(sid="payment-service")).status_code == 201
        assert stored("payment.catalog.yml") is not None

    def test_upload_lai_cung_ten_bao_warning_ghi_de(self):
        first = upload("order-service.yaml", VALID_YAML).json()
        body = upload("order-service.yaml", VALID_YAML).json()

        assert body["status"] == "warning"
        assert body["can_continue"] is True
        assert body["details"]["results"][0]["replaced_existing"] is True
        assert any(i["code"] == "FILE_REPLACED" for i in body["issues"])
        # Ghi ĐÈ đúng dòng cũ, không chèn thêm dòng mới: bảng phản ánh "các
        # catalog đang có", không phải nhật ký upload.
        assert body["details"]["results"][0]["record_id"] == first["details"]["results"][0]["record_id"]
        assert row_count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# Warning — đi tiếp được
# ─────────────────────────────────────────────────────────────────────────────


class TestWarning:
    def test_canh_bao_khong_chan_luong(self):
        r = upload("warn.yaml", WARNING_YAML)
        assert r.status_code == 201

        body = r.json()
        assert body["status"] == "warning"
        assert body["severity"] == "low"
        assert body["can_continue"] is True
        assert body["next_action"] == "review_warnings"
        assert body["code"] == "HAS_WARNINGS"
        assert {i["code"] for i in body["issues"]} >= {"MISSING_SYSTEM_REF"}
        assert all(i["severity"] == "warning" for i in body["issues"])
        # Có warning vẫn phải lưu được: warning là "để ý", không phải "dừng".
        assert stored("warn.yaml") is not None

    def test_file_co_warning_van_nam_trong_danh_sach(self):
        upload("warn.yaml", WARNING_YAML)
        item = client.get("/api/v1/catalogs").json()["details"]["items"][0]
        assert item["state"] == "valid_with_warnings"
        assert item["warning_count"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — basic input
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer1BasicInput:
    def test_khong_gui_file(self):
        r = client.post("/api/v1/catalogs")
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "NO_FILE"
        assert body["stage"] == "receive"
        assert body["next_action"] == "fix_and_reupload"

    def test_file_rong(self):
        r = upload("empty.yaml", "")
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "EMPTY_FILE"

    def test_sai_duoi_file(self):
        r = upload("catalog.txt", VALID_YAML)
        assert r.status_code == 201
        result = r.json()["details"]["results"][0]
        assert result["code"] == "INVALID_FILE_TYPE"
        assert result["details"]["allowed_extensions"] == [".yaml", ".yml"]

    def test_file_qua_lon(self):
        r = upload("huge.yaml", "#" + "a" * (config.MAX_UPLOAD_BYTES + 1))
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "FILE_TOO_LARGE"

    def test_ten_file_qua_dai(self):
        r = upload("a" * 200 + ".yaml", VALID_YAML)
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "FILENAME_TOO_LONG"

    def test_content_type_la_khong_bi_chan(self):
        """Content-Type do client khai không đáng tin -> không dùng để chặn."""
        r = upload("order-service.yaml", VALID_YAML, content_type="application/octet-stream")
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["status"] == "success"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2 — security
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer2Security:
    @pytest.mark.parametrize(
        "name",
        [
            "../../etc/passwd.yaml",
            "..\\..\\windows\\system32\\evil.yaml",
            "sub/dir/catalog.yaml",
            "C:catalog.yaml",
            "catalog.yaml:stream",
            "nul.yaml",
            ".hidden.yaml",
        ],
    )
    def test_ten_file_nguy_hiem_bi_tu_choi(self, name):
        r = upload(name, VALID_YAML)
        assert r.status_code == 201
        result = r.json()["details"]["results"][0]
        assert result["code"] == "UNSAFE_FILENAME"

    def test_path_traversal_khong_luu_duoc_gi(self):
        upload("../../evil.yaml", VALID_YAML)
        assert row_count() == 0

    def test_file_nhi_phan_doi_lot_yaml(self):
        r = upload("fake.yaml", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert r.status_code == 201
        result = r.json()["details"]["results"][0]
        assert result["code"] == "CONTENT_TYPE_MISMATCH"
        assert result["details"]["detected_format"] == "PNG"

    def test_noi_dung_chua_nul_byte(self):
        r = upload("weird.yaml", VALID_YAML.encode() + b"\x00\x01")
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "BINARY_CONTENT"

    def test_tag_python_bi_chan(self):
        payload = "specVersion: !!python/object/apply:os.system ['echo hi']\n"
        r = upload("evil.yaml", payload)
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "UNSAFE_YAML_TAG"

    def test_yaml_bomb_bi_chan_truoc_khi_parse(self):
        """'Billion laughs': SafeLoader KHÔNG chặn được, layer 2 phải chặn."""
        lines = ["a0: &a0 'x'"]
        for i in range(1, 40):
            lines.append(f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 8)}]")
        r = upload("bomb.yaml", "\n".join(lines))
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "YAML_EXPANSION_BOMB"

    def test_qua_nhieu_dong(self):
        r = upload("long.yaml", "# comment\n" * (config.MAX_YAML_LINES + 1))
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "YAML_TOO_MANY_LINES"

    def test_long_nhau_qua_sau(self):
        deep = "".join(" " * (2 * i) + f"k{i}:\n" for i in range(config.MAX_YAML_DEPTH + 5))
        r = upload("deep.yaml", deep)
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "YAML_TOO_DEEP"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — file integrity
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer3Integrity:
    def test_khong_phai_utf8(self):
        r = upload("latin.yaml", "specVersion: caf\xe9".encode("latin-1"))
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "INVALID_ENCODING"

    def test_bom_utf8_van_doc_duoc(self):
        r = upload("bom.yaml", b"\xef\xbb\xbf" + VALID_YAML.encode("utf-8"))
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["status"] == "success"

    def test_sai_cu_phap_yaml(self):
        r = upload("broken.yaml", "spec:\n  - a\n b: [unclosed\n")
        assert r.status_code == 201
        body = r.json()
        result = body["details"]["results"][0]
        assert result["code"] == "YAML_SYNTAX"
        assert result["stage"] == "layer3_file_integrity"
        assert len(body["issues"]) == 1

    def test_key_trung_bi_tu_choi(self):
        """PyYAML mặc định nuốt key trùng và lấy cái sau. Ở đây phải báo lỗi:
        key trùng gần như luôn là dấu hiệu merge nhầm."""
        dup = VALID_YAML.replace("  domain: commerce", "  domain: commerce\n  domain: retail")
        r = upload("dup.yaml", dup)
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "DUPLICATE_KEY"

    def test_root_khong_phai_mapping(self):
        r = upload("list.yaml", "- a\n- b\n")
        assert r.status_code == 201
        assert r.json()["details"]["results"][0]["code"] == "INVALID_STRUCTURE"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — schema
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer4Schema:
    def test_thieu_section_bat_buoc(self):
        r = upload("partial.yaml", "specVersion: vsf-idp.io/v2\n")
        assert r.status_code == 201
        body = r.json()
        result = body["details"]["results"][0]
        assert result["code"] == "MISSING_REQUIRED_SECTION"
        assert result["stage"] == "layer4_schema"
        assert set(result["details"]["missing_sections"]) == {"metadata", "spec"}

    def test_section_sai_kieu(self):
        r = upload("wrong.yaml", "specVersion: vsf-idp.io/v2\nmetadata: hello\nspec: 123\n")
        assert r.status_code == 201
        body = r.json()
        assert body["details"]["results"][0]["code"] == "INVALID_STRUCTURE"
        assert {i["location"] for i in body["issues"]} == {"metadata", "spec"}


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — data / business rules
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer5Data:
    def test_gom_het_loi_thay_vi_dung_o_loi_dau_tien(self):
        """Người sửa YAML cần thấy cả 5 lỗi trong một lần, không phải upload 5 lần."""
        r = upload("invalid.yaml", INVALID_DATA_YAML)
        assert r.status_code == 201

        body = r.json()
        result = body["details"]["results"][0]
        assert result["code"] == "SCHEMA_VALIDATION_FAILED"
        assert result["stage"] == "layer5_data"

        errors = [i for i in body["issues"] if i["severity"] == "error"]
        assert len(errors) >= 2
        assert {"INVALID_FORMAT", "MISSING_TECHLEAD"} <= {i["code"] for i in errors}
        assert all(i["location"] for i in errors), "mỗi lỗi phải chỉ đúng vị trí trong YAML"

    def test_specversion_khac_van_duoc_chap_nhan(self):
        """Không còn so sánh cứng specVersion — chỉ cần field có mặt, giá trị
        khác 'vsf-idp.io/v2' vẫn được lưu nguyên văn, không bị chặn."""
        r = upload("old.yaml", VALID_YAML.replace("vsf-idp.io/v2", "vsf-idp.io/v1"))
        assert r.status_code == 201
        body = r.json()
        assert body["details"]["results"][0]["status"] == "success"
        assert not any(i["code"] == "UNSUPPORTED_VERSION" for i in body["issues"])

        graph = stored("old.yaml")
        assert graph["information"]["specVersion"] == "vsf-idp.io/v1"

    def test_file_loi_khong_luu_db_va_khong_vao_kho(self):
        """Bản cũ ghi JSON kể cả khi parse còn lỗi -> kho tích luỹ rác."""
        upload("invalid.yaml", INVALID_DATA_YAML)
        assert row_count() == 0
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# Human-in-the-loop
# ─────────────────────────────────────────────────────────────────────────────


class TestHumanInTheLoop:
    PROVIDER_A = make_yaml(
        sid="order-service", stype="service",
        topology="\n    - ref: system:order/order-system"
                 "\n    - ref: providesApis:order/order-service",
    )
    PROVIDER_B = make_yaml(
        sid="payment-service", stype="service",
        topology="\n    - ref: system:order/order-system"
                 "\n    - ref: providesApis:order/order-service",
    )

    def test_tranh_chap_quyen_so_huu_chuyen_human_review(self):
        """Hai file cùng provides một API: hệ thống không có cơ sở chọn bên nào."""
        upload("a.yaml", self.PROVIDER_A)
        r = upload("b.yaml", self.PROVIDER_B)

        assert r.status_code == 201
        body = r.json()
        result = body["details"]["results"][0]
        assert result["code"] == "NEEDS_HUMAN_REVIEW"
        assert body["details"]["failed"] == 1
        assert body["issues"][0]["code"] == "AMBIGUOUS_OWNER"

    def test_tranh_chap_khong_lam_hong_du_lieu_da_co(self):
        upload("a.yaml", self.PROVIDER_A)
        upload("b.yaml", self.PROVIDER_B)
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 1
        assert stored("b.yaml") is None

    def test_upload_lai_chinh_no_khong_bi_coi_la_tranh_chap(self):
        upload("a.yaml", make_yaml())
        assert upload("a.yaml", make_yaml()).status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
# Danh sách + tìm kiếm
# ─────────────────────────────────────────────────────────────────────────────


class TestListAndSearch:
    @pytest.fixture(autouse=True)
    def seed(self):
        upload("order-service.yaml", make_yaml(sid="order-service"))
        upload("payment-service.yaml", make_yaml(sid="payment-service", namespace="payment",
                                                 system="payment-system"))
        upload("order-worker.yaml", make_yaml(sid="order-worker", stype="worker",
                                              topology="\n    - ref: system:order/order-system"))

    def test_liet_ke_day_du(self):
        d = client.get("/api/v1/catalogs").json()["details"]
        assert d["total"] == 3
        assert d["returned"] == 3
        assert [i["file"] for i in d["items"]] == [
            "order-service.yaml", "order-worker.yaml", "payment-service.yaml"
        ]

    def test_moi_dong_du_thong_tin_de_render_bang(self):
        item = client.get("/api/v1/catalogs").json()["details"]["items"][0]
        for field in ("file", "root", "state", "error_count", "warning_count",
                      "node_count", "edge_count", "size_bytes", "uploaded_at",
                      "output_file", "record_id"):
            assert field in item
        assert item["output_file"] == "order-service.json"
        assert isinstance(item["record_id"], int)

    def test_tim_kiem_theo_chuoi_con(self):
        d = client.get("/api/v1/catalogs", params={"q": "order"}).json()["details"]
        assert d["returned"] == 2
        assert d["total"] == 3
        assert all("order" in i["file"] for i in d["items"])

    def test_tim_kiem_khong_phan_biet_hoa_thuong(self):
        assert client.get("/api/v1/catalogs", params={"q": "ORDER"}).json()["details"]["returned"] == 2

    def test_tim_khong_thay_van_la_success_voi_danh_sach_rong(self):
        """Không tìm thấy KHÔNG phải lỗi — câu truy vấn đã chạy đúng."""
        body = client.get("/api/v1/catalogs", params={"q": "khong-co-gi"}).json()
        assert body["status"] == "success"
        assert body["details"]["items"] == []
        assert "khong-co-gi" in body["message"]

    def test_diagnostics_chi_tra_khi_duoc_yeu_cau(self):
        assert client.get("/api/v1/catalogs").json()["details"]["items"][0]["diagnostics"] is None
        with_diag = client.get("/api/v1/catalogs", params={"include": "diagnostics"}).json()
        assert with_diag["details"]["items"][0]["diagnostics"] is not None

    def test_include_sai_gia_tri_bi_tu_choi(self):
        r = client.get("/api/v1/catalogs", params={"include": "everything"})
        assert r.status_code == 422
        assert r.json()["severity"] == "validation"


# ─────────────────────────────────────────────────────────────────────────────
# Xoá
# ─────────────────────────────────────────────────────────────────────────────


class TestDelete:
    def test_xoa_ca_ban_ghi_lan_dong_trong_db(self):
        upload("order-service.yaml", VALID_YAML)
        assert stored("order-service.yaml") is not None

        r = client.delete("/api/v1/catalogs/order-service.yaml")
        assert r.status_code == 200

        body = r.json()
        assert body["status"] == "success"
        assert body["details"]["remaining"] == 0
        assert stored("order-service.yaml") is None
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 0

    def test_xoa_file_khong_ton_tai_kem_goi_y(self):
        upload("order-service.yaml", VALID_YAML)
        r = client.delete("/api/v1/catalogs/order-servic.yaml")

        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "CATALOG_NOT_FOUND"
        assert body["can_continue"] is False

    def test_goi_y_khi_go_tat(self):
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/api/v1/catalogs/order").json()
        assert body["details"]["suggestions"] == ["order-service.yaml"]

    def test_goi_y_khi_go_sai_chinh_ta(self):
        """Gõ thiếu/nhầm một ký tự là lúc cần gợi ý nhất — khớp chuỗi con không lo được."""
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/api/v1/catalogs/order-servic.yaml").json()
        assert body["details"]["suggestions"] == ["order-service.yaml"]

    def test_khong_goi_y_bua_khi_khong_co_gi_giong(self):
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/api/v1/catalogs/zzzzzzzz.yaml").json()
        assert body["details"]["suggestions"] == []

    def test_xoa_chi_anh_huong_dung_mot_file(self):
        upload("a.yaml", make_yaml(sid="order-service"))
        upload("b.yaml", make_yaml(sid="payment-service", namespace="payment",
                                   system="payment-system"))
        client.delete("/api/v1/catalogs/a.yaml")
        assert [i["file"] for i in client.get("/api/v1/catalogs").json()["details"]["items"]] == ["b.yaml"]


# ─────────────────────────────────────────────────────────────────────────────
# Bền vững qua restart — thứ mà bản ghi ra thư mục output_json/ không làm được
# ─────────────────────────────────────────────────────────────────────────────


class TestPersistence:
    # Khác namespace/system với VALID_YAML để hai file không tranh chấp quyền
    # sở hữu; thiếu ref 'system' nên vẫn sinh đúng một cảnh báo.
    WARN_KHAC = make_yaml(
        sid="payment-service", namespace="payment", system="payment-system",
        topology="\n    - ref: resource:payment/payment-db",
    )

    def test_nap_lai_chi_muc_tu_db_sau_restart(self):
        """`store.clear()` mô phỏng một lần restart: cache RAM mất sạch, database
        còn nguyên. Nạp lại xong danh sách phải trở lại như cũ — nếu không, người
        dùng sẽ tưởng mất dữ liệu và upload đè lên chính nó."""
        assert upload("order-service.yaml", VALID_YAML).status_code == 201
        assert upload("warn.yaml", self.WARN_KHAC).status_code == 201

        store.clear()
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 0

        assert store.load_from_db() == 2

        items = client.get("/api/v1/catalogs").json()["details"]["items"]
        assert [i["file"] for i in items] == ["order-service.yaml", "warn.yaml"]

        khoi_phuc = {i["file"]: i for i in items}
        assert khoi_phuc["order-service.yaml"]["root"] == "component:order/order-service"
        assert khoi_phuc["order-service.yaml"]["state"] == "valid"
        assert khoi_phuc["order-service.yaml"]["node_count"] > 0
        assert khoi_phuc["warn.yaml"]["state"] == "valid_with_warnings"
        assert khoi_phuc["warn.yaml"]["warning_count"] > 0
        # Nạp lại phải biết mình là dòng nào trong bảng, không để null.
        assert all(isinstance(i["record_id"], int) for i in items)

    def test_canh_bao_chi_tiet_van_con_sau_khi_nap_lai(self):
        """Diagnostics nằm trong JSON nên phải sống sót nguyên vẹn."""
        upload("warn.yaml", WARNING_YAML)
        goc = client.get("/api/v1/catalogs", params={"include": "diagnostics"}).json()

        store.clear()
        store.load_from_db()
        sau = client.get("/api/v1/catalogs", params={"include": "diagnostics"}).json()

        assert sau["details"]["items"][0]["diagnostics"] == \
            goc["details"]["items"][0]["diagnostics"]

    def test_size_bytes_khong_khoi_phuc_duoc_thi_bao_null(self):
        """Kích thước file YAML gốc không phải nội dung của JSON nên không lưu.
        Trả null trung thực hơn là bịa một con số."""
        upload("order-service.yaml", VALID_YAML)
        assert client.get("/api/v1/catalogs").json()["details"]["items"][0]["size_bytes"] > 0

        store.clear()
        store.load_from_db()
        item = client.get("/api/v1/catalogs").json()["details"]["items"][0]
        assert item["size_bytes"] is None
        assert item["uploaded_at"] is not None  # lấy được từ generatedAt

    def test_upload_lai_sau_restart_van_biet_la_ghi_de(self):
        """Cache mất nhưng DB nhớ -> vẫn phải báo FILE_REPLACED, không lặng lẽ
        đè lên bản cũ."""
        upload("order-service.yaml", VALID_YAML)
        store.clear()
        store.load_from_db()

        body = upload("order-service.yaml", VALID_YAML).json()
        assert body["details"]["results"][0]["replaced_existing"] is True
        assert row_count() == 1


# ─────────────────────────────────────────────────────────────────────────────
# Fail-safe
# ─────────────────────────────────────────────────────────────────────────────


class TestFailSafe:
    def test_exception_la_thanh_critical_chu_khong_thanh_success(self, monkeypatch):
        """Nguyên tắc 'Unknown error = Fail safely': không rõ là gì thì coi là hỏng."""
        def no_dau(*args, **kwargs):
            raise RuntimeError("hỏng ở chỗ không ai lường trước")

        monkeypatch.setattr(ingest, "_save_graph_document", no_dau)

        r = upload("order-service.yaml", VALID_YAML)
        assert r.status_code == 500
        body = r.json()
        assert body["status"] == "error"
        assert body["severity"] == "critical"
        assert body["code"] == "INTERNAL_ERROR"
        assert body["can_continue"] is False
        assert body["next_action"] == "contact_support"

    def test_message_loi_he_thong_khong_lo_chi_tiet_noi_bo(self, monkeypatch):
        def no_dau(*args, **kwargs):
            raise RuntimeError("/srv/secret/path/db.sqlite: password=hunter2")

        monkeypatch.setattr(ingest, "_save_graph_document", no_dau)

        body = upload("order-service.yaml", VALID_YAML).json()
        assert "hunter2" not in json.dumps(body)
        assert "/srv/secret" not in json.dumps(body)

    def test_ghi_that_bai_khong_luu_vao_kho(self, monkeypatch):
        """Dựng tài liệu hỏng -> KHÔNG được đánh dấu là đã nạp thành công."""
        def khong_ghi_duoc(*args, **kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(ingest, "merge_documents", khong_ghi_duoc)

        r = upload("order-service.yaml", VALID_YAML)
        assert r.status_code == 500
        assert r.json()["code"] == "STORAGE_FAILURE"
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 0

    def test_db_hong_van_dung_contract_va_khong_lo_dsn(self, monkeypatch):
        """DB chết là tình huống ta HIỂU RÕ -> STORAGE_FAILURE, không phải
        INTERNAL_ERROR. Và thông điệp psycopg2 hay kèm chuỗi kết nối, tức là kèm
        mật khẩu — nó không được phép đi ra tới client."""
        from sqlalchemy.exc import OperationalError

        def db_chet(*args, **kwargs):
            raise OperationalError(
                "SELECT 1",
                {},
                Exception("could not connect: password=sieu-bi-mat host=db.internal"),
            )

        # Chặn ở tầng session chứ không phải ở `save`: như vậy code thật của
        # repository vẫn chạy và ta kiểm tra được đúng phép ánh xạ lỗi của nó.
        monkeypatch.setattr(catalog_repository, "session_scope", db_chet)

        r = upload("order-service.yaml", VALID_YAML)
        assert r.status_code == 500

        body = r.json()
        assert body["code"] == "STORAGE_FAILURE"
        assert body["stage"] == "persist"
        assert body["next_action"] == "contact_support"
        assert "sieu-bi-mat" not in json.dumps(body)
        assert "db.internal" not in json.dumps(body)
        assert client.get("/api/v1/catalogs").json()["details"]["total"] == 0

    def test_route_khong_ton_tai_van_dung_contract(self):
        r = client.get("/khong-co-duong-nay")
        assert r.status_code == 404
        assert r.json()["code"] == "HTTP_404"

    def test_sai_method_van_dung_contract(self):
        r = client.put("/api/v1/catalogs")
        assert r.status_code == 405
        assert r.json()["status"] == "error"


# ─────────────────────────────────────────────────────────────────────────────
# Upload nhiều file cùng lúc
# ─────────────────────────────────────────────────────────────────────────────


class TestBatchUpload:
    def test_nhieu_file_hop_le_deu_duoc_luu(self):
        r = upload_many([
            ("a.yaml", make_yaml(sid="order-service")),
            ("b.yaml", make_yaml(sid="payment-service", namespace="payment",
                                  system="payment-system")),
        ])
        assert r.status_code == 201
        body = r.json()
        assert body["details"]["total"] == 2
        assert body["details"]["succeeded"] == 2
        assert body["details"]["failed"] == 0
        assert row_count() == 2

    def test_1_file_loi_khong_chan_cac_file_con_lai(self):
        r = upload_many([
            ("good.yaml", VALID_YAML),
            ("bad.yaml", INVALID_DATA_YAML),
        ])
        assert r.status_code == 201
        body = r.json()
        assert body["details"]["succeeded"] == 1
        assert body["details"]["failed"] == 1
        assert stored("good.yaml") is not None
        assert stored("bad.yaml") is None
        assert any(i["source"] == "bad.yaml" for i in body["issues"])


class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

