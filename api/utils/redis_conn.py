"""Redis/Valkey client and a Redis Streams task queue (XADD / XREADGROUP).

Producers push with ``queue_product``; workers use ``queue_consumer`` and ``RedisMsg.ack()``.
The old Lua token-bucket script was never invoked — removed. The delete-if-equal Lua only
supported a custom lock; ``valkey.lock.Lock`` already releases safely without that script.
"""

import asyncio
import json
import logging
import uuid

import valkey as redis
from valkey.lock import Lock

import os
from pathlib import Path


#### load cac cau hinh redis tu .env 
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

REDIS = {
    "host": os.getenv("REDIS_HOST", ""),
    "port": os.getenv("REDIS_PORT", ""),
    "password": os.getenv("REDIS_PASSWORD", ""),
    "db": os.getenv("REDIS_DB", ""),
}



class RedisMsg:
    """One message from a stream (consumer group); call ``ack()`` after successful processing."""

    def __init__(self, consumer, queue_name, group_name, msg_id, message):
        self.__consumer = consumer
        self.__queue_name = queue_name
        self.__group_name = group_name
        self.__msg_id = msg_id
        self.__message = json.loads(message["message"])

    def ack(self):
        try:
            self.__consumer.xack(self.__queue_name, self.__group_name, self.__msg_id)
            return True
        except Exception as e:
            logging.warning("[EXCEPTION]ack" + str(self.__queue_name) + "||" + str(e))
        return False

    def get_message(self):
        return self.__message

    def get_msg_id(self):
        return self.__msg_id



class RedisDB:
    def __init__(self):
        self.REDIS = None
        self.config = REDIS
        self.__open__()

    def __open__(self):
        try:
            host_raw = (self.config.get("host") or "127.0.0.1").strip()
            if ":" in host_raw:
                host, port_str = host_raw.split(":", 1)
                port = int(port_str)
            else:
                host = host_raw
                port_s = self.config.get("port")
                port = int(port_s) if port_s not in (None, "") else 6379
            db_s = self.config.get("db", 1)
            db = int(db_s) if db_s not in (None, "") else 1
            conn_params = {
                "host": host,
                "port": port,
                "db": db,
                "decode_responses": True,
            }
            username = self.config.get("username")
            if username:
                conn_params["username"] = username
            password = self.config.get("password")
            if password:
                conn_params["password"] = password

            self.REDIS = redis.StrictRedis(**conn_params)
        except Exception as e:
            logging.warning(f"Redis can't be connected. Error: {str(e)}")
        return self.REDIS

    def health(self):
        if not self.REDIS:
            return False
        self.REDIS.ping()
        a, b = "xx", "yy"
        self.REDIS.set(a, b, 3)
        return self.REDIS.get(a) == b

    def info(self):
        info = self.REDIS.info()
        return {
            "redis_version": info["redis_version"],
            "server_mode": info["server_mode"] if "server_mode" in info else info.get("redis_mode", ""),
            "used_memory": info["used_memory_human"],
            "total_system_memory": info["total_system_memory_human"],
            "mem_fragmentation_ratio": info["mem_fragmentation_ratio"],
            "connected_clients": info["connected_clients"],
            "blocked_clients": info["blocked_clients"],
            "instantaneous_ops_per_sec": info["instantaneous_ops_per_sec"],
            "total_commands_processed": info["total_commands_processed"],
        }

    def is_alive(self):
        return self.REDIS is not None

    def exist(self, k):
        if not self.REDIS:
            return None
        try:
            return self.REDIS.exists(k)
        except Exception as e:
            logging.warning("RedisDB.exist " + str(k) + " got exception: " + str(e))
            self.__open__()

    def get(self, k):
        if not self.REDIS:
            return None
        try:
            return self.REDIS.get(k)
        except Exception as e:
            logging.warning("RedisDB.get " + str(k) + " got exception: " + str(e))
            self.__open__()

    def set_obj(self, k, obj, exp=3600):
        try:
            self.REDIS.set(k, json.dumps(obj, ensure_ascii=False), exp)
            return True
        except Exception as e:
            logging.warning("RedisDB.set_obj " + str(k) + " got exception: " + str(e))
            self.__open__()
        return False

    def set(self, k, v, exp=3600):
        try:
            self.REDIS.set(k, v, exp)
            return True
        except Exception as e:
            logging.warning("RedisDB.set " + str(k) + " got exception: " + str(e))
            self.__open__()
        return False

    def delete(self, key) -> bool:
        try:
            self.REDIS.delete(key)
            return True
        except Exception as e:
            logging.warning("RedisDB.delete " + str(key) + " got exception: " + str(e))
            self.__open__()
        return False

    # --- Task queue (Redis Streams) ---

    def queue_product(self, queue, message) -> bool:
        for _ in range(3):
            try:
                payload = {"message": json.dumps(message)}
                self.REDIS.xadd(queue, payload)
                return True
            except Exception as e:
                logging.exception(
                    "RedisDB.queue_product " + str(queue) + " got exception: " + str(e)
                )
                self.__open__()
        return False

    def queue_consumer(self, queue_name, group_name, consumer_name, msg_id=b">") -> RedisMsg | None:
        """Read one message from the consumer group (short blocking read). See XREADGROUP docs."""
        for _ in range(3):
            try:
                try:
                    group_info = self.REDIS.xinfo_groups(queue_name)
                    if not any(gi["name"] == group_name for gi in group_info):
                        self.REDIS.xgroup_create(queue_name, group_name, id="0", mkstream=True)
                except redis.exceptions.ResponseError as e:
                    if "no such key" in str(e).lower():
                        self.REDIS.xgroup_create(queue_name, group_name, id="0", mkstream=True)
                    elif "busygroup" in str(e).lower():
                        logging.warning("Group already exists, continue.")
                    else:
                        raise

                args = {
                    "groupname": group_name,
                    "consumername": consumer_name,
                    "count": 1,
                    "block": 5000,
                    "streams": {queue_name: msg_id},
                }
                messages = self.REDIS.xreadgroup(**args)
                if not messages:
                    return None
                stream, element_list = messages[0]
                if not element_list:
                    return None
                mid, payload = element_list[0]
                return RedisMsg(self.REDIS, queue_name, group_name, mid, payload)
            except Exception as e:
                if str(e) == "no such key":
                    pass
                else:
                    logging.exception(
                        "RedisDB.queue_consumer "
                        + str(queue_name)
                        + " got exception: "
                        + str(e)
                    )
                    self.__open__()
        return None

    def get_unacked_iterator(self, queue_names: list[str], group_name, consumer_name):
        try:
            for queue_name in queue_names:
                try:
                    group_info = self.REDIS.xinfo_groups(queue_name)
                except Exception as e:
                    if str(e) == "no such key":
                        logging.warning(
                            f"RedisDB.get_unacked_iterator queue {queue_name} doesn't exist"
                        )
                        continue
                if not any(gi["name"] == group_name for gi in group_info):
                    logging.warning(
                        f"RedisDB.get_unacked_iterator queue {queue_name} group {group_name} doesn't exist"
                    )
                    continue
                current_min = 0
                while True:
                    payload = self.queue_consumer(
                        queue_name, group_name, consumer_name, current_min
                    )
                    if not payload:
                        break
                    current_min = payload.get_msg_id()
                    logging.info(
                        f"RedisDB.get_unacked_iterator {queue_name} {consumer_name} {current_min}"
                    )
                    yield payload
        except Exception:
            logging.exception(
                "RedisDB.get_unacked_iterator got exception: ",
            )
            self.__open__()

    def get_pending_msg(self, queue, group_name):
        try:
            return self.REDIS.xpending_range(queue, group_name, "-", "+", 10)
        except Exception as e:
            if "No such key" not in (str(e) or ""):
                logging.warning(
                    "RedisDB.get_pending_msg " + str(queue) + " got exception: " + str(e)
                )
        return []

    def requeue_msg(self, queue: str, group_name: str, msg_id: str):
        for _ in range(3):
            try:
                messages = self.REDIS.xrange(queue, msg_id, msg_id)
                if messages:
                    self.REDIS.xadd(queue, messages[0][1])
                    self.REDIS.xack(queue, group_name, msg_id)
            except Exception as e:
                logging.warning(
                    "RedisDB.requeue_msg " + str(queue) + " got exception: " + str(e)
                )
                self.__open__()

    def queue_info(self, queue, group_name) -> dict | None:
        for _ in range(3):
            try:
                groups = self.REDIS.xinfo_groups(queue)
                for group in groups:
                    if group["name"] == group_name:
                        return group
            except Exception as e:
                logging.warning(
                    "RedisDB.queue_info " + str(queue) + " got exception: " + str(e)
                )
                self.__open__()
        return None


REDIS_CONN = RedisDB()


class RedisDistributedLock:
    """Distributed lock; valkey's ``Lock`` uses its own Lua on release — no custom script."""

    def __init__(self, lock_key, lock_value=None, timeout=10, blocking_timeout=1):
        self.lock_key = lock_key
        self.lock_value = lock_value if lock_value else str(uuid.uuid4())
        self.timeout = timeout
        self.lock = Lock(
            REDIS_CONN.REDIS,
            lock_key,
            timeout=timeout,
            blocking_timeout=blocking_timeout,
        )

    def acquire(self):
        return self.lock.acquire(token=self.lock_value)

    async def spin_acquire(self):
        while True:
            if self.lock.acquire(token=self.lock_value):
                break
            await asyncio.sleep(10)

    def release(self):
        self.lock.release()
