# pararius_reactor/__main__.py
import sys
from .main import main

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as e:
        print(f"[fatal] Uncaught error in Pararius Reactor: {e}", file=sys.stderr)
        sys.exit(1)
