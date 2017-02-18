from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, DateTime, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from xdg import BaseDirectory

from ct.scramble import CubeScrambler


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


class Discipline:

    def __init__(self, puzzle, blind, one_handed, feet):
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

    def append(self, time=None, duration=None, remarks=None, scramble=None):
        if time is None:
            time = datetime.utcnow()
        if scramble is None and hasattr(self, 'last_scramble'):
            scramble = self.last_scramble
        if duration is None and remarks is None:
            raise ValueError("Can't add DNF/DNS without remarks")

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


class Solve(Base):
    __tablename__ = 'solves'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, nullable=False)
    duration = Column(Integer)
    puzzle = Column(String, nullable=False)
    blind = Column(Boolean, nullable=False, default=False)
    one_handed = Column(Boolean, nullable=False, default=False)
    feet = Column(Boolean, nullable=False, default=False)
    remarks = Column(String)
    scramble = Column(String)

    @property
    def discipline(self):
        return Discipline(self.puzzle, self.blind, self.one_handed, self.feet)

    @property
    def formatted_duration(self):
        sec, msec = divmod(self.duration, 1000)
        mins, sec = divmod(sec, 60)
        csec = msec // 10
        if mins > 0:
            self.time.setText(f'{mins}:{sec:02}.{csec:02}')
        else:
            self.time.setText(f'{sec}.{csec:02}')


Base.metadata.create_all(engine)
