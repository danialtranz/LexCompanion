# LangGraph Base — Lex Companion

Monorepo gồm **API FastAPI** (`api/`), **agent / xử lý văn bản pháp luật** (`deepagent/`), và **model serving** (`model_serving/`). Dependency Python được quản lý bằng **[uv](https://docs.astral.sh/uv/)**; môi trường ảo nằm tại **`.venv/`** ngay trong thư mục project.

---

## Yêu cầu

| Thành phần | Phiên bản |
|------------|-----------|
| Python | **3.12+** |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | mới nhất |
| Docker (tùy chọn) | Postgres, MinIO, Redis — xem `api/deployment.readme.md` |

---

## Cài đặt lần đầu

Tất cả lệnh chạy từ **root repo**:

```bash
cd /path/to/langgraph-base
```

### 1. Tạo môi trường ảo `.venv` (một lần)

```bash
uv venv --python 3.12
```

`uv` tạo thư mục `.venv` **ngay trong project** (không dùng venv global).

### 2. Kích hoạt venv (tùy chọn)

```bash
source .venv/bin/activate   # Linux / macOS
```

Hoặc **không cần activate** — gọi trực tiếp `.venv/bin/python` / `uv run`.

### 3. Cài toàn bộ dependency từ `pyproject.toml`

```bash
uv sync
```

- Đọc `pyproject.toml` + `uv.lock`
- Cài package vào `.venv`
- Project này **`package = false`**: không build wheel `src/langgraph_base` (code nằm ở `api/`, `deepagent/`)

### 4. Biến môi trường

```bash
cp .env.example .env
# Sửa POSTGRES_*, MINIO_*, REDIS_*, JWT_SECRET_KEY, ...
```

### 5. Hạ tầng (Postgres, MinIO, Redis)

```bash
# Ví dụ trong api/deployment.readme.md
docker run ...   # postgres-lex, minio-lex, redis_server
```

API **bắt buộc** Postgres + MinIO khi khởi động; Redis thiếu thì worker nền không chạy nhưng server vẫn lên.

---

## Chạy Lex Companion API

**Không** chạy `python api/lex_companion_server.py` trực tiếp (dễ lỗi import `api.*`).

### Cách khuyến nghị

```bash
uv run --env-file .env python -m api.lex_companion_server
```

Hoặc script:

```bash
chmod +x scripts/start_lex_api.sh
./scripts/start_lex_api.sh
```

Hoặc sau `source .venv/bin/activate`:

```bash
export PYTHONPATH=.
python -m api.lex_companion_server
```

- URL: `http://localhost:5999`
- OpenAPI: `http://localhost:5999/docs`

---

## Quản lý thư viện bằng uv

**Nguồn sự thật:** `pyproject.toml` (và `uv.lock` sau mỗi lần sync).

### Thêm thư viện

```bash
# Thêm vào dependencies chính (production)
uv add requests

# Thêm với version cố định
uv add "pandas>=2.0"

# Thêm nhóm dev (langgraph CLI, pytest, ...)
uv add --dev pytest
```

`uv add` sẽ:

1. Ghi vào `pyproject.toml`
2. Cập nhật `uv.lock`
3. Cài vào `.venv`

### Gỡ thư viện

```bash
uv remove requests

# Gỡ khỏi nhóm dev
uv remove --dev pytest
```

### Cài lại đúng lockfile (sau git pull)

```bash
uv sync
```

### Cài thêm nhóm dev

```bash
uv sync --group dev
```

### Xem package đã cài

```bash
uv pip list
# hoặc
.venv/bin/pip list
```

### Cập nhật một package lên bản mới trong ràng buộc

```bash
uv lock --upgrade-package langchain
uv sync
```

---

## Lệnh **không** nên dùng với repo này

| Lệnh | Lý do |
|------|--------|
| `uv pip install -e .` | Project không đóng gói wheel; sẽ lỗi thiếu `src/langgraph_base/` |
| `pip install -e .` | Giống trên |
| `python api/lex_companion_server.py` | Thiếu `PYTHONPATH=.` → lỗi `ModuleNotFoundError: api` |

Chỉ cần: **`uv sync`** + chạy module **`api.lex_companion_server`**.

---

## Cấu trúc thư mục (rút gọn)

```text
langgraph-base/
├── .venv/                 # Môi trường ảo (uv venv) — không commit
├── .env                   # Biến môi trường local — không commit
├── .env.example
├── pyproject.toml         # Khai báo dependency
├── uv.lock                # Lockfile — nên commit
├── api/                   # FastAPI Lex Companion
│   ├── lex_companion_server.py
│   ├── apps/routers/
│   └── deployment.readme.md
├── deepagent/             # Agent, chunking, LLM providers
├── model_serving/         # Embedding / LLM services riêng (venv riêng)
├── scripts/
│   └── start_lex_api.sh
└── web/                   # Frontend Next.js (yarn, không dùng uv)
```

**Lưu ý:** `model_serving/embeddings/...` và `model_serving/llms/...` có thể có `.venv` riêng cho GPU — **khác** với `.venv` root dùng cho API.

---

## Import code trong repo

Package Python **không** cài editable. Import bằng cách đặt root repo lên `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/langgraph-base
python -c "from api.db.models import DB; print('ok')"
```

`uv run` tự dùng project root khi chạy từ đó.

---

## Xử lý lỗi thường gặp

### `ModuleNotFoundError: langchain_anthropic`

```bash
uv add langchain-anthropic
# hoặc
uv sync
```

### `ModuleNotFoundError: api`

Dùng `python -m api.lex_companion_server` với `PYTHONPATH=.` hoặc `uv run`.

### `uv pip install -e .` → `Expected src/langgraph_base/__init__.py`

Bình thường với layout hiện tại. Dùng **`uv sync`**, không `-e .`.

### MinIO connection failed khi start server

Kiểm tra container MinIO và biến `MINIO_*` trong `.env`.

---

## Phát triển thêm

| Việc cần làm | Lệnh / tài liệu |
|--------------|-----------------|
| Tạo API mới | `api_creating_instruction.md` |
| Docker Postgres/MinIO/Redis | `api/deployment.readme.md` |
| Elasticsearch | `model_serving/retrievers/elastic_search/deployment.readme.md` |
| LangGraph dev (tùy chọn) | `uv sync --group dev` rồi `uv run langgraph dev` |

---

## License

Generated / maintained by project contributors.
