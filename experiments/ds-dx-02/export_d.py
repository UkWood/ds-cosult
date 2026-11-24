import argparse
from pathlib import Path
from bundle import export, verify_zip
from protocol import Stop

parser = argparse.ArgumentParser()
parser.add_argument("--knowledge", type=Path)
parser.add_argument("--zip", type=Path, required=True)
args = parser.parse_args()
try:
    if args.knowledge:
        export(args.knowledge, args.zip)
    print(verify_zip(args.zip)["identity"])
except Stop as error:
    raise SystemExit(str(error)) from None
