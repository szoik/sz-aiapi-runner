#!/usr/bin/env python3
"""
Convert result.tsv to result2.tsv with split volume columns.

Transforms:
  volume (30x25x5) -> vw, vl, vh (sorted descending: 30, 25, 5)
  packed_volume (30x25x3) -> pvw, pvl, pvh (sorted descending: 30, 25, 3)

Usage:
  python scripts/result_to_tsv2.py <input.tsv> [output.tsv]

If output is not specified, writes to result2.tsv in the same directory as input.
"""

import argparse
import csv
from pathlib import Path


def split_volume(vol_str: str) -> list[str]:
    """Split volume string (e.g., '30x25x5') into sorted descending values."""
    if not vol_str:
        return ['', '', '']
    parts = vol_str.split('x')
    nums = sorted([float(p) for p in parts], reverse=True)
    result = []
    for n in nums:
        if n == int(n):
            result.append(str(int(n)))
        else:
            result.append(str(n))
    return result


def calc_volume_m3(w: str, l: str, h: str) -> str:
    """Calculate volume in m³ from cm dimensions. Returns rounded to 2 decimals."""
    if not w or not l or not h:
        return ''
    vol = float(w) * float(l) * float(h) / 1000000
    return f'{vol:.2f}'


def convert(input_path: Path, output_path: Path) -> None:
    with open(input_path, 'r') as infile:
        reader = csv.DictReader(infile, delimiter='\t')

        new_header = ['id', 'productName', 'category', 'vw', 'vl', 'vh', 'vol', 'pvw', 'pvl', 'pvh', 'pvol', 'weight', 'reason']

        rows = []
        for row in reader:
            if not row.get('id'):  # blank line (error item)
                rows.append({h: '' for h in new_header})
                continue

            vol = split_volume(row.get('volume', ''))
            pvol = split_volume(row.get('packed_volume', ''))

            new_row = {
                'id': row['id'],
                'productName': row['productName'],
                'category': row['category'],
                'vw': vol[0],
                'vl': vol[1],
                'vh': vol[2],
                'vol': calc_volume_m3(vol[0], vol[1], vol[2]),
                'pvw': pvol[0],
                'pvl': pvol[1],
                'pvh': pvol[2],
                'pvol': calc_volume_m3(pvol[0], pvol[1], pvol[2]),
                'weight': row['weight'],
                'reason': row['reason']
            }
            rows.append(new_row)

    with open(output_path, 'w') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=new_header, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)

    print(f'Converted {input_path} -> {output_path}')


def main():
    parser = argparse.ArgumentParser(description='Convert result.tsv to result2.tsv with split volume columns')
    parser.add_argument('input', help='Input TSV file (result.tsv)')
    parser.add_argument('output', nargs='?', help='Output TSV file (default: result2.tsv in same directory)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / 'result2.tsv'

    convert(input_path, output_path)


if __name__ == '__main__':
    main()
