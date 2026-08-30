import csv
import sys
from collections import defaultdict

# quick + dirty report generator for the monthly export
# TODO: the date parsing is fragile, fix when we move off the legacy CSV

DATE_COL = 2
AMOUNT_COL = 5


def load(path):
    rows = []
    with open(path, newline="") as f:
        r = csv.reader(f)
        next(r)  # header
        for line in r:
            if not line or len(line) < 6:
                continue
            rows.append(line)
    return rows


def by_month(rows):
    out = defaultdict(float)
    for row in rows:
        d = row[DATE_COL]
        # dates come through as either YYYY-MM-DD or DD/MM/YYYY depending
        # on which upstream system exported them. yes really.
        if "/" in d:
            parts = d.split("/")
            key = parts[2] + "-" + parts[1]
        else:
            key = d[:7]
        try:
            out[key] += float(row[AMOUNT_COL])
        except ValueError:
            print("bad amount on row:", row[:3], file=sys.stderr)
    return out


if __name__ == "__main__":
    data = by_month(load(sys.argv[1]))
    for k in sorted(data):
        print(k, round(data[k], 2))
