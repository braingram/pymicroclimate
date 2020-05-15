import datetime

import serial

from . import config
from . import logger


class MockSerial:
    def __init__(self, *args, **kwargs):
        self.line = None
        pass

    def readline(self):
        l = self.line
        if l is None:
            l = b"\n"
        self.line = None
        return l


def build_line(**kwargs):
    s = ''
    for (k, t) in logger.line_tokens:
        v = t(kwargs.get(k, 0.))
        if len(s):
            s += ',%s' % v
        else:
            s = str(v)
    return s


def get_all(db):
    cur = db.cursor()
    cur.execute("select * from weather")
    return cur.fetchall()


def test_config():
    pass


def test_reading():
    r = logger.Reading()
    ts = datetime.datetime.fromtimestamp(5E8)
    r.from_line(build_line(), ts)
    for k in r.data:
        if k == 'Timestamp':
            assert r.data[k] == ts.timestamp()
        else:
            assert r.data[k] == 0
    for (k, t) in logger.line_tokens:
        if t == int:
            v = 1
        elif t == float:
            v = 1.5
        else:
            assert False
        r.from_line(build_line(**{k: v}), ts)
        for dk in r.data:
            if dk == 'Timestamp':
                continue
            if dk == k:
                assert r.data[dk] == v
            else:
                assert r.data[dk] == 0


def test_logger():
    original = serial.Serial
    serial.Serial = MockSerial
    l = logger.Logger({
        'data_dir': ':memory:',
        'split_days': True,
    })

    line = build_line(Rain=1.5)
    ts = datetime.datetime.fromtimestamp(5E8)

    # add first reading
    l.parse_line(line, ts)
    assert l.db is not None
    assert len(get_all(l.db)) == 1

    # check comment lines are ignored
    l.parse_line("#", ts)
    assert len(get_all(l.db)) == 1
    l.parse_line("#" + line, ts)
    assert len(get_all(l.db)) == 1

    # check mal-formed lines throw error
    try:
        l.parse_line("0,1", ts)
        assert False
    except logger.ReadingError:
        assert True
    assert len(get_all(l.db)) == 1

    # add 2nd reading
    ts2 = ts + datetime.timedelta(seconds=1)
    l.parse_line(line, ts2)
    assert len(get_all(l.db)) == 2

    # test split
    ts3 = ts + datetime.timedelta(days=1)
    l.parse_line(line, ts3)
    assert len(get_all(l.db)) == 1

    # test parsing from fake serial input
    l = logger.Logger({
        'data_dir': ':memory:',
        'split_days': True,
    })
    l.conn.line = line.encode('ascii')
    l.read_serial_line()
    assert len(get_all(l.db)) == 1

    # TODO save to temp files to test split by hour

def run():
    test_config()
    test_reading()
    test_logger()
