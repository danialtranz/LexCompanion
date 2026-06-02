import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from peewee import (
    AutoField,
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    FloatField,
    ForeignKeyField,
    IntegerField,
    Model,
    PostgresqlDatabase,
    TextField,
)
from playhouse.migrate import PostgresqlMigrator, migrate
from playhouse.postgres_ext import JSONField

from api.utils.utils import current_timestamp
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


POSTGRES_CONFIG = {
    "db": os.getenv("POSTGRES_DB", ""),
    "user": os.getenv("POSTGRES_USER", ""),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "sslmode": os.getenv("POSTGRES_SSLMODE", "disable"),
}

def _build_database() -> PostgresqlDatabase:
    return PostgresqlDatabase(
        POSTGRES_CONFIG["db"],
        user=POSTGRES_CONFIG["user"],
        password=POSTGRES_CONFIG["password"],
        host=POSTGRES_CONFIG["host"],
        port=POSTGRES_CONFIG["port"],
        sslmode=POSTGRES_CONFIG["sslmode"],
    )


db = _build_database()
DB = db


class BaseModel(Model):
    create_date = DateTimeField(default=datetime.utcnow)
    update_date = DateTimeField(default=datetime.utcnow)
    create_time = BigIntegerField(default=lambda: int(current_timestamp()))
    update_time = BigIntegerField(default=lambda: int(current_timestamp()))
    class Meta:
        database = db

    def save(self, *args, **kwargs):
        self.update_date = datetime.utcnow()
        self.update_time = int(current_timestamp())
        return super().save(*args, **kwargs)


class Users(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    email = TextField()
    username = TextField()
    password = TextField(null=True)
    super_admin = BooleanField(default=False)
    status = TextField()

    class Meta:
        table_name = "users"


class Knowledgebase(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    avatar = TextField(null=True, help_text="avatar base64 string")
    tenant_id = CharField(max_length=36, null=False, index=True)
    name = CharField(max_length=128, null=False, help_text="KB name", index=True)
    language = CharField(max_length=36, null=True, default="vietnamese" , index=True)
    description = TextField(null=True, help_text="KB description")
    permission = CharField(max_length=16, null=False, help_text="me|team", default="me", index=True)
    created_by = CharField(max_length=36, null=False, index=True)
    doc_num = IntegerField(default=0, index=True)
    token_num = IntegerField(default=0, index=True)
    chunk_num = IntegerField(default=0, index=True)
    similarity_threshold = FloatField(default=0.2, index=True)
    vector_size = IntegerField(default=0, index=True)


    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "knowledgebases"


class Document(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    thumbnail = TextField(null=True, help_text="thumbnail base64 string")
    kb_id = CharField(max_length=256, null=False, index=True)
    file_id = CharField(max_length=36, null=True, help_text="file id", index=True)
    source_type = CharField(max_length=128, null=False, default="local", help_text="where dose this document come from", index=True)
    type = CharField(max_length=36, null=False, help_text="file extension", index=True)
    created_by = CharField(max_length=36, null=False, help_text="who created it", index=True)
    name = CharField(max_length=255, null=True, help_text="file name", index=True)
    location = CharField(max_length=255, null=True, help_text="where dose it store Example : Elasticsearch", index=True)
    size = IntegerField(default=0, index=True)
    token_num = IntegerField(default=0, index=True)
    chunk_num = IntegerField(default=0, index=True)
    progress = FloatField(default=0, index=True)
    
    process_duration = FloatField(default=0)
    suffix = CharField(max_length=36, null=False, help_text="The real file extension suffix", index=True)

    content_hash = CharField(max_length=36, null=True, help_text="xxhash128 of document content for change detection", default="", index=True)

    run = CharField(max_length=1, null=True, help_text="start to run processing or cancel.(1: run it; 2: cancel)", default="0", index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)
    
   
    class Meta:
        db_table = "documents"


class File(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    tenant_id = CharField(max_length=36, null=False, help_text="tenant id", index=True)
    created_by = CharField(max_length=36, null=False, help_text="who created it", index=True)
    name = CharField(max_length=255, null=False, help_text="file name", index=True)
    location = TextField(null=True, help_text="where dose it store example : minio or html content", index=True)
    file_content = TextField(null=True, help_text="file content", index=False)
    size = IntegerField(default=0, index=True)
    type = CharField(max_length=36, null=False, help_text="file extension", index=True)
    source_type = CharField(max_length=128, null=False, default="", help_text="where dose this document come from", index=True)

    class Meta:
        db_table = "files"




class Tenant(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    name = CharField(max_length=100, null=True, help_text="Tenant name", index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "tenants"


class UserTenant(BaseModel):
    id = CharField(max_length=36, primary_key=True)
    user_id = CharField(max_length=36, null=False, index=True)
    tenant_id = CharField(max_length=36, null=False, index=True)
    role = CharField(max_length=36, null=False, help_text="UserTenantRole", index=True)
    invited_by = CharField(max_length=36, null=False, index=True)
    status = CharField(max_length=1, null=True, help_text="is it validate(0: wasted, 1: validate)", default="1", index=True)

    class Meta:
        db_table = "user_tenants"


class _LegalTimestampModel(Model):
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)


class LegalTopic(_LegalTimestampModel):
    """ontology_topics — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    topic_id = TextField(null=True, index=True)
    topic_number = BigIntegerField(null=True, index=True)
    topic_title_vi = TextField(null=True)
    topic_title_en = TextField(null=True)
    topic_note = TextField(null=True)
    article_count = BigIntegerField(null=True)
    demuc_count = BigIntegerField(null=True)

    class Meta:
        table_name = "legal_topics"


class LegalSubject(_LegalTimestampModel):
    """subjects — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    subject_id = TextField(null=False, index=True)
    topic_id = TextField(null=True, index=True)
    topic_number = BigIntegerField(null=True, index=True)
    topic_title = TextField(null=True)
    subject_number = BigIntegerField(null=True, index=True)
    subject_title = TextField(null=True)
    source_url = TextField(null=True)
    file_version = TextField(null=True)
    fetch_status = TextField(null=True, index=True)
    fetch_error = TextField(null=True)
    scraped_at = TextField(null=True)

    class Meta:
        table_name = "legal_subjects"


class LegalTreeNode(_LegalTimestampModel):
    """tree_nodes — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    node_id = TextField(null=False, index=True)
    parent_id = TextField(null=True, index=True)
    kind = TextField(null=True, index=True)
    number = BigIntegerField(null=True, index=True)
    title = TextField(null=True)
    raw_text = TextField(null=True)

    class Meta:
        table_name = "legal_tree_nodes"


class LegalArticle(_LegalTimestampModel):
    """articles — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    subject_id = TextField(null=False, index=True)
    topic_id = TextField(null=True, index=True)
    topic_number = BigIntegerField(null=True, index=True)
    topic_title = TextField(null=True)
    subject_number = BigIntegerField(null=True, index=True)
    subject_title = TextField(null=True)
    article_anchor = TextField(null=True, index=True)
    article_title = TextField(null=True)
    chapter_title = TextField(null=True)
    source_note_text = TextField(null=True)
    source_links = JSONField(null=True)
    related_note_text = TextField(null=True)
    content_text = TextField(null=True)
    content_char_len = BigIntegerField(null=True)
    content_word_count = BigIntegerField(null=True)
    source_url = TextField(null=True)
    scraped_at = TextField(null=True)

    class Meta:
        table_name = "legal_articles"


class LegalOntologySubject(_LegalTimestampModel):
    """ontology_subjects — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    topic_id = TextField(null=True, index=True)
    topic_number = BigIntegerField(null=True, index=True)
    topic_title_vi = TextField(null=True)
    topic_title_en = TextField(null=True)
    subject_id = TextField(null=True, index=True)
    subject_title_vi = TextField(null=True)
    subject_title_en = TextField(null=True)
    article_count = BigIntegerField(null=True)

    class Meta:
        table_name = "legal_ontology_subjects"


class LegalGlossary(_LegalTimestampModel):
    """ontology_glossary — schema tmquan/phapdien-moj-gov-vn."""

    id = AutoField(primary_key=True)
    category = TextField(null=True, index=True)
    vi = TextField(null=False, index=True)
    en = TextField(null=True)
    note = TextField(null=True)

    class Meta:
        table_name = "legal_glossary"


class LegalIngestionJob(Model):
    id = AutoField(primary_key=True)
    dataset_name = TextField(null=True, index=True)
    dataset_version = TextField(null=True)
    status = TextField(null=True, index=True)
    started_at = DateTimeField(null=True)
    finished_at = DateTimeField(null=True)
    total_rows = IntegerField(null=True)
    success_rows = IntegerField(null=True)
    failed_rows = IntegerField(null=True)
    error_message = TextField(null=True)
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db
        table_name = "legal_ingestion_jobs"


class ChatSession(_LegalTimestampModel):
    """Cuộc trò chuyện — bảng chat_sessions."""

    id = CharField(max_length=36, primary_key=True)
    user_id = CharField(max_length=36, null=False, index=True)
    title = TextField(null=True)
    metadata = JSONField(default=dict)
    status = CharField(max_length=64, null=True, index=True)
    deleted_at = DateTimeField(null=True)

    class Meta:
        table_name = "chat_sessions"


class ChatMessage(Model):
    """Tin nhắn trong phiên — bảng chat_messages."""

    id = CharField(max_length=36, primary_key=True)
    session = ForeignKeyField(
        ChatSession,
        backref="messages",
        column_name="session_id",
        on_delete="CASCADE",
        index=True,
    )
    user_id = CharField(max_length=36, null=True, index=True)
    role = CharField(max_length=16, null=False)
    content = TextField(null=False)
    message_references = JSONField(default=list, column_name="references")
    created_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        database = db
        table_name = "chat_messages"

    VALID_ROLES = frozenset({"user", "assistant", "system", "tool"})

    @property
    def references(self):
        return self.message_references

    @references.setter
    def references(self, value):
        self.message_references = value

    def save(self, *args, **kwargs):
        if self.role not in self.VALID_ROLES:
            raise ValueError(
                f"Invalid role {self.role!r}; must be one of {sorted(self.VALID_ROLES)}"
            )
        return super().save(*args, **kwargs)


CHAT_MODELS = [ChatSession, ChatMessage]

LEGAL_MODELS = [
    LegalTopic,
    LegalSubject,
    LegalTreeNode,
    LegalArticle,
    LegalOntologySubject,
    LegalGlossary,
    LegalIngestionJob,
]


def _constraint_exists(constraint_name: str) -> bool:
    row = db.execute_sql(
        """
        SELECT 1
        FROM pg_constraint
        WHERE conname = %s
        LIMIT 1
        """,
        (constraint_name,),
    ).fetchone()
    return row is not None


def _chat_messages_session_fk_exists() -> bool:
    row = db.execute_sql(
        """
        SELECT 1
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = 'public'
          AND tc.table_name = 'chat_messages'
          AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = 'session_id'
        LIMIT 1
        """
    ).fetchone()
    return row is not None


def _ensure_chat_messages_constraints() -> None:
    """Bổ sung FK và CHECK role nếu bảng được tạo qua migrate từng cột."""
    if not _column_exists(ChatMessage._meta.table_name, "session_id"):
        return

    if not _chat_messages_session_fk_exists():
        db.execute_sql(
            """
            ALTER TABLE chat_messages
            ADD CONSTRAINT chat_messages_session_id_fkey
            FOREIGN KEY (session_id)
            REFERENCES chat_sessions (id)
            ON DELETE CASCADE
            """
        )

    if not _constraint_exists("chat_messages_role_check"):
        db.execute_sql(
            """
            ALTER TABLE chat_messages
            ADD CONSTRAINT chat_messages_role_check
            CHECK (role IN ('user', 'assistant', 'system', 'tool'))
            """
        )


def _column_exists(table_name: str, column_name: str) -> bool:
    query = """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
    """
    row = db.execute_sql(query, (table_name, column_name)).fetchone()
    return row is not None


def _column_data_type(table_name: str, column_name: str) -> str | None:
    row = db.execute_sql(
        """
        SELECT data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
          AND column_name = %s
        LIMIT 1
        """,
        (table_name, column_name),
    ).fetchone()
    return row[0] if row else None


def _migrate_users_id_to_charfield() -> None:
    """
    Chuẩn hóa users.id khỏi CHAR padding:
    - Trim dữ liệu để loại trailing spaces.
    - Chặn trường hợp trim gây trùng khóa.
    - Đổi kiểu cột users.id sang VARCHAR(36).
    """
    users_table = Users._meta.table_name
    if not _column_exists(users_table, "id"):
        return

    # Nếu đã là varchar thì chỉ cần đảm bảo dữ liệu sạch ở các cột user_id liên quan.
    data_type = _column_data_type(users_table, "id")

    duplicate_trimmed = db.execute_sql(
        f"""
        SELECT TRIM(id) AS trimmed_id, COUNT(*) AS c
        FROM {users_table}
        GROUP BY TRIM(id)
        HAVING COUNT(*) > 1
        LIMIT 1
        """
    ).fetchone()
    if duplicate_trimmed:
        raise RuntimeError(
            f"Cannot migrate users.id: trimmed duplicate key detected for {duplicate_trimmed[0]!r}"
        )

    db.execute_sql(f"UPDATE {users_table} SET id = TRIM(id) WHERE id <> TRIM(id)")

    # Đồng bộ tất cả cột user_id đang dùng trong hệ thống hiện tại.
    for table_name, column_name in [
        (UserTenant._meta.table_name, "user_id"),
        (ChatSession._meta.table_name, "user_id"),
        (ChatMessage._meta.table_name, "user_id"),
    ]:
        if _column_exists(table_name, column_name):
            db.execute_sql(
                f"""
                UPDATE {table_name}
                SET {column_name} = TRIM({column_name})
                WHERE {column_name} IS NOT NULL
                  AND {column_name} <> TRIM({column_name})
                """
            )

    if data_type == "character":
        db.execute_sql(
            f"""
            ALTER TABLE {users_table}
            ALTER COLUMN id TYPE VARCHAR(36)
            """
        )


def _build_migration_ops(migrator: PostgresqlMigrator):
    tables_columns = {
        Users._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "email": lambda: TextField(),
            "username": lambda: TextField(),
            "password": lambda: TextField(null=True),
            "super_admin": lambda: BooleanField(default=False),
            "status": lambda: TextField(),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        Knowledgebase._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "avatar": lambda: TextField(null=True),
            "tenant_id": lambda: CharField(max_length=36, null=False, index=True),
            "name": lambda: CharField(max_length=128, null=False, index=True),
            "language": lambda: CharField(max_length=36, null=True, default="vietnamese", index=True),
            "description": lambda: TextField(null=True),
            "permission": lambda: CharField(max_length=16, null=False, default="me", index=True),
            "created_by": lambda: CharField(max_length=36, null=False, index=True),
            "doc_num": lambda: IntegerField(default=0, index=True),
            "token_num": lambda: IntegerField(default=0, index=True),
            "chunk_num": lambda: IntegerField(default=0, index=True),
            "similarity_threshold": lambda: FloatField(default=0.2, index=True),
            "vector_size": lambda: IntegerField(default=0, index=True),
            "status": lambda: CharField(max_length=1, null=True, default="1", index=True),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        Document._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "thumbnail": lambda: TextField(null=True),
            "kb_id": lambda: CharField(max_length=256, null=False, index=True),
            "file_id": lambda: CharField(max_length=36, null=True, index=True),
            "source_type": lambda: CharField(max_length=128, null=False, default="local", index=True),
            "type": lambda: CharField(max_length=36, null=False, index=True),
            "created_by": lambda: CharField(max_length=36, null=False, index=True),
            "name": lambda: CharField(max_length=255, null=True, index=True),
            "location": lambda: CharField(max_length=255, null=True, index=True),
            "size": lambda: IntegerField(default=0, index=True),
            "token_num": lambda: IntegerField(default=0, index=True),
            "chunk_num": lambda: IntegerField(default=0, index=True),
            "progress": lambda: FloatField(default=0, index=True),
            "process_duration": lambda: FloatField(default=0),
            "suffix": lambda: CharField(max_length=36, null=False, index=True),
            "content_hash": lambda: CharField(max_length=36, null=True, default="", index=True),
            "run": lambda: CharField(max_length=1, null=True, default="0", index=True),
            "status": lambda: CharField(max_length=1, null=True, default="1", index=True),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        File._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "tenant_id": lambda: CharField(max_length=36, null=False, index=True),
            "created_by": lambda: CharField(max_length=36, null=False, index=True),
            "name": lambda: CharField(max_length=255, null=False, index=True),
            "location": lambda: TextField(null=True, index=True),
            "file_content": lambda: TextField(null=True, index=False),
            "size": lambda: IntegerField(default=0, index=True),
            "type": lambda: CharField(max_length=36, null=False, index=True),
            "source_type": lambda: CharField(max_length=128, null=False, default="", index=True),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        Tenant._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "name": lambda: CharField(max_length=100, null=True, index=True),
            "status": lambda: CharField(max_length=1, null=True, default="1", index=True),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        UserTenant._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "user_id": lambda: CharField(max_length=36, null=False, index=True),
            "tenant_id": lambda: CharField(max_length=36, null=False, index=True),
            "role": lambda: CharField(max_length=36, null=False, index=True),
            "invited_by": lambda: CharField(max_length=36, null=False, index=True),
            "status": lambda: CharField(max_length=1, null=True, default="1", index=True),
            "create_date": lambda: DateTimeField(default=datetime.utcnow),
            "update_date": lambda: DateTimeField(default=datetime.utcnow),
            "create_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
            "update_time": lambda: BigIntegerField(default=lambda: int(current_timestamp())),
        },
        LegalTopic._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "topic_id": lambda: TextField(null=True, index=True),
            "topic_number": lambda: BigIntegerField(null=True, index=True),
            "topic_title_vi": lambda: TextField(null=True),
            "topic_title_en": lambda: TextField(null=True),
            "topic_note": lambda: TextField(null=True),
            "article_count": lambda: BigIntegerField(null=True),
            "demuc_count": lambda: BigIntegerField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalSubject._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "subject_id": lambda: TextField(null=False, index=True),
            "topic_id": lambda: TextField(null=True, index=True),
            "topic_number": lambda: BigIntegerField(null=True, index=True),
            "topic_title": lambda: TextField(null=True),
            "subject_number": lambda: BigIntegerField(null=True, index=True),
            "subject_title": lambda: TextField(null=True),
            "source_url": lambda: TextField(null=True),
            "file_version": lambda: TextField(null=True),
            "fetch_status": lambda: TextField(null=True, index=True),
            "fetch_error": lambda: TextField(null=True),
            "scraped_at": lambda: TextField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalTreeNode._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "node_id": lambda: TextField(null=False, index=True),
            "parent_id": lambda: TextField(null=True, index=True),
            "kind": lambda: TextField(null=True, index=True),
            "number": lambda: BigIntegerField(null=True, index=True),
            "title": lambda: TextField(null=True),
            "raw_text": lambda: TextField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalArticle._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "subject_id": lambda: TextField(null=False, index=True),
            "topic_id": lambda: TextField(null=True, index=True),
            "topic_number": lambda: BigIntegerField(null=True, index=True),
            "topic_title": lambda: TextField(null=True),
            "subject_number": lambda: BigIntegerField(null=True, index=True),
            "subject_title": lambda: TextField(null=True),
            "article_anchor": lambda: TextField(null=True, index=True),
            "article_title": lambda: TextField(null=True),
            "chapter_title": lambda: TextField(null=True),
            "source_note_text": lambda: TextField(null=True),
            "source_links": lambda: JSONField(null=True),
            "related_note_text": lambda: TextField(null=True),
            "content_text": lambda: TextField(null=True),
            "content_char_len": lambda: BigIntegerField(null=True),
            "content_word_count": lambda: BigIntegerField(null=True),
            "source_url": lambda: TextField(null=True),
            "scraped_at": lambda: TextField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalOntologySubject._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "topic_id": lambda: TextField(null=True, index=True),
            "topic_number": lambda: BigIntegerField(null=True, index=True),
            "topic_title_vi": lambda: TextField(null=True),
            "topic_title_en": lambda: TextField(null=True),
            "subject_id": lambda: TextField(null=True, index=True),
            "subject_title_vi": lambda: TextField(null=True),
            "subject_title_en": lambda: TextField(null=True),
            "article_count": lambda: BigIntegerField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalGlossary._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "category": lambda: TextField(null=True, index=True),
            "vi": lambda: TextField(null=False, index=True),
            "en": lambda: TextField(null=True),
            "note": lambda: TextField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        LegalIngestionJob._meta.table_name: {
            "id": lambda: AutoField(primary_key=True),
            "dataset_name": lambda: TextField(null=True, index=True),
            "dataset_version": lambda: TextField(null=True),
            "status": lambda: TextField(null=True, index=True),
            "started_at": lambda: DateTimeField(null=True),
            "finished_at": lambda: DateTimeField(null=True),
            "total_rows": lambda: IntegerField(null=True),
            "success_rows": lambda: IntegerField(null=True),
            "failed_rows": lambda: IntegerField(null=True),
            "error_message": lambda: TextField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        ChatSession._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "user_id": lambda: CharField(max_length=36, null=False, index=True),
            "title": lambda: TextField(null=True),
            "metadata": lambda: JSONField(default=dict),
            "status": lambda: CharField(max_length=64, null=True, index=True),
            "deleted_at": lambda: DateTimeField(null=True),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
            "updated_at": lambda: DateTimeField(default=datetime.utcnow),
        },
        ChatMessage._meta.table_name: {
            "id": lambda: CharField(max_length=36, primary_key=True),
            "session_id": lambda: CharField(max_length=36, null=False, index=True),
            "user_id": lambda: CharField(max_length=36, null=True, index=True),
            "role": lambda: CharField(max_length=16, null=False),
            "content": lambda: TextField(null=False),
            "references": lambda: JSONField(default=list),
            "created_at": lambda: DateTimeField(default=datetime.utcnow),
        },
    }

    ops = []
    for table_name, columns in tables_columns.items():
        for column_name, field_factory in columns.items():
            if not _column_exists(table_name, column_name):
                ops.append(
                    migrator.add_column(
                        table_name,
                        column_name,
                        field_factory(),
                    )
                )
    return ops


def run_migration() -> None:
    connection_opened_here = False
    if db.is_closed():
        db.connect()
        connection_opened_here = True

    try:
        db.create_tables(
            [
                Users,
                Knowledgebase,
                Document,
                File,
                Tenant,
                UserTenant,
                *CHAT_MODELS,
                *LEGAL_MODELS,
            ],
            safe=True,
        )
        _migrate_users_id_to_charfield()
        _ensure_chat_messages_constraints()
        migration_ops = _build_migration_ops(PostgresqlMigrator(db))
        if migration_ops:
            migrate(*migration_ops)
    finally:
        if connection_opened_here and not db.is_closed():
            db.close()
