import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from peewee import (
    BigIntegerField,
    BooleanField,
    DateTimeField,
    FixedCharField,
    Model,
    PostgresqlDatabase,
    TextField,CharField,IntegerField,FloatField
)
from playhouse.migrate import PostgresqlMigrator, migrate

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
    id = FixedCharField(max_length=36, primary_key=True)
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
    location = CharField(max_length=255, null=True, help_text="where dose it store example : minio ", index=True)
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


def _build_migration_ops(migrator: PostgresqlMigrator):
    tables_columns = {
        Users._meta.table_name: {
            "id": lambda: FixedCharField(max_length=36, primary_key=True),
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
            "location": lambda: CharField(max_length=255, null=True, index=True),
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
        db.create_tables([Users, Knowledgebase, Document, File, Tenant, UserTenant], safe=True)
        migration_ops = _build_migration_ops(PostgresqlMigrator(db))
        if migration_ops:
            migrate(*migration_ops)
    finally:
        if connection_opened_here and not db.is_closed():
            db.close()
