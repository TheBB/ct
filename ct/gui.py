import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QButtonGroup, QLabel, QFrame, QScrollArea, QMenu, QDialog, QSplitter, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent

from ct.db import puzzles, Discipline
from ct.util import format_time
from ct import default_puzzle
import ct.stats as stats

from math import isnan
from enum import Enum, auto
from os.path import abspath, dirname, join
import sys


class ChartWidget(FigureCanvas):

    def __init__(self, data, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        axes = fig.add_subplot(111)

        index = data['Single'].index
        xs = list(range(len(index)))
        axes.scatter(xs, data['Single'] / 1000, alpha=0.3, edgecolor='none', color='black', label='Single')
        data = data.drop('Single', 'columns')

        plot_kwargs = [
            {
                'color': '#0099ff',
                'linestyle': 'dashed',
                'linewidth': 2,
            },
            {
                'color': '#3333ff',
                'linestyle': 'solid',
                'linewidth': 2,
            },
            {
                'color': '#ff0000',
                'linestyle': 'solid',
                'linewidth': 2,
            }
        ]
        for kwargs, (k, v) in zip(plot_kwargs, data.items()):
            axes.plot(xs, v / 1000, label=k, **kwargs)

        axes.set_xlim(xs[0], xs[-1])
        axes.legend()

        xticks = [i for i in axes.get_xticks() if int(i) < len(index)]
        xlabels = [index[int(i)].strftime('%Y-%m-%d') for i in xticks]
        axes.set_xticks(xticks)
        axes.set_xticklabels(xlabels)

        ylabels = [format_time(t * 1000) for t in axes.get_yticks()]
        axes.set_yticklabels(ylabels)

        axes.grid()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(
            self, QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        FigureCanvas.updateGeometry(self)


class StatsWidget(QWidget):

    def __init__(self, records, current):
        super(StatsWidget, self).__init__()
        self.setMaximumWidth(500)

        self.setLayout(QGridLayout())
        self.layout().setHorizontalSpacing(30)

        for c, t in [(1, 'BEST'), (2, 'WHEN'), (3, 'LAST')]:
            label = QLabel(t)
            label.setStyleSheet('QLabel { font-size: 15pt; font-weight: bold; }')
            self.layout().addWidget(label, 0, c)

        frame = QFrame()
        frame.setFrameShape(QFrame.HLine)
        frame.setFrameShadow(QFrame.Sunken)
        self.layout().addWidget(frame, 1, 0, 1, 4)

        self.next_row = 2
        for (name, when, record), (_, latest) in zip(records, current):
            if when:
                when = when.strftime('%Y-%m-%d')
            else:
                when = '--'
            self.add_row(name.upper(), format_time(record), when, format_time(latest))

        self.layout().setRowStretch(self.next_row, 1000)

    def add_row(self, title, best, when, current):
        label = QLabel(title)
        label.setStyleSheet('QLabel { font-weight: bold; }')
        self.layout().addWidget(label, self.next_row, 0)

        label = QLabel(best)
        label.setAlignment(Qt.AlignRight)
        self.layout().addWidget(label, self.next_row, 1)

        label = QLabel(when)
        label.setAlignment(Qt.AlignRight)
        self.layout().addWidget(label, self.next_row, 2)

        label = QLabel(current)
        label.setAlignment(Qt.AlignRight)
        self.layout().addWidget(label, self.next_row, 3)

        self.next_row += 1


class HistoryDialog(QDialog):

    def __init__(self, discipline, parent=None):
        super(HistoryDialog, self).__init__(parent)
        self.setWindowTitle(f'History for {discipline.name}')
        self.showMaximized()

        self.setLayout(QHBoxLayout())
        self.layout().addWidget(StatsWidget(discipline.records(), discipline.current()))
        self.layout().addWidget(ChartWidget(discipline.historical(), parent=self))


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


class ResultWidget(QFrame):

    def __init__(self, master, solve):
        super(ResultWidget, self).__init__(master)
        self.master = master
        self.setFrameShape(QFrame.StyledPanel)
        self.solve = solve

        self.setLayout(QHBoxLayout())

        self.time = QLabel(solve.formatted_duration)
        self.layout().addWidget(self.time)

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        plus_two = menu.addAction('+2')
        plus_two.setCheckable(True)
        plus_two.setChecked(self.solve.plus_two)

        dnf = menu.addAction('DNF')
        dnf.setCheckable(True)
        dnf.setChecked(self.solve.dnf)

        delete = menu.addAction('Delete')

        selected = menu.exec_(self.mapToGlobal(event.pos()))
        if selected == plus_two:
            self.solve.plus_two = not self.solve.plus_two
            self.solve.save()
        elif selected == dnf:
            self.solve.dnf = not self.solve.dnf
            self.solve.save()
        elif selected == delete:
            self.solve.delete()
            self.master.layout.removeWidget(self)
            self.setParent(None)

        self.time.setText(self.solve.formatted_duration)


class ResultsList(QScrollArea):

    def __init__(self):
        super(ResultsList, self).__init__()
        self.setMaximumWidth(250)

        central = QWidget()
        self.setWidget(central)
        self.setWidgetResizable(True)

        self.layout = QVBoxLayout(central)
        self.layout.addStretch()

    def new_solve(self, solve):
        self.layout.insertWidget(0, ResultWidget(self, solve))


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
        solve = self.discipline.append(self.clock, scramble=self.scramble.text())
        self.master.new_solve(solve)
        self.new_scramble()

    def update_timer(self):
        if self.clock is None:
            self.time.setText('--:--.--')
        else:
            self.time.setText(format_time(self.clock))

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

    def new_solve(self, solve):
        self.results.new_solve(solve)

    def set_discipline(self, discipline):
        self.timer.discipline = discipline

    def trigger(self):
        self.timer.trigger()
        self.choice.setEnabled(self.timer.state == TimerWidget.State.waiting)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Cube Timer')

        self.master = MasterWidget()
        self.setCentralWidget(self.master)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.text() in [' ', 'q', 'h']:
            if event.text() == ' ':
                self.centralWidget().trigger()
            if event.text() == 'q':
                self.close()
            if event.text() == 'h':
                HistoryDialog(self.master.timer.discipline, self).exec_()
            return True
        return super(MainWindow, self).eventFilter(obj, event)


def run_gui():
    app = QApplication(sys.argv)
    win = MainWindow()
    app.installEventFilter(win)
    win.showMaximized()
    return app.exec_()
