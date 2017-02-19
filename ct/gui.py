import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QButtonGroup, QLabel, QFrame, QScrollArea, QMenu, QDialog, QGridLayout,
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QEvent

from ct.db import puzzles, Discipline
from ct.util import format_time
import ct.timing as timing

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
                'linestyle': 'solid',
                'linewidth': 2,
                'alpha': 0.6,
            },
            {
                'color': '#0000bb',
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

        super(ChartWidget, self).__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()


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
        for (name, when, record), (_, _, latest) in zip(records, current):
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

        timing.state_changed.register(self.state_changed)

    def state_changed(self):
        self.setEnabled(timing.state == timing.State.waiting)

    def make_discipline(self):
        timing.set_discipline(Discipline(
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
            if self.solve.plus_two:
                self.solve.duration += 2000
            else:
                self.solve.duration -= 2000
            timing.discipline.save(self.solve)
        elif selected == dnf:
            self.solve.dnf = not self.solve.dnf
            timing.discipline.save(self.solve)
        elif selected == delete:
            timing.discipline.delete(self.solve)
            self.master.remove_widget(self)

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

        self.widgets = []

        timing.new_solve.register(self.new_solve)
        timing.discipline_changed.register(self.discipline_changed)

    def new_solve(self, solve, records):
        self.widgets.append(ResultWidget(self, solve))
        self.layout.insertWidget(0, self.widgets[-1])

    def remove_widget(self, widget):
        self.layout.removeWidget(widget)
        widget.setParent(None)

    def discipline_changed(self):
        for w in self.widgets:
            self.remove_widget(w)
        self.widgets = []


class TimerWidget(QWidget):

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

        self.puzzle = puzzle
        self.scramble = scramble
        self.time = time

        for event in ['discipline_changed', 'scramble_changed', 'clock_changed']:
            getattr(self, event)()
            getattr(timing, event).register(getattr(self, event))

    def discipline_changed(self):
        self.puzzle.setText(timing.discipline.name)

    def scramble_changed(self):
        self.scramble.setText(timing.scramble)

    def clock_changed(self):
        self.time.setText(format_time(timing.clock))


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


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle('Cube Timer')
        self.setCentralWidget(MasterWidget())

        # timing.new_solve.register(self.new_solve)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.text() in [' ', 'q', 'h', 'c']:
            if event.text() == ' ':
                timing.trigger()
            if event.text() == 'c':
                timing.escape()
            if event.text() == 'q':
                self.close()
            if event.text() == 'h':
                HistoryDialog(timing.discipline, self).exec_()
            return True
        return super(MainWindow, self).eventFilter(obj, event)

    def new_solve(self, solve, records):
        if records:
            msgbox = QMessageBox()
            msgbox.setStyleSheet('QLabel { font-weight: bold; }')
            msgbox.setWindowTitle('New records set')
            msgbox.setIcon(QMessageBox.Information)
            text = []
            for r in records:
                text.append(f'<p>{r.name}: {format_time(r.duration)}<p>')
            msgbox.setText(''.join(text))
            msgbox.exec_()


def run_gui():
    app = QApplication(sys.argv)
    win = MainWindow()
    app.installEventFilter(win)
    win.showMaximized()
    return app.exec_()
