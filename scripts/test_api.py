"""
test_api.py — Kịch bản kiểm thử end-to-end IDP Catalog Graph API.

Khác với `pytest tests/`: bộ này gọi API qua HTTP THẬT trên server thật, đọc
thẳng bảng `input_json` trên Postgres để đối chiếu, và tắt/bật server để chứng
minh dữ liệu sống sót qua restart. Đây là thứ dùng để demo và để tin rằng hệ
thống chạy được ngoài đời, không chỉ trong test in-process.

    .\\.venv\\Scripts\\python.exe scripts/test_api.py

Mặc định script TỰ dựng một uvicorn riêng ở cổng 8765 rồi tự tắt — không cần
chuẩn bị gì. Muốn bắn vào server đang chạy sẵn thì:

    .\\.venv\\Scripts\\python.exe scripts/test_api.py --base-url http://127.0.0.1:8000

(khi đó phần restart bị bỏ qua, vì script không sở hữu tiến trình đó).

AN TOÀN: script ghi vào database THẬT trong .env. Nó chỉ đụng đúng những catalog
do nó tạo ra, dọn sạch lúc kết thúc, và TỪ CHỐI chạy nếu một trong các tên file
nó định dùng đã có sẵn trong bảng — không có đường nào để nó ghi đè dữ liệu của
bạn.
"""

from __future__ import annotations

import argparse
import io
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Console Windows mặc định không phải UTF-8; không ép thì mọi thông điệp tiếng
# Việt do API trả về sẽ hiện thành ký tự rác và người xem tưởng hệ thống hỏng.
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from src.core.config import (  # noqa: E402
    DATABASE_URL,
    DB_SCHEMA,
    DB_SCHEMA_FALLBACK,
    MAX_UPLOAD_BYTES,
    MAX_YAML_DEPTH,
    MAX_YAML_LINES,
)

HAPPY = ROOT / "data" / "happyCase"
BROKEN = ROOT / "data" / "testCase"

# Tên file script sẽ upload. Dùng để kiểm tra va chạm trước khi chạy và để dọn
# dẹp chính xác lúc kết thúc.
CATALOG_SACH = "01-simple-notification-worker.catalog.yaml"
CATALOG_CANH_BAO = "02-normal-order-service.catalog.yaml"
CATALOG_D1 = "D1-order-service.catalog.yaml"
CATALOG_D3 = "D3-order-duplicate.catalog.yaml"
TEN_FILE_SE_TAO = [CATALOG_SACH, CATALOG_CANH_BAO, CATALOG_D1, CATALOG_D3, "bom-utf8.yaml"]


# ─────────────────────────────────────────────────────────────────────────────
# Báo cáo
# ─────────────────────────────────────────────────────────────────────────────


class Report:
    """Gom kết quả và in ra dạng bảng. Không dừng ở lỗi đầu tiên — một lần chạy
    phải cho biết TẤT CẢ những gì đang hỏng, không phải từng cái một."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[str] = []

    def section(self, title: str) -> None:
        print(f"\n\033[1m{title}\033[0m")

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        if ok:
            self.passed += 1
            print(f"  \033[32mPASS\033[0m  {name:<52} {detail}")
        else:
            self.failed.append(name)
            print(f"  \033[31mFAIL\033[0m  {name:<52} {detail}")
        return ok

    def equals(self, name: str, actual: Any, expected: Any) -> bool:
        return self.check(
            name,
            actual == expected,
            f"{actual!r}" if actual == expected else f"nhận {actual!r}, mong {expected!r}",
        )

    def summary(self) -> int:
        total = self.passed + len(self.failed)
        print("\n" + "─" * 78)
        if self.failed:
            print(f"\033[31m{len(self.failed)}/{total} HỎNG\033[0m")
            for name in self.failed:
                print(f"   - {name}")
            return 1
        print(f"\033[32m{total}/{total} PASS\033[0m")
        return 0


# ─────────────────────────────────────────────────────────────────────────────
# Hợp đồng response — tính chất phải đúng cho MỌI response
# ─────────────────────────────────────────────────────────────────────────────

STATUS_THEO_SEVERITY = {
    "none": "success",
    "low": "warning",
    "validation": "error",
    "critical": "error",
}


def vi_pham_contract(body: dict[str, Any]) -> list[str]:
    loi = []
    for field in ("status", "severity", "message", "can_continue", "next_action",
                  "stage", "request_id", "issues", "details"):
        if field not in body:
            loi.append(f"thiếu field '{field}'")
    if not loi:
        mong = STATUS_THEO_SEVERITY.get(body["severity"])
        if body["status"] != mong:
            loi.append(f"status={body['status']} không khớp severity={body['severity']}")
        if body["status"] == "error" and body["can_continue"]:
            loi.append("lỗi nhưng can_continue=True")
        if not body["request_id"]:
            loi.append("request_id rá»—ng")
    return loi


# ─────────────────────────────────────────────────────────────────────────────
# Client
# ─────────────────────────────────────────────────────────────────────────────


class Api:
    def __init__(self, base_url: str, rp: Report) -> None:
        self.base = base_url.rstrip("/")
        self.rp = rp
        self.client = httpx.Client(timeout=30.0)

    def _kiem_contract(self, r: httpx.Response) -> dict[str, Any]:
        try:
            body = r.json()
        except Exception:
            self.rp.check("response là JSON hợp lệ", False, r.text[:80])
            return {}
        for v in vi_pham_contract(body):
            self.rp.check(f"contract: {v}", False, f"{r.request.method} {r.url.path}")
        return body

    def upload(self, name: str, data: bytes | str,
               content_type: str = "application/x-yaml") -> tuple[int, dict[str, Any]]:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        r = self.client.post(f"{self.base}/catalogs",
                             files={"file": (name, raw, content_type)})
        return r.status_code, self._kiem_contract(r)

    def upload_file(self, path: Path) -> tuple[int, dict[str, Any]]:
        return self.upload(path.name, path.read_bytes())

    def get(self, path: str, **params) -> tuple[int, dict[str, Any]]:
        r = self.client.get(f"{self.base}{path}", params=params or None)
        if path == "/health":
            return r.status_code, r.json()
        return r.status_code, self._kiem_contract(r)

    def delete(self, filename: str) -> tuple[int, dict[str, Any]]:
        r = self.client.delete(f"{self.base}/catalogs/{filename}")
        return r.status_code, self._kiem_contract(r)

    def raw(self, method: str, path: str) -> tuple[int, dict[str, Any]]:
        r = self.client.request(method, f"{self.base}{path}")
        return r.status_code, self._kiem_contract(r)


# ─────────────────────────────────────────────────────────────────────────────
# Truy vấn database — nguồn sự thật, không tin lời API kể
# ─────────────────────────────────────────────────────────────────────────────


class Db:
    def __init__(self) -> None:
        if not DATABASE_URL:
            sys.exit("Thiếu DATABASE_URL trong .env — không có database để kiểm chứng.")
        self.schema = DB_SCHEMA or DB_SCHEMA_FALLBACK
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)

    def _q(self, sql: str, **kw):
        with self.engine.connect() as c:
            return c.execute(text(sql.format(s=self.schema)), kw)

    def ten_file_dang_co(self) -> list[str]:
        return [r[0] for r in self._q(
            "select content->'scope'->'sources'->0->>'file' from {s}.input_json"
        ).all()]

    def so_dong(self) -> int:
        return self._q("select count(*) from {s}.input_json").scalar()

    def dong(self, filename: str) -> dict[str, Any] | None:
        r = self._q(
            "select id, jsonb_typeof(content), length(content::text), "
            "  jsonb_array_length(content->'edges'), content->>'generatedAt' "
            "from {s}.input_json "
            "where content->'scope'->'sources'->0->>'file' = :f",
            f=filename,
        ).first()
        if r is None:
            return None
        return {"id": r[0], "kieu": r[1], "so_ky_tu": r[2], "edges": r[3], "generatedAt": r[4]}


# ─────────────────────────────────────────────────────────────────────────────
# Quản lý server tự dựng
# ─────────────────────────────────────────────────────────────────────────────


class Server:
    def __init__(self, port: int) -> None:
        self.port = port
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.main:app",
             "--port", str(self.port), "--log-level", "warning"],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self._doi_san_sang()

    def _doi_san_sang(self, timeout: float = 60.0) -> None:
        base = f"http://127.0.0.1:{self.port}"
        het_han = time.time() + timeout
        while time.time() < het_han:
            if self.proc and self.proc.poll() is not None:
                sys.exit(f"uvicorn chết ngay khi khởi động (exit {self.proc.returncode}).")
            try:
                if httpx.get(f"{base}/health", timeout=2.0).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.4)
        sys.exit(f"Server không lên sau {timeout:.0f}s.")

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.proc = None


def cong_trong(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


# ─────────────────────────────────────────────────────────────────────────────
# Dữ liệu sinh tại chỗ cho các tầng chặn
# ─────────────────────────────────────────────────────────────────────────────

def yaml_toi_thieu(sid: str = "order-service", ns: str = "order",
                   system: str = "order-system") -> str:
    """File hợp lệ nhỏ nhất. Tham số hoá id/namespace vì mỗi file THỰC SỰ được
    lưu phải khai một component khác nhau — hai file cùng khai một node là tranh
    chấp quyền sở hữu (409), đúng luật nghiệp vụ nhưng không phải thứ đang test.
    """
    return f"""specVersion: vsf-idp.io/v2
metadata:
  domain: commerce
  system: {system}
  namespace: {ns}
spec:
  type: worker
  id: {sid}
  name: Demo Service
  owners:
    members:
      - user: alice@example.com
        role: techlead
  review:
    branch: main
  topology:
    - ref: system:{ns}/{system}
"""


# Dùng cho các test BỊ CHẶN trước tầng 5 — không bao giờ được lưu nên id trùng
# nhau cũng không sao.
YAML_TOI_THIEU = yaml_toi_thieu()


def yaml_bomb() -> str:
    """'Billion laughs': 1KB nở ra hàng GB lúc parse. SafeLoader KHÔNG chặn."""
    lines = ["a0: &a0 'x'"]
    for i in range(1, 40):
        lines.append(f"a{i}: &a{i} [{', '.join([f'*a{i - 1}'] * 8)}]")
    return "\n".join(lines)


def yaml_qua_sau() -> str:
    return "".join(" " * (2 * i) + f"k{i}:\n" for i in range(MAX_YAML_DEPTH + 5))


# ─────────────────────────────────────────────────────────────────────────────
# Các nhóm kịch bản
# ─────────────────────────────────────────────────────────────────────────────


def kiem_health(api: Api, rp: Report) -> None:
    rp.section("0. Sức khoẻ dịch vụ")
    code, body = api.get("/health")
    rp.equals("GET /health -> 200", code, 200)
    rp.equals("body = {'status': 'ok'}", body, {"status": "ok"})


def kiem_happy_path(api: Api, db: Db, rp: Report) -> None:
    rp.section("2. Nạp file hợp lệ — sạch tuyệt đối")
    code, body = api.upload_file(HAPPY / CATALOG_SACH)
    rp.equals("POST /catalogs -> 201", code, 201)
    rp.equals("status", body.get("status"), "success")
    rp.equals("severity", body.get("severity"), "none")
    rp.equals("can_continue", body.get("can_continue"), True)
    rp.equals("next_action", body.get("next_action"), "proceed")
    rp.equals("không cảnh báo nào", body.get("issues"), [])

    d = body.get("details", {})
    rp.check("details.record_id là số nguyên", isinstance(d.get("record_id"), int),
             f"record_id={d.get('record_id')}")
    rp.check("details.node_count > 0", d.get("node_count", 0) > 0,
             f"{d.get('node_count')} node / {d.get('edge_count')} edge")

    rp.section("2b. Đối chiếu thẳng trong bảng input_json")
    row = db.dong(CATALOG_SACH)
    rp.check("dòng tồn tại trong database", row is not None)
    if row:
        rp.equals("id trong DB khớp record_id API trả về", row["id"], d.get("record_id"))
        rp.equals("cột content là JSON object", row["kieu"], "object")
        rp.check("content có nội dung thật", row["so_ky_tu"] > 500,
                 f"{row['so_ky_tu']} ký tự, {row['edges']} edge")
        rp.check("có generatedAt để khôi phục uploaded_at", bool(row["generatedAt"]),
                 str(row["generatedAt"]))


def kiem_canh_bao(api: Api, rp: Report) -> None:
    rp.section("3. Nạp file hợp lệ nhưng có cảnh báo — không chặn luồng")
    code, body = api.upload_file(HAPPY / CATALOG_CANH_BAO)
    rp.equals("POST /catalogs -> 201", code, 201)
    rp.equals("status", body.get("status"), "warning")
    rp.equals("severity", body.get("severity"), "low")
    rp.equals("code", body.get("code"), "HAS_WARNINGS")
    rp.equals("can_continue vẫn True", body.get("can_continue"), True)
    rp.equals("next_action", body.get("next_action"), "review_warnings")
    codes = {i["code"] for i in body.get("issues", [])}
    rp.check("có cảnh báo AWAITING_SPEC_INGEST", "AWAITING_SPEC_INGEST" in codes, str(codes))


def kiem_ghi_de(api: Api, db: Db, rp: Report) -> None:
    rp.section("4. Upload lại cùng tên — ghi đè đúng dòng cũ, không sinh dòng mới")
    truoc = db.dong(CATALOG_SACH)
    code, body = api.upload_file(HAPPY / CATALOG_SACH)
    sau = db.dong(CATALOG_SACH)

    rp.equals("POST lần 2 -> 201", code, 201)
    rp.equals("status chuyển thành warning", body.get("status"), "warning")
    rp.equals("details.replaced_existing", body.get("details", {}).get("replaced_existing"), True)
    codes = {i["code"] for i in body.get("issues", [])}
    rp.check("có cảnh báo FILE_REPLACED", "FILE_REPLACED" in codes, str(codes))
    if truoc and sau:
        rp.equals("id không đổi (UPDATE chứ không INSERT)", sau["id"], truoc["id"])


def kiem_layer1(api: Api, rp: Report) -> None:
    rp.section("5. Tầng 1 — input cơ bản")
    cases = [
        ("file rá»—ng", "empty.yaml", "", "application/x-yaml", 422, "EMPTY_FILE"),
        ("sai đuôi file (.txt)", "catalog.txt", YAML_TOI_THIEU, "text/plain",
         422, "INVALID_FILE_TYPE"),
        ("file quá lớn (>1MiB)", "huge.yaml", "#" + "a" * (MAX_UPLOAD_BYTES + 1),
         "application/x-yaml", 422, "FILE_TOO_LARGE"),
        ("tên file quá dài", "a" * 200 + ".yaml", YAML_TOI_THIEU,
         "application/x-yaml", 422, "FILENAME_TOO_LONG"),
    ]
    for ten, fname, data, ctype, http, code in cases:
        got_http, body = api.upload(fname, data, ctype)
        rp.check(ten, got_http == http and body.get("code") == code,
                 f"{got_http} {body.get('code')}")

    # Content-Type do client khai KHÔNG được dùng để chặn — trình duyệt thật hay khai sai.
    # File này ĐƯỢC LƯU nên phải khai component riêng, không đụng file nào khác.
    noi_dung = yaml_toi_thieu(sid="demo-worker", ns="demo", system="demo-system")
    got_http, _ = api.upload("bom-utf8.yaml", b"\xef\xbb\xbf" + noi_dung.encode(),
                             "application/octet-stream")
    rp.check("Content-Type lạ + BOM vẫn được nhận", got_http == 201, str(got_http))


def kiem_layer2(api: Api, rp: Report) -> None:
    rp.section("6. Tầng 2 — an toàn nội dung (chạy trên BYTE THÔ, trước khi parse)")
    cases = [
        ("path traversal ../../etc/passwd.yaml", "../../etc/passwd.yaml",
         YAML_TOI_THIEU, 400, "UNSAFE_FILENAME"),
        ("tên file kiểu Windows ..\\..\\evil.yaml", "..\\..\\windows\\evil.yaml",
         YAML_TOI_THIEU, 400, "UNSAFE_FILENAME"),
        ("PNG đội lốt .yaml", "fake.yaml", b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
         400, "CONTENT_TYPE_MISMATCH"),
        ("nội dung lẫn NUL byte", "weird.yaml", YAML_TOI_THIEU.encode() + b"\x00\x01",
         400, "BINARY_CONTENT"),
        ("tag !!python/object", "evil.yaml",
         "specVersion: !!python/object/apply:os.system ['echo hi']\n",
         400, "UNSAFE_YAML_TAG"),
        ("YAML bomb (billion laughs)", "bomb.yaml", yaml_bomb(),
         400, "YAML_EXPANSION_BOMB"),
        ("quá nhiều dòng", "long.yaml", "# comment\n" * (MAX_YAML_LINES + 1),
         400, "YAML_TOO_MANY_LINES"),
        ("lồng nhau quá sâu", "deep.yaml", yaml_qua_sau(), 400, "YAML_TOO_DEEP"),
    ]
    for ten, fname, data, http, code in cases:
        got_http, body = api.upload(fname, data)
        rp.check(ten, got_http == http and body.get("code") == code,
                 f"{got_http} {body.get('code')}")


def kiem_layer3_4(api: Api, rp: Report) -> None:
    rp.section("7. Tầng 3 & 4 — toàn vẹn file và cấu trúc")
    dup = YAML_TOI_THIEU.replace("  domain: commerce", "  domain: commerce\n  domain: retail")
    cases = [
        ("không phải UTF-8", "latin.yaml", "specVersion: caf\xe9".encode("latin-1"),
         422, "INVALID_ENCODING"),
        ("cú pháp YAML vỡ", "broken.yaml", "spec:\n  - a\n b: [unclosed\n",
         422, "YAML_SYNTAX"),
        ("key trùng lặp", "dup.yaml", dup, 422, "DUPLICATE_KEY"),
        ("root không phải mapping", "list.yaml", "- a\n- b\n", 422, "INVALID_STRUCTURE"),
        ("thiếu section bắt buộc", "partial.yaml", "specVersion: vsf-idp.io/v2\n",
         422, "MISSING_REQUIRED_SECTION"),
        ("section sai kiểu", "wrong.yaml",
         "specVersion: vsf-idp.io/v2\nmetadata: hello\nspec: 123\n",
         422, "INVALID_STRUCTURE"),
    ]
    for ten, fname, data, http, code in cases:
        got_http, body = api.upload(fname, data)
        rp.check(ten, got_http == http and body.get("code") == code,
                 f"{got_http} {body.get('code')}")

    # File vỡ cú pháp thật từ bộ fixture -> đúng 1 lỗi, dừng ngay (fail-fast).
    got_http, body = api.upload_file(BROKEN / "C-broken-syntax.catalog.yaml")
    rp.check("C-broken-syntax.catalog.yaml -> YAML_SYNTAX, đúng 1 lỗi",
             got_http == 422 and body.get("code") == "YAML_SYNTAX"
             and len(body.get("issues", [])) == 1,
             f"{got_http} {body.get('code')} / {len(body.get('issues', []))} lá»—i")


def kiem_layer5(api: Api, db: Db, rp: Report) -> None:
    rp.section("8. Tầng 5 — luật nghiệp vụ (GOM HẾT lỗi, không dừng ở lỗi đầu)")

    got_http, body = api.upload_file(BROKEN / "A-invalid-fields.catalog.yaml")
    loi = [i for i in body.get("issues", []) if i["severity"] == "error"]
    rp.equals("A-invalid-fields -> 422", got_http, 422)
    rp.equals("code", body.get("code"), "SCHEMA_VALIDATION_FAILED")
    rp.equals("stage", body.get("stage"), "layer5_data")
    rp.check("gom đúng 13 lỗi trong MỘT response", len(loi) == 13, f"{len(loi)} lỗi")
    rp.check("mỗi lỗi đều chỉ đúng vị trí trong YAML",
             all(i.get("location") for i in loi),
             f"{sum(1 for i in loi if i.get('location'))}/{len(loi)} có location")
    co = {i["code"] for i in loi}
    for ma in ("UNSUPPORTED_VERSION", "INVALID_FORMAT", "INVALID_ENUM",
               "MISSING_TECHLEAD", "INVALID_REF", "UNKNOWN_KIND"):
        rp.check(f"  bắt được {ma}", ma in co)

    got_http, body = api.upload_file(BROKEN / "B-missing-required.catalog.yaml")
    loi = [i for i in body.get("issues", []) if i["severity"] == "error"]
    rp.check("B-missing-required -> 422 với đúng 5 lỗi REQUIRED",
             got_http == 422 and len(loi) == 5
             and all(i["code"] == "REQUIRED" for i in loi),
             f"{got_http}, {len(loi)} lá»—i: {sorted({i['code'] for i in loi})}")

    rp.check("file lỗi KHÔNG để lại gì trong database",
             db.dong("A-invalid-fields.catalog.yaml") is None
             and db.dong("B-missing-required.catalog.yaml") is None)


def kiem_hitl(api: Api, db: Db, rp: Report) -> None:
    """Chạy ĐẦU TIÊN, trên bảng rỗng.

    D1 và D3 cùng khai `component:order/order-service`. Nếu để sau các bước khác
    thì D1 sẽ tranh chấp với catalog đã nạp trước đó và ta không còn phân biệt
    được "D1 xung đột với D3" — đúng thứ đang muốn kiểm — với "D1 xung đột với
    một file bất kỳ nào đó". Kết thúc, section này xoá D1 để trả lại bảng rỗng.
    """
    rp.section("1. Human-in-the-loop — tranh chấp quyền sở hữu giữa 2 file")
    code_d1, _ = api.upload_file(BROKEN / CATALOG_D1)
    rp.equals("D1 nạp được (từng file riêng đều hợp lệ)", code_d1, 201)

    code_d3, body = api.upload_file(BROKEN / CATALOG_D3)
    rp.equals("D3 -> 409 Conflict", code_d3, 409)
    rp.equals("code", body.get("code"), "NEEDS_HUMAN_REVIEW")
    rp.equals("next_action", body.get("next_action"), "human_review")
    rp.equals("can_continue", body.get("can_continue"), False)
    co = {i["code"] for i in body.get("issues", [])}
    rp.check("chỉ rõ tranh chấp gì", co & {"AMBIGUOUS_OWNER", "DUPLICATE_DECLARATION"} != set(),
             str(co))
    rp.check("D3 KHÔNG được ghi vào database", db.dong(CATALOG_D3) is None)
    rp.check("D1 đã có vẫn còn nguyên", db.dong(CATALOG_D1) is not None)

    api.delete(CATALOG_D1)
    rp.check("dọn D1, trả bảng về rỗng cho các bước sau", db.so_dong() == 0,
             f"{db.so_dong()} dòng")


def kiem_liet_ke(api: Api, rp: Report) -> None:
    rp.section("9. Danh sách và tìm kiếm")
    code, body = api.get("/catalogs")
    d = body.get("details", {})
    rp.equals("GET /catalogs -> 200", code, 200)
    rp.check("details.total khớp số item trả về", d.get("total") == len(d.get("items", [])),
             f"total={d.get('total')}")
    rp.check("item đủ field để render bảng",
             all(k in (d.get("items") or [{}])[0] for k in
                 ("file", "root", "state", "error_count", "warning_count", "node_count",
                  "edge_count", "size_bytes", "uploaded_at", "output_file", "record_id")))

    _, body = api.get("/catalogs", q="order")
    d = body.get("details", {})
    rp.check("tìm theo chuỗi con ?q=order",
             all("order" in i["file"] for i in d.get("items", [])) and d.get("returned", 0) > 0,
             f"{d.get('returned')}/{d.get('total')} file")

    _, body = api.get("/catalogs", q="ORDER")
    rp.check("tìm kiếm không phân biệt hoa thường",
             body.get("details", {}).get("returned", 0) > 0)

    _, body = api.get("/catalogs", q="khong-ton-tai-dau")
    rp.check("không tìm thấy vẫn là success, không phải lỗi",
             body.get("status") == "success"
             and body.get("details", {}).get("returned") == 0)

    _, body = api.get("/catalogs")
    rp.check("mặc định KHÔNG kèm diagnostics",
             body["details"]["items"][0].get("diagnostics") is None)
    _, body = api.get("/catalogs", include="diagnostics")
    rp.check("?include=diagnostics thì có chi tiết",
             body["details"]["items"][0].get("diagnostics") is not None)


def kiem_xoa(api: Api, db: Db, rp: Report) -> None:
    rp.section("10. Xoá và gợi ý tên")
    code, body = api.delete(CATALOG_CANH_BAO)
    rp.equals(f"DELETE {CATALOG_CANH_BAO} -> 200", code, 200)
    rp.equals("status", body.get("status"), "success")
    rp.check("dòng đã biến mất khỏi database", db.dong(CATALOG_CANH_BAO) is None)

    code, body = api.delete("khong-co-that.yaml")
    rp.equals("xoá file không tồn tại -> 422", code, 422)
    rp.equals("code", body.get("code"), "CATALOG_NOT_FOUND")
    rp.equals("can_continue", body.get("can_continue"), False)

    _, body = api.delete("01-simple")
    rp.check("gõ tắt vẫn gợi ý được tên đầy đủ",
             CATALOG_SACH in body.get("details", {}).get("suggestions", []),
             str(body.get("details", {}).get("suggestions")))

    _, body = api.delete("01-simple-notification-worker.catalog.yam")
    rp.check("gõ sai một ký tự vẫn gợi ý được (khớp mờ)",
             CATALOG_SACH in body.get("details", {}).get("suggestions", []),
             str(body.get("details", {}).get("suggestions")))

    _, body = api.delete("zzzzzzzzzzzz.yaml")
    rp.check("không gợi ý bừa khi không có gì giống",
             body.get("details", {}).get("suggestions") == [])


def kiem_fail_safe(api: Api, rp: Report) -> None:
    rp.section("11. Fail-safe — lỗi ngoài luồng vẫn đúng contract")
    code, body = api.raw("GET", "/duong-dan-khong-ton-tai")
    rp.check("route lạ -> 404 đúng contract",
             code == 404 and body.get("code") == "HTTP_404", f"{code} {body.get('code')}")

    code, body = api.raw("PUT", "/catalogs")
    rp.check("sai HTTP method -> 405 đúng contract",
             code == 405 and body.get("status") == "error", f"{code} {body.get('status')}")

    r = api.client.post(f"{api.base}/catalogs")
    body = r.json()
    rp.check("POST không kèm file -> NO_FILE",
             r.status_code == 422 and body.get("code") == "NO_FILE",
             f"{r.status_code} {body.get('code')}")

    r = api.client.get(f"{api.base}/catalogs", headers={"X-Request-ID": "demo-trace-123"})
    rp.check("X-Request-ID của client được giữ nguyên trong log và response",
             r.headers.get("X-Request-ID") == "demo-trace-123"
             and r.json()["request_id"] == "demo-trace-123",
             r.headers.get("X-Request-ID", ""))


def kiem_restart(server: Server, api: Api, db: Db, rp: Report) -> None:
    rp.section("12. Bền vững qua RESTART — thứ bản ghi ra output_json/ không làm được")
    truoc = {i["file"]: i for i in api.get("/catalogs")[1]["details"]["items"]}
    rp.check("có dữ liệu trước khi restart", len(truoc) > 0, f"{len(truoc)} catalog")

    print("        ... tắt uvicorn và bật lại")
    server.stop()
    server.start()

    code, body = api.get("/catalogs")
    sau = {i["file"]: i for i in body["details"]["items"]}
    rp.equals("GET /catalogs sau restart -> 200", code, 200)
    rp.check("danh sách còn nguyên sau restart",
             set(sau) == set(truoc), f"{len(sau)}/{len(truoc)} catalog")

    for ten in truoc:
        if ten not in sau:
            continue
        rp.equals(f"  {ten}: record_id giữ nguyên", sau[ten]["record_id"],
                  truoc[ten]["record_id"])

    mau = next(iter(sau.values()), {})
    rp.check("size_bytes = null (không nằm trong JSON, đúng thiết kế)",
             mau.get("size_bytes") is None, str(mau.get("size_bytes")))
    rp.check("uploaded_at khôi phục được từ generatedAt",
             mau.get("uploaded_at") is not None, str(mau.get("uploaded_at")))
    rp.check("số liệu đồ thị khôi phục nguyên vẹn",
             mau.get("node_count", 0) > 0 and mau.get("root"),
             f"{mau.get('node_count')} node, root={mau.get('root')}")


def don_dep(api: Api, db: Db, rp: Report, goc: int) -> None:
    rp.section("13. Dọn dẹp — trả database về đúng trạng thái ban đầu")
    con_lai = [i["file"] for i in api.get("/catalogs")[1]["details"]["items"]]
    for ten in con_lai:
        api.delete(ten)
    rp.check("đã xoá hết catalog do script tạo", len(con_lai) >= 0, f"{len(con_lai)} file")
    rp.equals("số dòng trong input_json trở lại như trước khi chạy", db.so_dong(), goc)


# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Kiểm thử end-to-end IDP Catalog Graph API")
    ap.add_argument("--base-url", help="Bắn vào server có sẵn (bỏ qua phần restart)")
    ap.add_argument("--port", type=int, default=8765, help="Cổng cho server script tự dựng")
    args = ap.parse_args()

    for thu_muc in (HAPPY, BROKEN):
        if not thu_muc.is_dir():
            sys.exit(f"Không tìm thấy {thu_muc} — bộ test cần dữ liệu mẫu trong data/.")

    db = Db()
    print(f"Database : {db.schema}.input_json")

    # Không chạy nếu sẽ giẫm lên dữ liệu có sẵn.
    dang_co = db.ten_file_dang_co()
    va_cham = sorted(set(dang_co) & set(TEN_FILE_SE_TAO))
    if va_cham:
        sys.exit(
            "DỪNG: bảng đã có sẵn catalog trùng tên với file mà script sẽ upload:\n  "
            + "\n  ".join(va_cham)
            + "\nChạy tiếp sẽ ghi đè dữ liệu của bạn. Hãy xoá chúng trước, hoặc đổi "
              "DATABASE_URL sang schema khác."
        )
    so_dong_goc = db.so_dong()
    print(f"Ban đầu  : {so_dong_goc} dòng trong bảng")

    server: Server | None = None
    if args.base_url:
        base = args.base_url
        print(f"Server   : {base} (có sẵn — bỏ qua kịch bản restart)")
    else:
        if not cong_trong(args.port):
            sys.exit(f"Cổng {args.port} đang bận. Dùng --port <khác> hoặc --base-url.")
        server = Server(args.port)
        print(f"Server   : script tự dựng uvicorn ở cổng {args.port}")
        server.start()
        base = f"http://127.0.0.1:{args.port}"

    rp = Report()
    api = Api(base, rp)
    try:
        kiem_health(api, rp)
        # HITL chạy trước, lúc bảng còn rỗng — xem docstring của nó.
        kiem_hitl(api, db, rp)
        kiem_happy_path(api, db, rp)
        kiem_canh_bao(api, rp)
        kiem_ghi_de(api, db, rp)
        kiem_layer1(api, rp)
        kiem_layer2(api, rp)
        kiem_layer3_4(api, rp)
        kiem_layer5(api, db, rp)
        kiem_liet_ke(api, rp)
        kiem_xoa(api, db, rp)
        kiem_fail_safe(api, rp)
        if server is not None:
            kiem_restart(server, api, db, rp)
        don_dep(api, db, rp, so_dong_goc)
    finally:
        api.client.close()
        if server is not None:
            server.stop()

    return rp.summary()


if __name__ == "__main__":
    raise SystemExit(main())


