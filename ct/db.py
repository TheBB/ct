from collections import namedtuple
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, DateTime, String, Boolean, Float, text as _text, bindparam
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from xdg import BaseDirectory
from math import isnan

import numpy as np
import pandas as pd

from ct.scramble import CubeScrambler
from ct.util import format_time
from ct.stats import default_stats


DATA_PATH = BaseDirectory.save_data_path('ct')
engine = create_engine(f'sqlite:///{DATA_PATH}/db.sqlite3')
Base = declarative_base()

Session = sessionmaker(bind=engine)
Session.configure(bind=engine)
session = Session()


puzzles = {
    '2': {
        'name': '2×2×2',
        'inspection': 15,
        'scrambler': CubeScrambler(2, 25),
    },
    '3': {
        'default': True,
        'name': '3×3×3',
        'inspection': 15,
        'scrambler': CubeScrambler(3, 25),
    },
    '4': {
        'name': '4×4×4',
        'inspection': 15,
        'scrambler': CubeScrambler(4, 40),
    },
    '5': {
        'name': '5×5×5',
        'inspection': 15,
        'scrambler': CubeScrambler(5, 60),
    },
}


def text(s):
    sql = _text(s)

    if 'puzzle' in sql._bindparams:
        sql = sql.bindparams(bindparam('puzzle', String))
    for param in set(sql._bindparams) & {'blind', 'one_handed', 'feet'}:
        sql = sql.bindparams(bindparam(param, Boolean))

    return sql


Record = namedtuple('Record', ['name', 'when', 'duration'])


class Discipline:

    def __init__(self, puzzle, blind=False, one_handed=False, feet=False):
        self.puzzle_name = puzzle
        self.puzzle = puzzles[puzzle]
        self.blind = blind
        self.one_handed = one_handed
        self.feet = feet
        self._records = []

    @property
    def inspection(self):
        if self.blind:
            return 0
        return self.puzzle['inspection']

    @property
    def name(self):
        args = [self.puzzle['name']]
        if self.blind:
            args.append('BLD')
        if self.one_handed:
            args.append('OH')
        if self.feet:
            args.append('FEET')
        return ' '.join(args)

    @property
    def stats_computer(self):
        return default_stats

    def scramble(self):
        self.last_scramble = self.puzzle['scrambler'].scramble()
        return self.last_scramble

    def append(self, duration, time=None, remarks=None, scramble=None):
        if time is None:
            time = datetime.utcnow()
        if scramble is None and hasattr(self, 'last_scramble'):
            scramble = self.last_scramble

        records = list(self.records())

        solve = Solve(
            time=time,
            duration=duration,
            puzzle=self.puzzle_name,
            blind=self.blind,
            one_handed=self.one_handed,
            feet=self.feet,
            remarks=remarks,
            scramble=scramble
        )
        session.add(solve)
        session.commit()

        new_records = []
        self._records = []
        for rec, cur in zip(records, self.current()):
            if cur.duration < rec.duration:
                rec = cur
                new_records.append(cur)
            self._records.append(rec)

        return solve, new_records

    def solve_fits(self, solve):
        return all([
            self.puzzle_name == solve.puzzle,
            self.blind == solve.blind,
            self.one_handed == solve.one_handed,
            self.feet == solve.feet,
        ])

    def save(self, solve):
        assert self.solve_fits(solve)
        self._records = []
        session.commit()

    def delete(self, solve):
        assert self.solve_fits(solve)
        self._records = []
        session.delete(solve)
        session.commit()

    def bindings(self):
        return {
            'puzzle': self.puzzle_name,
            'blind': self.blind,
            'one_handed': self.one_handed,
            'feet': self.feet,
        }

    def historical(self):
        computer = self.stats_computer
        data = self.data()
        return computer.compute(data)

    def records(self, recompute=False):
        if recompute or not self._records:
            data = self.historical()
            self._records = []
            for k in data.columns:
                when = data[k].argmin()
                if isinstance(when, float) and isnan(when):
                    when = None
                self._records.append(Record(k, when, data[k].min()))
        yield from self._records

    def current(self):
        computer = self.stats_computer
        data = self.data(take=computer.minimum, recent=True)
        data = computer.compute(data)
        for k in data.columns:
            yield Record(k, data.index[-1], data[k][-1])

    def data(self, take=None, recent=False):
        query = f"""
        SELECT
            time,
            CASE WHEN dnf = 1 THEN NULL ELSE duration END AS duration
        FROM solves
        WHERE
            puzzle = :puzzle AND
            blind = :blind AND
            one_handed = :one_handed AND
            feet = :feet
        ORDER BY time {'DESC' if recent else 'ASC'}
        """

        if take:
            query = f'{query}\n LIMIT :total'
        if recent:
            query = f'SELECT * FROM ({query}) ORDER BY time ASC'

        query = text(query)
        query = query.columns(time=DateTime, duration=Integer)

        bindings = self.bindings()
        if take:
            bindings['total'] = take

        data = [(np.datetime64(row[0], 's'), row[1])
                for row in engine.execute(query, bindings)]
        data = np.array(data, dtype=[('time', 'datetime64[s]'), ('duration', '>f4')])
        return pd.Series(data=data['duration'], index=data['time'])

    def __repr__(self):
        return self.name


class Solve(Base):
    __tablename__ = 'solves'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    puzzle = Column(String, nullable=False)
    blind = Column(Boolean, nullable=False, default=False)
    one_handed = Column(Boolean, nullable=False, default=False)
    feet = Column(Boolean, nullable=False, default=False)
    plus_two = Column(Boolean, nullable=False, default=False)
    dnf = Column(Boolean, nullable=False, default=False)
    remarks = Column(String)
    scramble = Column(String)

    @property
    def discipline(self):
        return Discipline(self.puzzle, self.blind, self.one_handed, self.feet)

    @property
    def formatted_duration(self):
        base = format_time(self.duration)
        if self.plus_two:
            base = f'{base} (+2)'
        if self.dnf:
            base = f'<s>{base}</s>'
        return base


Base.metadata.create_all(engine)
