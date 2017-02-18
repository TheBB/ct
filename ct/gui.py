from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QButtonGroup, QLabel, QFrame, QScrollArea
)

from PyQt5.QtCore import Qt, QSize, QTimer

from ct.db import puzzles, Discipline
from ct import default_puzzle

from enum import Enum, auto
from os.path import abspath, dirname, join
import sys


class DisciplineChoiceWidget(QWidget):

    def __init__(self, main):
        super(DisciplineChoiceWidget, self).__init__()
        self.main = main
        self.blind = False
        self.one_handed = False
        self.feet = False
        self.setMaximumWidth(70)
        self.setLayout(QVBoxLayout())

        group = QButtonGroup(self)
        group.setExclusive(True)

        ICON_PATH = join(dirname(abspath(__file__)), 'data')
        for pid, p in puzzles.items():
            btn = QPushButton()
            pixmap = QPixmap(join(ICON_PATH, pid) + '.png')
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(pixmap.rect().size())
            btn.setCheckable(True)
            if 'default' in p and p['default']:
                btn.setChecked(True)
                self.puzzle = pid
            btn.pressed.connect(lambda q=pid: self.set_puzzle(q))
            group.addButton(btn)
            self.layout().addWidget(btn)

        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        frame.setFrameShadow(QFrame.Sunken)
        self.layout().addWidget(frame)

        btn = QPushButton('BLD')
        btn.setCheckable(True)
        btn.pressed.connect(self.set_bld)
        self.layout().addWidget(btn)

        btn = QPushButton('OH')
        btn.setCheckable(True)
        btn.pressed.connect(self.set_one_handed)
        self.layout().addWidget(btn)

        btn = QPushButton('FEET')
        btn.setCheckable(True)
        btn.pressed.connect(self.set_feet)
        self.layout().addWidget(btn)

        self.layout().addStretch()

        self.make_discipline()

    def make_discipline(self):
        self.main.set_discipline(Discipline(
            self.puzzle, self.blind, self.one_handed, self.feet
        ))

    def set_puzzle(self, puzzle):
        self.puzzle = puzzle
        self.make_discipline()

    def set_bld(self):
        self.blind = not self.blind
        self.make_discipline()

    def set_one_handed(self):
        self.one_handed = not self.one_handed
        self.make_discipline()

    def set_feet(self):
        self.feet = not self.feet
        self.make_discipline()


class ResultWidget(QWidget):

    def __init__(self, parent):
        super(ResultWidget, sefl).__init__(parent)


class ResultsList(QScrollArea):

    def __init__(self):
        super(ResultsList, self).__init__()
        self.setMaximumWidth(200)

        central = QWidget()
        self.setWidget(central)
        self.setWidgetResizable(True)

        self.layout = QVBoxLayout(central)
        self.layout.addStretch()

    def new_solve(self, solve):
        self.layout.insertWidget(0, QPushButton(solve.discipline.name + ' ' + str(solve.duration)))


class TimerWidget(QWidget):

    class State(Enum):
        waiting = auto()
        solving = auto()

    _state = State.waiting

    def __init__(self, master):
        super(TimerWidget, self).__init__()
        self.master = master
        self.setLayout(QVBoxLayout())

        self.layout().addStretch()

        puzzle = QLabel()
        puzzle.setStyleSheet('QLabel { font-size: 20pt; font-weight: bold; }')
        puzzle.setAlignment(Qt.AlignCenter)
        self.layout().addWidget(puzzle)

        time = QLabel()
        time.setStyleSheet('QLabel { font-size: 75pt; font-weight: bold; }')
        time.setAlignment(Qt.AlignCenter)
        time.setMinimumHeight(200)
        self.layout().addWidget(time)

        scramble = QLabel()
        scramble.setStyleSheet('QLabel { font-size: 25pt; font-weight: bold; padding: 0em 3em 0em 3em; }')
        scramble.setAlignment(Qt.AlignCenter)
        scramble.setWordWrap(True)
        self.layout().addWidget(scramble)

        self.layout().addStretch()

        self.puzzle= puzzle
        self.scramble = scramble
        self.time = time
        self.clock = None

        self.update_timer()

    @property
    def discipline(self):
        return self._discipline

    @discipline.setter
    def discipline(self, discipline):
        self._discipline = discipline
        self.puzzle.setText(discipline.name)
        self.clock = None
        self.update_timer()
        self.new_scramble()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    def new_scramble(self):
        self.scramble.setText(self.discipline.scramble())

    def start_solving(self):
        self.state = TimerWidget.State.solving
        self.clock = 0
        self.update_timer()

        timer = QTimer()
        timer.timeout.connect(lambda: self.solution_timeout(timer))
        timer.start(10)

    def solution_timeout(self, timer):
        if self.state != TimerWidget.State.solving:
            timer.stop()
            return

        self.clock += 10
        self.update_timer()

    def abort_solve(self):
        self.state = TimerWidget.State.waiting
        self.clock = None
        self.new_scramble()
        self.update_timer()

    def finish_solve(self):
        self.state = TimerWidget.State.waiting
        solve = self.discipline.append(duration=self.clock, scramble=self.scramble.text())
        self.master.new_solve(solve)
        self.new_scramble()

    def update_timer(self):
        if self.clock is None:
            self.time.setText('--:--.--')

        else:
            sec, msec = divmod(self.clock, 1000)
            mins, sec = divmod(sec, 60)
            csec = msec // 10
            if mins > 0:
                self.time.setText(f'{mins}:{sec:02}.{csec:02}')
            else:
                self.time.setText(f'{sec}.{csec:02}')

    def trigger(self):
        if self.state == TimerWidget.State.waiting:
            self.start_solving()
        elif self.state == TimerWidget.State.solving:
            self.finish_solve()


class MasterWidget(QWidget):

    def __init__(self):
        super(MasterWidget, self).__init__()

        self.setLayout(QHBoxLayout())

        self.timer = TimerWidget(self)
        self.choice = DisciplineChoiceWidget(self)
        self.results = ResultsList()

        self.layout().addWidget(self.choice)
        self.layout().addWidget(self.timer)
        self.layout().addWidget(self.results)

        self.grabKeyboard()

    def new_solve(self, solve):
        self.results.new_solve(solve)

    def set_discipline(self, discipline):
        self.timer.discipline = discipline

    def keyPressEvent(self, event):
        if event.text() == ' ':
            self.timer.trigger()
            self.choice.setEnabled(self.timer.state == TimerWidget.State.waiting)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Cube Timer')

        self.setCentralWidget(MasterWidget())


def run_gui():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.showMaximized()
    return app.exec_()
