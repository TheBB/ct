from PyQt5.QtCore import QTimer
from enum import Enum, auto

from ct.db import Discipline


class State(Enum):
    waiting = auto()
    solving = auto()


class EventHandler:

    def __init__(self):
        self.handlers = []

    def register(self, handler):
        self.handlers.append(handler)

    def __call__(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)

discipline_changed = EventHandler()
scramble_changed = EventHandler()
clock_changed = EventHandler()
state_changed = EventHandler()
new_solve = EventHandler()

state = State.waiting
clock = None

discipline = Discipline('3')
scramble = discipline.scramble()


def set_discipline(_discipline):
    assert state == State.waiting
    global discipline, clock, scramble
    discipline = _discipline
    scramble = discipline.scramble()
    clock = None
    discipline_changed()
    scramble_changed()
    clock_changed()


def _start_solving():
    global state, clock
    state = State.solving
    state_changed()
    clock = 0
    clock_changed()

    timer = QTimer()
    timer.timeout.connect(lambda: _solving_timeout(timer))
    timer.start(10)


def _solving_timeout(timer):
    global state, clock
    if state != State.solving:
        timer.stop()
        return
    clock += 10
    clock_changed()


def _finish_solving():
    global state, scramble
    state = State.waiting
    state_changed()
    solve, records = discipline.append(clock, scramble=scramble)
    scramble = discipline.scramble()
    scramble_changed()
    new_solve(solve, records)


def escape():
    global state, clock, scramble
    if state == State.solving:
        state = State.waiting
        state_changed()
        clock = None
        clock_changed()
        scramble = discipline.scramble()
        scramble_changed()


def trigger():
    if state == State.waiting:
        _start_solving()
    elif state == State.solving:
        _finish_solving()
