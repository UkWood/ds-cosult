"""Use python -m ds_pilot to import sources, ask questions or start the chat."""
import argparse
from pathlib import Path
import sys
from uuid import uuid4

from .catalog import import_checkout, load_local
from . import pdf_sources
from .engine import Pilot, encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(".pilot"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("import").add_argument("checkout", type=Path)
    serve = sub.add_parser("serve")
    serve.add_argument("--port", default=8765, type=int)
    serve.add_argument("--host", choices=["127.0.0.1"], default="127.0.0.1")
    serve.add_argument("--lab", action="store_true")
    serve.add_argument("--enable-deepseek", action="store_true")
    pdf_sources.add_commands(sub)
    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--session", default="cli")
    ask.add_argument("--json", action="store_true")
    sub.add_parser("manifest")
    args = parser.parse_args()
    try:
        if args.command == "import":
            catalog = import_checkout(args.checkout, args.data)
            Pilot(catalog, args.data / "pilot.sqlite")
            print(encode(catalog.manifest()))
            return
        catalog = load_local(args.data)
        if args.command in {"pdf-inventory", "import-pdf", "download-pdf"}:
            print(encode(pdf_sources.run_command(args, catalog)))
            return
        pdf_sources.load_pdfs(catalog, args.data)
        if args.command == "manifest":
            print(encode(catalog.manifest()))
            return
        if args.command == "ask":
            pilot = Pilot(catalog, args.data / "pilot.sqlite")
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

        from .providers import create_live
        if args.enable_deepseek and not args.lab:
            parser.error("--enable-deepseek требует --lab")
        live = create_live() if args.enable_deepseek else None
        try:
            database = args.data / ("lab.sqlite" if args.lab else "pilot.sqlite")
            pilot = Pilot(catalog, database, lab=args.lab, live=live)
            uvicorn.run(create_app(pilot), host=args.host, port=args.port,
                        proxy_headers=False, access_log=False)
        finally:
            if live:
                live.close()
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Ошибка источника или локального хранилища: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
