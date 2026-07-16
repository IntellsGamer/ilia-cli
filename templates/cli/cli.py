#!/usr/bin/env python3
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="{{ description }}")
    parser.add_argument("--name", "-n", default="world", help="Name to greet")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        print(f"{{ project_name }} v{{ version }}")
    print(f"Hello, {args.name}!")

if __name__ == "__main__":
    main()
