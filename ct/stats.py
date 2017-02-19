import numpy as np


def avg(total, drop):
    s = slice(drop, -drop if drop else None)
    def operator(data):
        return np.sort(data)[s].mean()
    def inner(df):
        return df.rolling(window=total, min_periods=total-drop).apply(operator)
    return inner

def single(df):
    return df

stats = {
    'Single': single,
    'Avg. of 5': avg(5, 1),
    'Avg. of 12': avg(12, 1),
    'Mean of 100': avg(100, 0),
}
