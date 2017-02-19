from collections import OrderedDict
import numpy as np
import pandas as pd


class Average:

    def __init__(self, name, total, drop):
        self.name = name
        self.total = total
        self.drop = drop
        self.minimum = total

    def compute(self, data):
        s = slice(self.drop, -self.drop if self.drop else None)
        def operator(d):
            return np.sort(d)[s].mean()
        return data.rolling(window=self.total, min_periods=self.total-self.drop).apply(operator)


class Single:

    def __init__(self):
        self.name = 'Single'
        self.minimum = 1

    def compute(self, data):
        return data


class StatsCollection:

    def __init__(self, *args):
        self.stats = args

    def compute(self, data):
        data = OrderedDict([(s.name, s.compute(data)) for s in self.stats])
        return pd.DataFrame(data=data)

    @property
    def minimum(self):
        return max(s.minimum for s in self.stats)


default_stats = StatsCollection(
    Single(),
    Average('Avg. of 5', 5, 1),
    Average('Avg. of 12', 12, 1),
    Average('Mean of 100', 100, 0),
)
