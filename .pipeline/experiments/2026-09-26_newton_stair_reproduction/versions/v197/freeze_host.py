"""Freeze or verify the v197 display package."""
import argparse
from freeze_display import freeze, verify

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("freeze", "verify"))
    args = parser.parse_args()
    (freeze if args.action == "freeze" else verify)()
