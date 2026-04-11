

import logging
import os
import ssl
import time
from datetime import timedelta
from pathlib import Path
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error, ServerError, InvalidResponseError
from io import BytesIO
import urllib3
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


MINIO_CONFIG = {
    "host": os.getenv("MINIO_HOST", ""),
    "port": os.getenv("MINIO_PORT", "") or None,
    "user": os.getenv("MINIO_USER", ""),
    "password": os.getenv("MINIO_PASSWORD", ""),
    "secure": _parse_bool(os.getenv("MINIO_SECURE"), False),
    "region": os.getenv("MINIO_REGION", "") or None,
    "verify": _parse_bool(os.getenv("MINIO_VERIFY"), True),
    "bucket": os.getenv("MINIO_BUCKET", "") or None,
    "prefix_path": os.getenv("MINIO_PREFIX_PATH", "") or None,
}


def _build_minio_endpoint():
    host = MINIO_CONFIG.get("host", "") or ""
    port = MINIO_CONFIG.get("port")
    # MinIO Python SDK accepts endpoint as "host:port".
    # If host already contains a port, keep it unchanged.
    if port and ":" not in host:
        return f"{host}:{port}"
    return host


def _build_minio_http_client():
    """
    Build an optional urllib3 HTTP client for MinIO when using SSL/TLS.
    Respects MINIO.verify (default True) to allow self-signed certificates
    when set to False.
    """
    verify = MINIO_CONFIG.get("verify", True)
    if verify:
        return None
    return urllib3.PoolManager(cert_reqs=ssl.CERT_NONE)



class LexCompanionMinio:
    def __init__(self):
        self.conn = None
        # Use `or None` to convert empty strings to None, ensuring single-bucket
        # mode is truly disabled when not configured
        self.bucket = MINIO_CONFIG.get("bucket", None)
        self.prefix_path = MINIO_CONFIG.get("prefix_path", None)
        self.__open__()

    @staticmethod
    def use_default_bucket(method):
        def wrapper(self, bucket, *args, **kwargs):
            # If there is a default bucket, use the default bucket
            # but preserve the original bucket identifier so it can be
            # used as a path prefix inside the physical/default bucket.
            original_bucket = bucket
            actual_bucket = self.bucket if self.bucket else bucket
            if self.bucket:
                # pass original identifier forward for use by other decorators
                kwargs['_orig_bucket'] = original_bucket
            return method(self, actual_bucket, *args, **kwargs)

        return wrapper

    @staticmethod
    def use_prefix_path(method):
        def wrapper(self, bucket, fnm, *args, **kwargs):
            # If a default MINIO bucket is configured, the use_default_bucket
            # decorator will have replaced the `bucket` arg with the physical
            # bucket name and forwarded the original identifier as `_orig_bucket`.
            # Prefer that original identifier when constructing the key path so
            # objects are stored under <physical-bucket>/<identifier>/...
            orig_bucket = kwargs.pop('_orig_bucket', None)

            if self.prefix_path:
                # If a prefix_path is configured, include it and then the identifier
                if orig_bucket:
                    fnm = f"{self.prefix_path}/{orig_bucket}/{fnm}"
                else:
                    fnm = f"{self.prefix_path}/{fnm}"
            else:
                # No prefix_path configured. If orig_bucket exists and the
                # physical bucket equals configured default, use orig_bucket as a path.
                if orig_bucket and bucket == self.bucket:
                    fnm = f"{orig_bucket}/{fnm}"

            return method(self, bucket, fnm, *args, **kwargs)

        return wrapper

    def __open__(self):
        try:
            if self.conn:
                self.__close__()
        except Exception:
            pass

        try:
            http_client = _build_minio_http_client()
            self.conn = Minio(
                _build_minio_endpoint(),
                access_key=MINIO_CONFIG["user"],
                secret_key=MINIO_CONFIG["password"],
                secure=MINIO_CONFIG["secure"],
                region=MINIO_CONFIG.get("region"),
                http_client=http_client,
            )
        except Exception:
            logging.exception(
                "Fail to connect %s " % _build_minio_endpoint())

    def __close__(self):
        del self.conn
        self.conn = None

    def health(self):
        """
        Check MinIO service availability.
        """
        try:
            if self.bucket:
                # Single-bucket mode:
                # 1) Ensure service is reachable.
                # 2) Ensure configured bucket exists (create if missing).
                buckets = self.conn.list_buckets()
                bucket_names = {b.name for b in buckets}
                if self.bucket not in bucket_names:
                    self.conn.make_bucket(self.bucket)
                    logging.info(f"Created missing MinIO bucket: {self.bucket}")

                try:
                    return self.conn.bucket_exists(self.bucket)
                except S3Error as e:
                    logging.warning(
                        f"bucket_exists failed for '{self.bucket}' with {e.code}: {e.message}. "
                        "Using list_buckets() result for health check."
                    )
                    return self.bucket in bucket_names or self.bucket in {b.name for b in self.conn.list_buckets()}
            else:
                # Multi-bucket mode: verify MinIO service connectivity
                self.conn.list_buckets()
                return True
        except (S3Error, ServerError, InvalidResponseError):
            return False
        except ValueError as e:
            logging.error(f"Invalid MinIO bucket configuration '{self.bucket}': {e}")
            return False
        except Exception as e:
            logging.warning(f"Unexpected error in MinIO health check: {e}")
            return False

    @use_default_bucket
    @use_prefix_path
    def put(self, bucket, fnm, binary, tenant_id=None):
        for _ in range(3):
            try:
                # Note: bucket must already exist - we don't have permission to create buckets
                if not self.bucket and not self.conn.bucket_exists(bucket):
                    self.conn.make_bucket(bucket)

                r = self.conn.put_object(bucket, fnm,
                                         BytesIO(binary),
                                         len(binary)
                                         )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)

    @use_default_bucket
    @use_prefix_path
    def rm(self, bucket, fnm, tenant_id=None):
        try:
            self.conn.remove_object(bucket, fnm)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    @use_default_bucket
    @use_prefix_path
    def get(self, bucket, filename, tenant_id=None):
        for _ in range(1):
            try:
                r = self.conn.get_object(bucket, filename)
                return r.read()
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                self.__open__()
                time.sleep(1)
        return

    @use_default_bucket
    @use_prefix_path
    def obj_exist(self, bucket, filename, tenant_id=None):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            if self.conn.stat_object(bucket, filename):
                return True
            else:
                return False
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got exception")
            return False

    @use_default_bucket
    def bucket_exists(self, bucket):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            else:
                return True
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"bucket_exist {bucket} got exception")
            return False

    @use_default_bucket
    @use_prefix_path
    def get_presigned_url(self, bucket, fnm, expires, tenant_id=None):
        # MinIO SDK expects expires as datetime.timedelta, not seconds (int).
        if isinstance(expires, (int, float)):
            expires = timedelta(seconds=int(expires))
        for _ in range(10):
            try:
                return self.conn.get_presigned_url("GET", bucket, fnm, expires)
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)
        return

    @use_default_bucket
    def remove_bucket(self, bucket, **kwargs):
        orig_bucket = kwargs.pop('_orig_bucket', None)
        try:
            if self.bucket:
                # Single bucket mode: remove objects with prefix
                prefix = ""
                if self.prefix_path:
                    prefix = f"{self.prefix_path}/"
                if orig_bucket:
                    prefix += f"{orig_bucket}/"

                # List objects with prefix
                objects_to_delete = self.conn.list_objects(bucket, prefix=prefix, recursive=True)
                for obj in objects_to_delete:
                    self.conn.remove_object(bucket, obj.object_name)
                # Do NOT remove the physical bucket
            else:
                if self.conn.bucket_exists(bucket):
                    objects_to_delete = self.conn.list_objects(bucket, recursive=True)
                    for obj in objects_to_delete:
                        self.conn.remove_object(bucket, obj.object_name)
                    self.conn.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")

    def _resolve_bucket_and_path(self, bucket, fnm):
        if self.bucket:
            if self.prefix_path:
                fnm = f"{self.prefix_path}/{bucket}/{fnm}"
            else:
                fnm = f"{bucket}/{fnm}"
            bucket = self.bucket
        elif self.prefix_path:
            fnm = f"{self.prefix_path}/{fnm}"
        return bucket, fnm

    def copy(self, src_bucket, src_path, dest_bucket, dest_path):
        try:
            src_bucket, src_path = self._resolve_bucket_and_path(src_bucket, src_path)
            dest_bucket, dest_path = self._resolve_bucket_and_path(dest_bucket, dest_path)

            if not self.conn.bucket_exists(dest_bucket):
                self.conn.make_bucket(dest_bucket)

            try:
                self.conn.stat_object(src_bucket, src_path)
            except Exception as e:
                logging.exception(f"Source object not found: {src_bucket}/{src_path}, {e}")
                return False

            self.conn.copy_object(
                dest_bucket,
                dest_path,
                CopySource(src_bucket, src_path),
            )
            return True

        except Exception:
            logging.exception(f"Fail to copy {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}")
            return False

    def move(self, src_bucket, src_path, dest_bucket, dest_path):
        try:
            if self.copy(src_bucket, src_path, dest_bucket, dest_path):
                self.rm(src_bucket, src_path)
                return True
            else:
                logging.error(f"Copy failed, move aborted: {src_bucket}/{src_path}")
                return False
        except Exception:
            logging.exception(f"Fail to move {src_bucket}/{src_path} -> {dest_bucket}/{dest_path}")
            return False