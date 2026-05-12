"""arxivhaiku CLI.

Usage:
  python -m arxivhaiku                       generate one haiku alias
  python -m arxivhaiku -n 10                 generate 10 aliases
  python -m arxivhaiku --sep _               use '_' separator
  python -m arxivhaiku encode 0x1234567      canonical (int) → alias
  python -m arxivhaiku encode K3X9P          5-char Crockford → alias
  python -m arxivhaiku decode frosty-meadow  alias → int canonical and Crockford
"""
from __future__ import annotations
import argparse
import sys

from arxivhaiku.codec import (
    haiku, encode, decode, encode_crockford, decode_crockford,
    InvalidAliasError, InvalidCanonicalError, CANON_MAX, CANON_CHARS,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="arxivhaiku", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    p_gen = sub.add_parser("gen", help="generate random aliases (default)")
    p_gen.add_argument("-n", "--count", type=int, default=1,
                       help="number of aliases to generate (default 1)")
    p_gen.add_argument("--sep", default="-", help="separator (default '-')")

    p_enc = sub.add_parser("encode", help="canonical → alias")
    p_enc.add_argument("value",
                       help="canonical: int (e.g. 12345) or 0xHEX, or 5-char Crockford (e.g. K3X9P)")
    p_enc.add_argument("--sep", default="-")
    p_enc.add_argument("--crockford-out", action="store_true",
                       help="also print the 5-char Crockford form")

    p_dec = sub.add_parser("decode", help="alias → canonical")
    p_dec.add_argument("alias")
    p_dec.add_argument("--sep", default="-")

    # If no subcommand given, treat as 'gen'
    args = p.parse_args(argv)
    if args.cmd is None:
        args.cmd = "gen"
        args.count = 1
        args.sep = "-"

    if args.cmd == "gen":
        for _ in range(args.count):
            print(haiku(separator=args.sep))
        return 0

    if args.cmd == "encode":
        v = args.value.strip()
        # Try int forms first
        canonical: int | None = None
        if v.startswith(("0x", "0X")):
            try: canonical = int(v, 16)
            except ValueError: pass
        elif v.isdigit():
            canonical = int(v)
        # Crockford fallback
        if canonical is None:
            try:
                canonical = decode_crockford(v)
            except InvalidCanonicalError as e:
                print(f"error: {e}", file=sys.stderr); return 2
        if canonical < 0 or canonical > CANON_MAX:
            print(f"error: canonical out of range [0, {CANON_MAX}]", file=sys.stderr)
            return 2
        alias = encode(canonical, separator=args.sep)
        if args.crockford_out:
            print(f"{alias}\t{encode_crockford(canonical)}\t{canonical}")
        else:
            print(alias)
        return 0

    if args.cmd == "decode":
        try:
            canonical = decode(args.alias, separator=args.sep)
        except InvalidAliasError as e:
            print(f"error: {e}", file=sys.stderr); return 2
        print(f"{canonical}\t0x{canonical:07x}\t{encode_crockford(canonical)}")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
