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

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import app
from app.services import ingest
from app.services.store import store

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
    return client.post("/catalogs", files={"file": (name, data, content_type)})


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    """Mỗi test chạy trên kho rỗng và thư mục output riêng — không đụng vào
    output_json/ thật của dự án."""
    monkeypatch.setattr(ingest, "OUTPUT_DIR", str(tmp_path))
    store.clear()
    yield
    store.clear()


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path


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
        lambda: client.get("/catalogs"),
        lambda: client.delete("/catalogs/khong-ton-tai.yaml"),
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
        r = client.get("/catalogs", headers={"X-Request-ID": "trace-abc-123"})
        assert r.json()["request_id"] == "trace-abc-123"


# ─────────────────────────────────────────────────────────────────────────────
# Luồng thành công
# ─────────────────────────────────────────────────────────────────────────────


class TestHappyPath:
    def test_file_hop_le_tra_success_va_ghi_json(self, output_dir):
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
        assert body["details"]["root"] == "component:order/order-service"
        assert body["details"]["node_count"] > 0

        written = output_dir / "order-service.json"
        assert written.exists()
        graph = json.loads(written.read_text(encoding="utf-8"))
        assert graph["nodes"]["component:order/order-service"]["spec"]["type"] == "worker"

    def test_duoi_yml_va_hau_to_catalog_deu_duoc(self, output_dir):
        assert upload("payment.catalog.yml", make_yaml(sid="payment-service")).status_code == 201
        assert (output_dir / "payment.json").exists()

    def test_upload_lai_cung_ten_bao_warning_ghi_de(self):
        upload("order-service.yaml", VALID_YAML)
        body = upload("order-service.yaml", VALID_YAML).json()

        assert body["status"] == "warning"
        assert body["can_continue"] is True
        assert body["details"]["replaced_existing"] is True
        assert any(i["code"] == "FILE_REPLACED" for i in body["issues"])


# ─────────────────────────────────────────────────────────────────────────────
# Warning — đi tiếp được
# ─────────────────────────────────────────────────────────────────────────────


class TestWarning:
    def test_canh_bao_khong_chan_luong(self, output_dir):
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
        # Có warning vẫn phải ghi được file: warning là "để ý", không phải "dừng".
        assert (output_dir / "warn.json").exists()

    def test_file_co_warning_van_nam_trong_danh_sach(self):
        upload("warn.yaml", WARNING_YAML)
        item = client.get("/catalogs").json()["details"]["items"][0]
        assert item["state"] == "valid_with_warnings"
        assert item["warning_count"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1 — basic input
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer1BasicInput:
    def test_khong_gui_file(self):
        r = client.post("/catalogs")
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "NO_FILE"
        assert body["stage"] == "receive"
        assert body["next_action"] == "fix_and_reupload"

    def test_file_rong(self):
        r = upload("empty.yaml", "")
        assert r.status_code == 422
        assert r.json()["code"] == "EMPTY_FILE"

    def test_sai_duoi_file(self):
        r = upload("catalog.txt", VALID_YAML)
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "INVALID_FILE_TYPE"
        assert body["details"]["allowed_extensions"] == [".yaml", ".yml"]

    def test_file_qua_lon(self):
        r = upload("huge.yaml", "#" + "a" * (config.MAX_UPLOAD_BYTES + 1))
        assert r.status_code == 422
        assert r.json()["code"] == "FILE_TOO_LARGE"

    def test_ten_file_qua_dai(self):
        r = upload("a" * 200 + ".yaml", VALID_YAML)
        assert r.status_code == 422
        assert r.json()["code"] == "FILENAME_TOO_LONG"

    def test_content_type_la_khong_bi_chan(self):
        """Content-Type do client khai không đáng tin -> không dùng để chặn."""
        r = upload("order-service.yaml", VALID_YAML, content_type="application/octet-stream")
        assert r.status_code == 201


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
        assert r.status_code == 400
        body = r.json()
        assert body["code"] == "UNSAFE_FILENAME"
        assert body["severity"] == "critical"

    def test_path_traversal_khong_ghi_duoc_file_nao(self, output_dir):
        upload("../../evil.yaml", VALID_YAML)
        assert list(output_dir.rglob("*.json")) == []

    def test_file_nhi_phan_doi_lot_yaml(self):
        r = upload("fake.yaml", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert r.status_code == 400
        body = r.json()
        assert body["code"] == "CONTENT_TYPE_MISMATCH"
        assert body["details"]["detected_format"] == "PNG"

    def test_noi_dung_chua_nul_byte(self):
        r = upload("weird.yaml", VALID_YAML.encode() + b"\x00\x01")
        assert r.status_code == 400
        assert r.json()["code"] == "BINARY_CONTENT"

    def test_tag_python_bi_chan(self):
        payload = "specVersion: !!python/object/apply:os.system ['echo hi']\n"
        r = upload("evil.yaml", payload)
        assert r.status_code == 400
        assert r.json()["code"] == "UNSAFE_YAML_TAG"

    def test_yaml_bomb_bi_chan_truoc_khi_parse(self):
        """'Billion laughs': SafeLoader KHÔNG chặn được, layer 2 phải chặn."""
        lines = ["a0: &a0 'x'"]
        for i in range(1, 40):
            lines.append(f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 8)}]")
        r = upload("bomb.yaml", "\n".join(lines))
        assert r.status_code == 400
        assert r.json()["code"] == "YAML_EXPANSION_BOMB"

    def test_qua_nhieu_dong(self):
        r = upload("long.yaml", "# comment\n" * (config.MAX_YAML_LINES + 1))
        assert r.status_code == 400
        assert r.json()["code"] == "YAML_TOO_MANY_LINES"

    def test_long_nhau_qua_sau(self):
        deep = "".join(" " * (2 * i) + f"k{i}:\n" for i in range(config.MAX_YAML_DEPTH + 5))
        r = upload("deep.yaml", deep)
        assert r.status_code == 400
        assert r.json()["code"] == "YAML_TOO_DEEP"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3 — file integrity
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer3Integrity:
    def test_khong_phai_utf8(self):
        r = upload("latin.yaml", "specVersion: caf\xe9".encode("latin-1"))
        assert r.status_code == 422
        assert r.json()["code"] == "INVALID_ENCODING"

    def test_bom_utf8_van_doc_duoc(self):
        r = upload("bom.yaml", b"\xef\xbb\xbf" + VALID_YAML.encode("utf-8"))
        assert r.status_code == 201

    def test_sai_cu_phap_yaml(self):
        r = upload("broken.yaml", "spec:\n  - a\n b: [unclosed\n")
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "YAML_SYNTAX"
        assert body["stage"] == "layer3_file_integrity"
        assert len(body["issues"]) == 1

    def test_key_trung_bi_tu_choi(self):
        """PyYAML mặc định nuốt key trùng và lấy cái sau. Ở đây phải báo lỗi:
        key trùng gần như luôn là dấu hiệu merge nhầm."""
        dup = VALID_YAML.replace("  domain: commerce", "  domain: commerce\n  domain: retail")
        r = upload("dup.yaml", dup)
        assert r.status_code == 422
        assert r.json()["code"] == "DUPLICATE_KEY"

    def test_root_khong_phai_mapping(self):
        r = upload("list.yaml", "- a\n- b\n")
        assert r.status_code == 422
        assert r.json()["code"] == "INVALID_STRUCTURE"


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4 — schema
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer4Schema:
    def test_thieu_section_bat_buoc(self):
        r = upload("partial.yaml", "specVersion: vsf-idp.io/v2\n")
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "MISSING_REQUIRED_SECTION"
        assert body["stage"] == "layer4_schema"
        assert set(body["details"]["missing_sections"]) == {"metadata", "spec"}

    def test_section_sai_kieu(self):
        r = upload("wrong.yaml", "specVersion: vsf-idp.io/v2\nmetadata: hello\nspec: 123\n")
        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "INVALID_STRUCTURE"
        assert {i["location"] for i in body["issues"]} == {"metadata", "spec"}


# ─────────────────────────────────────────────────────────────────────────────
# Layer 5 — data / business rules
# ─────────────────────────────────────────────────────────────────────────────


class TestLayer5Data:
    def test_gom_het_loi_thay_vi_dung_o_loi_dau_tien(self):
        """Người sửa YAML cần thấy cả 5 lỗi trong một lần, không phải upload 5 lần."""
        r = upload("invalid.yaml", INVALID_DATA_YAML)
        assert r.status_code == 422

        body = r.json()
        assert body["code"] == "SCHEMA_VALIDATION_FAILED"
        assert body["stage"] == "layer5_data"

        errors = [i for i in body["issues"] if i["severity"] == "error"]
        assert len(errors) >= 2
        assert {"INVALID_FORMAT", "MISSING_TECHLEAD"} <= {i["code"] for i in errors}
        assert all(i["location"] for i in errors), "mỗi lỗi phải chỉ đúng vị trí trong YAML"

    def test_sai_specversion(self):
        r = upload("old.yaml", VALID_YAML.replace("vsf-idp.io/v2", "vsf-idp.io/v1"))
        assert r.status_code == 422
        assert any(i["code"] == "UNSUPPORTED_VERSION" for i in r.json()["issues"])

    def test_file_loi_khong_ghi_json_va_khong_vao_kho(self, output_dir):
        """Bản cũ ghi JSON kể cả khi parse còn lỗi -> output tích luỹ rác."""
        upload("invalid.yaml", INVALID_DATA_YAML)
        assert list(output_dir.rglob("*.json")) == []
        assert client.get("/catalogs").json()["details"]["total"] == 0


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

        assert r.status_code == 409
        body = r.json()
        assert body["code"] == "NEEDS_HUMAN_REVIEW"
        assert body["next_action"] == "human_review"
        assert body["can_continue"] is False
        assert body["issues"][0]["code"] == "AMBIGUOUS_OWNER"

    def test_tranh_chap_khong_lam_hong_du_lieu_da_co(self, output_dir):
        upload("a.yaml", self.PROVIDER_A)
        upload("b.yaml", self.PROVIDER_B)
        assert client.get("/catalogs").json()["details"]["total"] == 1
        assert not (output_dir / "b.json").exists()

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
        d = client.get("/catalogs").json()["details"]
        assert d["total"] == 3
        assert d["returned"] == 3
        assert [i["file"] for i in d["items"]] == [
            "order-service.yaml", "order-worker.yaml", "payment-service.yaml"
        ]

    def test_moi_dong_du_thong_tin_de_render_bang(self):
        item = client.get("/catalogs").json()["details"]["items"][0]
        for field in ("file", "root", "state", "error_count", "warning_count",
                      "node_count", "edge_count", "size_bytes", "uploaded_at", "output_file"):
            assert field in item
        assert item["output_file"] == "order-service.json"

    def test_tim_kiem_theo_chuoi_con(self):
        d = client.get("/catalogs", params={"q": "order"}).json()["details"]
        assert d["returned"] == 2
        assert d["total"] == 3
        assert all("order" in i["file"] for i in d["items"])

    def test_tim_kiem_khong_phan_biet_hoa_thuong(self):
        assert client.get("/catalogs", params={"q": "ORDER"}).json()["details"]["returned"] == 2

    def test_tim_khong_thay_van_la_success_voi_danh_sach_rong(self):
        """Không tìm thấy KHÔNG phải lỗi — câu truy vấn đã chạy đúng."""
        body = client.get("/catalogs", params={"q": "khong-co-gi"}).json()
        assert body["status"] == "success"
        assert body["details"]["items"] == []
        assert "khong-co-gi" in body["message"]

    def test_diagnostics_chi_tra_khi_duoc_yeu_cau(self):
        assert client.get("/catalogs").json()["details"]["items"][0]["diagnostics"] is None
        with_diag = client.get("/catalogs", params={"include": "diagnostics"}).json()
        assert with_diag["details"]["items"][0]["diagnostics"] is not None

    def test_include_sai_gia_tri_bi_tu_choi(self):
        r = client.get("/catalogs", params={"include": "everything"})
        assert r.status_code == 422
        assert r.json()["severity"] == "validation"


# ─────────────────────────────────────────────────────────────────────────────
# Xoá
# ─────────────────────────────────────────────────────────────────────────────


class TestDelete:
    def test_xoa_ca_ban_ghi_lan_file_json(self, output_dir):
        upload("order-service.yaml", VALID_YAML)
        assert (output_dir / "order-service.json").exists()

        r = client.delete("/catalogs/order-service.yaml")
        assert r.status_code == 200

        body = r.json()
        assert body["status"] == "success"
        assert body["details"]["remaining"] == 0
        assert not (output_dir / "order-service.json").exists()
        assert client.get("/catalogs").json()["details"]["total"] == 0

    def test_xoa_file_khong_ton_tai_kem_goi_y(self):
        upload("order-service.yaml", VALID_YAML)
        r = client.delete("/catalogs/order-servic.yaml")

        assert r.status_code == 422
        body = r.json()
        assert body["code"] == "CATALOG_NOT_FOUND"
        assert body["can_continue"] is False

    def test_goi_y_khi_go_tat(self):
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/catalogs/order").json()
        assert body["details"]["suggestions"] == ["order-service.yaml"]

    def test_goi_y_khi_go_sai_chinh_ta(self):
        """Gõ thiếu/nhầm một ký tự là lúc cần gợi ý nhất — khớp chuỗi con không lo được."""
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/catalogs/order-servic.yaml").json()
        assert body["details"]["suggestions"] == ["order-service.yaml"]

    def test_khong_goi_y_bua_khi_khong_co_gi_giong(self):
        upload("order-service.yaml", VALID_YAML)
        body = client.delete("/catalogs/zzzzzzzz.yaml").json()
        assert body["details"]["suggestions"] == []

    def test_xoa_chi_anh_huong_dung_mot_file(self):
        upload("a.yaml", make_yaml(sid="order-service"))
        upload("b.yaml", make_yaml(sid="payment-service", namespace="payment",
                                   system="payment-system"))
        client.delete("/catalogs/a.yaml")
        assert [i["file"] for i in client.get("/catalogs").json()["details"]["items"]] == ["b.yaml"]


# ─────────────────────────────────────────────────────────────────────────────
# Fail-safe
# ─────────────────────────────────────────────────────────────────────────────


class TestFailSafe:
    def test_exception_la_thanh_critical_chu_khong_thanh_success(self, monkeypatch):
        """Nguyên tắc 'Unknown error = Fail safely': không rõ là gì thì coi là hỏng."""
        def no_dau(*args, **kwargs):
            raise RuntimeError("hỏng ở chỗ không ai lường trước")

        monkeypatch.setattr(ingest, "_write_graph_json", no_dau)

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

        monkeypatch.setattr(ingest, "_write_graph_json", no_dau)

        body = upload("order-service.yaml", VALID_YAML).json()
        assert "hunter2" not in json.dumps(body)
        assert "/srv/secret" not in json.dumps(body)

    def test_ghi_dia_that_bai_khong_luu_vao_kho(self, monkeypatch):
        """Ghi đĩa hỏng -> KHÔNG được đánh dấu là đã nạp thành công."""
        def khong_ghi_duoc(*args, **kwargs):
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(ingest, "merge_documents", khong_ghi_duoc)

        r = upload("order-service.yaml", VALID_YAML)
        assert r.status_code == 500
        assert r.json()["code"] == "STORAGE_FAILURE"
        assert client.get("/catalogs").json()["details"]["total"] == 0

    def test_route_khong_ton_tai_van_dung_contract(self):
        r = client.get("/khong-co-duong-nay")
        assert r.status_code == 404
        assert r.json()["code"] == "HTTP_404"

    def test_sai_method_van_dung_contract(self):
        r = client.put("/catalogs")
        assert r.status_code == 405
        assert r.json()["status"] == "error"


class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}
