import pandas as pd
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("file1", type=str)
parser.add_argument("file2", type=str)
parser.add_argument("--join_on", type=str, nargs="+", default=None, required=True)
parser.add_argument("--join_type", type=str, choices=["left", "right", "outer", "inner", "cross", "left_anti", "right_anti"], default="inner")
parser.add_argument("--suffix1", type=str, default="_1")
parser.add_argument("--suffix2", type=str, default="_2")
parser.add_argument("--sorted", action="store_true", help="Sorts by the fields given in the field argument.")
parser.add_argument("--output", type=str, default="merged.csv")

def main(args):
    df_csv1 = pd.read_csv(args.file1, index_col=args.join_on)
    df_csv2 = pd.read_csv(args.file2, index_col=args.join_on)

    df_merged = df_csv1.merge(
        df_csv2,
        how="outer",
        on=args.join_on,
        suffixes=(args.suffix1, args.suffix2),
        sort=False
    )

    if args.sorted:
        df_merged.sort_index(inplace=True)
    df_merged.to_csv(args.output)

if __name__ == "__main__":
    main(parser.parse_args())