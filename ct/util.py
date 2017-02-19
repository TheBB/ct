from math import isnan


def format_time(time):
    if isnan(time):
        return '--:--.--'
    sec, msec = divmod(int(time), 1000)
    mins, sec = divmod(sec, 60)
    csec = msec // 10
    if mins > 0:
        return f'{mins}:{sec:02}.{csec:02}'
    return f'{sec}.{csec:02}'
