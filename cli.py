import argparse
import json

from config.logging_config import setup_logging
from analyzer import Analyzer


def main():
    parser = argparse.ArgumentParser(
        prog="spynet",
        description="SpyNet — web technology analyser",
    )
    parser.add_argument("url", help="Target URL to analyse (e.g. example.com)")
    parser.add_argument(
        "--depth",
        action="store_true",
        help="Return full WHOIS and Geo data instead of the summarised view",
    )
    parser.add_argument(
        "--snapshot",
        metavar="SNAPSHOT_URL",
        help="Analyse a Wayback Machine snapshot URL instead of a live site",
    )
    args = parser.parse_args()

    setup_logging()

    analyzer = Analyzer()

    if args.snapshot:
        result = analyzer.analyze_snapshot(args.snapshot)
    else:
        result = analyzer.analyze(args.url, depth_data=args.depth)

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
