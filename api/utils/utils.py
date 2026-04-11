from datetime import datetime
import uuid

def current_timestamp():
    return datetime.now().timestamp()

def datetime_format(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

def get_uuid():
    ### bo qua cac ky tu dac biet de thanh 32 ki tu alpha numeric
    return str(uuid.uuid4()).replace("-", "")