import datetime
import logging
import os
import sqlite3

import numpy
import serial

from . import config


line_tokens = [
    ('Time', int),
    ('Light', float),
    ('WindDir', float),
    ('WindSpd', float),
    ('Rain', float),
    ('WBTemp', float),
    ('WBPres', float),
    ('WBHum', float),
    ('ExtTemp', float),
    ('SampleIndex', int)
]
row_dtype = [('Timestamp', int), ] + line_tokens


def create_table(db):
    cur = db.cursor()
    with db:
        cur.execute("""
        create table if not exists weather(
            Timestamp integer,
            Time integer,
            Light float,
            WindDir float,
            WindSpd float,
            Rain float,
            WBTemp float,
            WBPres float,
            WBHum float,
            ExtTemp float,
            SampleIndex integer)
        """)


class ReadingError(Exception):
    pass


class Reading:
    def __init__(self, data=None):
        if data is None:
            data = {}
        self.data = data
    
    def from_line(self, line, timestamp):
        tks = line.strip().split(',')
        if len(tks) != len(line_tokens):
            raise ReadingError(
                "Invalid number of tokens on line[%s]" % len(tks))
        self.data['Timestamp'] = int(timestamp.timestamp())
        for (v, tk) in zip(tks, line_tokens):
            n, t = tk
            self.data[n] = t(v)

    def to_db(self, db):
        cur = db.cursor()
        with db:
            vs = [self.data['Timestamp'], ]
            vs += [self.data[k] for k, _ in line_tokens]
            cur.execute("""
            insert into weather values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, vs)

    def __repr__(self):
        return "Reading(%s)" % (self.data, )


class Logger:
    def __init__(self, cfg=None):
        self.cfg = config.load_config(cfg)
        self.conn = serial.Serial(self.cfg['port'], 115200)
        self.db = None
        self.db_ts = None

    def split(self, ts):
        # new db file
        ddir = os.path.expanduser(self.cfg['data_dir'])
        if ddir == ':memory:':
            fn = ddir
        else:
            if not os.path.exists(ddir):
                os.makedirs(ddir)
            fn = os.path.join(ddir, ts.strftime('%y%m%d') + '.sqlite')
        self.db = sqlite3.connect(fn)
        self.db_ts = ts
        create_table(self.db)

    def check_for_split(self, ts):
        if self.db is None:
            return self.split(ts)
        if not self.cfg.get('split_days', False):
            return
        dbts = self.db_ts
        if (
                dbts.year != ts.year or
                dbts.month != ts.month or
                dbts.day != ts.day):
            return self.split(ts)

    def log_line(self, line, ts):
        if not len(line):
            return
        if line[0] == '#':
            return
        self.check_for_split(ts)
        r = Reading()
        r.from_line(line, ts)
        r.to_db(self.db)
        logging.debug("Wrote %s to database", r)

    def parse_line(self, line, ts=None):
        if ts is None:
            ts = datetime.datetime.now()
        self.log_line(line, ts)

    def read_serial_line(self):
        try:
            self.parse_line(self.conn.readline().decode('ascii').strip())
        except ReadingError as e:
            print("Invalid line: %s" % e)


def load_file(fn, as_array=True):
    with sqlite3.connect(fn) as db:
        cur = db.cursor()
        cur.execute('select * from weather')
        vs = cur.fetchall()
        if not as_array:
            return vs
        return numpy.array(vs, dtype=row_dtype)


def run_cmdline():
    cfg = config.from_cmdline()
    logger = Logger(cfg)
    print("Logging %s to %s, Ctrl-C to quit" % (cfg['port'], cfg['data_dir']))
    while True:
        try:
            logger.read_serial_line()
        except KeyboardInterrupt as e:
            print("Quitting...")
            break
    del logger
