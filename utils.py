import time


def get_time_str(seconds: float) -> str:
    return time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(seconds))
