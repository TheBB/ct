from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, DateTime, String, Boolean, Float, text as _text, bindparam
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from xdg import BaseDirectory

import numpy as np
import pandas as pd

from ct.scramble import CubeScrambler
from ct.util import format_time


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


class Discipline:

    def __init__(self, puzzle, blind=False, one_handed=False, feet=False):
        self.puzzle_name = puzzle
        self.puzzle = puzzles[puzzle]
        self.blind = blind
        self.one_handed = one_handed
        self.feet = feet

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

    def scramble(self):
        self.last_scramble = self.puzzle['scrambler'].scramble()
        return self.last_scramble

    def append(self, duration, time=None, remarks=None, scramble=None):
        if time is None:
            time = datetime.utcnow()
        if scramble is None and hasattr(self, 'last_scramble'):
            scramble = self.last_scramble

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

        return solve

    def bindings(self):
        return {
            'puzzle': self.puzzle_name,
            'blind': self.blind,
            'one_handed': self.one_handed,
            'feet': self.feet,
        }

    def current_average(self, total, drop_btm, drop_top):
        query = text(sql.current_average)
        bindings = self.bindings()
        bindings.update({
            'total': total,
            'select': total - drop_btm - drop_top,
            'drop_top': drop_top,
        })
        for row in engine.execute(query, bindings):
            return row[0]
        return None

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
        data = np.array(data, dtype=[('time', 'datetime64[s]'), ('duration', '>i4')])
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

    def save(self):
        session.commit()

    def delete(self):
        session.delete(self)
        session.commit()


Base.metadata.create_all(engine)
