from ct.scramble import CubeScrambler

from os.path import abspath, dirname, join


DATA_PATH = join(dirname(abspath(__file__)), 'data')


class Puzzle:

    def __init__(self, long_name, short_name, scrambler, inspection=0):
        self.long_name = long_name
        self.short_name = short_name
        self.scrambler = scrambler
        self.inspection = inspection

    @property
    def icon(self):
        return join(DATA_PATH, self.short_name + '.png')

puzzles = [
    Puzzle('2×2×2', '2', CubeScrambler(2), 15),
    Puzzle('3×3×3', '3', CubeScrambler(3), 15),
    Puzzle('4×4×4', '4', CubeScrambler(4), 15),
    Puzzle('5×5×5', '5', CubeScrambler(5), 15),
]

default_puzzle = puzzles[1]
