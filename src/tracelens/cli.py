import argparse
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the TraceLens incident analysis service")
    parser.add_argument("serve", nargs="?", default="serve", choices=["serve"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("tracelens.api:app", host=args.host, port=args.port)
