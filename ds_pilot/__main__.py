"""Use python -m ds_pilot to import sources, ask questions or start the chat."""
import argparse
from pathlib import Path
import sys
from uuid import uuid4

from .catalog import Catalog, PINS, load_git
from .engine import Pilot, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(".pilot"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("import").add_argument("checkout", type=Path)
    sub.add_parser("serve").add_argument("--port", default=8765, type=int)
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--session", default="cli")
    ask.add_argument("--json", action="store_true")
    sub.add_parser("manifest")
    args = parser.parse_args()
    try:
        if args.command == "import":
            files = load_git(args.checkout)
            catalog = Catalog(files)
            args.data.mkdir(mode=0o700, parents=True, exist_ok=True)
            for key, content in files.items():
                temp = args.data / f"{key}.{uuid4().hex}.tmp"
                temp.write_bytes(content)
                temp.replace(args.data / f"{key}.md")
            Pilot(catalog, args.data / "pilot.sqlite")
            print(encode(catalog.manifest()))
            return
        catalog = Catalog({key: (args.data / f"{key}.md").read_bytes() for key in PINS})
        if args.command == "manifest":
            print(encode(catalog.manifest()))
            return
        pilot = Pilot(catalog, args.data / "pilot.sqlite")
        if args.command == "ask":
            result = pilot.ask(args.question, args.session, uuid4().hex)
            if args.json:
                print(encode(result))
            else:
                print(result["text"])
                for key in ("verified_claims", "document_references", "conflict_positions"):
                    for record in result.get(key, []):
                        citation = record["citation"]
                        print(f"{citation['locator']} · {citation['url']}")
                        if "document_url" in record:
                            print(record["document_url"])
            return
        import uvicorn
        from .web import create_app

        uvicorn.run(create_app(pilot), host="127.0.0.1", port=args.port,
                    proxy_headers=False, access_log=False)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Ошибка источника или локального хранилища: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
