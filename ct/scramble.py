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

    def same_axis(self, other):
        return self.side in {
            side: group
            for group in ['FB', 'UD', 'LF']
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


class Scrambler:

    def scrambles(self):
        while True:
            moves = []
            while len(moves) < self.length:
                candidate = self.random_move()
                if self.valid(moves, candidate):
                    moves.append(candidate)
            yield ' '.join(str(m) for m in moves)


class CubeScrambler(Scrambler):

    _length = {
        2: 25,
        3: 25,
        4: 40,
        5: 60,
    }

    def __init__(self, size=3):
        super(CubeScrambler, self).__init__()
        self.size = size

    @property
    def length(self):
        return self._length[self.size]

    def random_move(self):
        widths = list(range(1, self.size // 2 + 1))
        amounts = [1, 2, -1]
        sides = 'FBUDLF'
        return CubeMove(choice(sides), choice(widths), choice(amounts), self.size)

    def valid(self, moves, candidate):
        valid = True
        n_same_axis, max_same_axis = 0, self.size - 1
        for m in moves[::-1]:
            if not m.same_axis(candidate):
                break
            if m.same_layers(candidate):
                valid = False
                break
            else:
                n_same_axis += 1
                if n_same_axis == max_same_axis:
                    valid = False
                    break
        return valid
