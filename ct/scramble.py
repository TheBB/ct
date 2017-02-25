from abc import abstractmethod
from random import choice


class CubeMove:

    def __init__(self, side, width, amount, size=3):
        self.side = side
        self.width = width
        self.amount = amount
        self.size = size

    def __eq__(self, other):
        if isinstance(other, CubeMove):
            return all([
                self.side == other.side,
                self.width == other.width,
                self.amount == other.amount,
            ])
        return False

    @property
    def slice(self):
        if self.side in 'LBD':
            return self.size - self.width
        return self.width

    def same_axis(self, other):
        return self.side in {
            side: group
            for group in ['FB', 'UD', 'LR']
            for side in group
        }[other.side]

    def same_layers(self, other):
        if not self.same_axis(other):
            return False
        return self.side == other.side and self.width == other.width

    def __str__(self):
        amount = {
            1: '',
            2: '²',
            -1: "'",
        }[self.amount]
        if self.size <= 5:
            return f"{self.side}{'w' if self.width > 1 else ''}{amount}"
        return f"{self.width if self.width > 1 else ''}{self.side}{amount}"

    def __repr__(self):
        return str(self)


class Scrambler:

    def scramble(self):
        moves = []
        while len(moves) < self.length:
            candidate = self.random_move()
            if self.valid(moves, candidate):
                moves.append(candidate)
        return ' '.join(str(m) for m in moves)

    @abstractmethod
    def random_move(self):
        pass

    @abstractmethod
    def valid(self, moves, candidate):
        pass


class CubeScrambler(Scrambler):

    def __init__(self, size=3, length=25):
        super(CubeScrambler, self).__init__()
        self.size = size
        self.length = length

    def random_move(self):
        widths = list(range(1, self.size // 2 + 1))
        amounts = [1, 2, -1]
        sides = 'FBUDLR'
        return CubeMove(choice(sides), choice(widths), choice(amounts), self.size)

    def valid(self, moves, candidate):
        valid = True
        slices = {candidate.slice}
        for m in moves[::-1]:
            if not m.same_axis(candidate):
                break
            if m.slice in slices:
                valid = False
                break
            slices.add(m.slice)
        return valid
