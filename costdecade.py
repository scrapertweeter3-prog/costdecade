#!/usr/bin/env python3
"""costdecade - price durability by the decade, not the receipt.

A cheap tool replaced three times costs more than the dear one bought once,
but nobody does that arithmetic at the shelf. costdecade does it: give each
candidate a price and how long it lasts, and the tool ranks them by real cost
per decade, finds the exact lifespan where the dear option starts winning,
and totals the spend over a full ownership horizon with replacement
inflation. Feed it a CSV of candidates for one category and it names the
winner, including the cases where the budget pick beats the heirloom one.

Usage:
    python3 costdecade.py --price 340 --life 10 --rival-price 120 --rival-life 2
    python3 costdecade.py --file candidates.csv --horizon 30 --inflation 3
    python3 costdecade.py --file candidates.csv --json

candidates.csv rows: name,price,life_years  (optional 4th column = warranty
years, which extends life to at least the warranty term).

Exit code 0 when a budget passed with --budget is met, 1 when the winner
still costs more than the budget allows.
"""

import argparse
import csv
import json
import sys

DECADE = 10.0


def spend_over(price, life, horizon, inflation_pct):
    """Total spend to keep one item class running for `horizon` years."""
    if life <= 0:
        raise ValueError("life must be positive")
    if inflation_pct <= 0:
        return price * (horizon / life)
    g = 1.0 + inflation_pct / 100.0
    n = 0
    total = 0.0
    year = 0.0
    while year < horizon:
        total += price * (g ** n)
        n += 1
        year += life
    return total


def effective_price(price, resale_pct):
    return price * (1.0 - resale_pct / 100.0)


def analyze(name, price, life, horizon, inflation_pct, resale_pct=0.0,
            warranty=0.0):
    if warranty > life:
        life = warranty
    ep = effective_price(price, resale_pct)
    per_year = ep / life
    return {
        "name": name,
        "price": round(price, 2),
        "life_years": round(life, 1),
        "cost_per_year": round(per_year, 2),
        "cost_per_decade": round(per_year * DECADE, 2),
        "spend_over_horizon": round(spend_over(ep, life, horizon,
                                               inflation_pct), 2),
    }


def break_even(cheap, dear):
    """Years the dear option must last before it beats the cheap one."""
    if dear["cost_per_year"] < cheap["cost_per_year"]:
        return 0.0
    return round(dear["price"] / cheap["cost_per_year"], 1)


def load_candidates(path):
    """Read name,price,life_years[,warranty] rows, pointing at the bad line."""
    import os

    cands = []
    if not os.path.exists(path):
        raise SystemExit("%s: no such file" % path)
    with open(path, newline="") as f:
        for lineno, row in enumerate(csv.reader(f), start=1):
            if not row or not any(cell.strip() for cell in row):
                continue
            if row[0].strip().startswith("#"):
                continue
            if len(row) < 3:
                raise SystemExit(
                    "%s:%d: expected 3 columns (name,price,life_years), got %d: %r"
                    % (path, lineno, len(row), ",".join(row)))
            nm = row[0].strip()
            try:
                pr = float(row[1])
                lf = float(row[2])
            except ValueError as exc:
                raise SystemExit("%s:%d: bad number for %r: %s"
                                 % (path, lineno, nm, exc)) from None
            if lf <= 0:
                raise SystemExit("%s:%d: life_years must be positive, got %r"
                                 % (path, lineno, row[2]))
            if pr < 0:
                raise SystemExit("%s:%d: price must not be negative, got %r"
                                 % (path, lineno, row[1]))
            wr = 0.0
            if len(row) > 3 and row[3].strip():
                try:
                    wr = float(row[3])
                except ValueError as exc:
                    raise SystemExit("%s:%d: bad warranty value %r: %s"
                                     % (path, lineno, row[3], exc)) from None
                if wr < 0:
                    raise SystemExit("%s:%d: warranty must not be negative, got %r"
                                     % (path, lineno, row[3]))
            cands.append((nm, pr, lf, wr))
    if not cands:
        raise SystemExit("%s: no candidate rows found" % path)
    return cands


def main():
    ap = argparse.ArgumentParser(
        description="price durability by the decade, not the receipt")
    ap.add_argument("--name", default="item")
    ap.add_argument("--price", type=float)
    ap.add_argument("--life", type=float, help="expected years of service")
    ap.add_argument("--rival-name", default="rival")
    ap.add_argument("--rival-price", type=float)
    ap.add_argument("--rival-life", type=float)
    ap.add_argument("--file", help="CSV: name,price,life_years[,warranty]")
    ap.add_argument("--horizon", type=float, default=30.0,
                    help="ownership horizon in years (default 30)")
    ap.add_argument("--inflation", type=float, default=0.0,
                    help="replacement price inflation pct/yr (default 0)")
    ap.add_argument("--resale", type=float, default=0.0,
                    help="salvage value as pct of price")
    ap.add_argument("--budget", type=float,
                    help="exit 1 unless winner's horizon spend fits")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cands = []
    if args.file:
        cands = load_candidates(args.file)
    else:
        if args.price is None or args.life is None:
            ap.error("need --file or --price/--life")
        cands.append((args.name, args.price, args.life, 0.0))
        if args.rival_price is not None and args.rival_life is not None:
            cands.append((args.rival_name, args.rival_price,
                          args.rival_life, 0.0))

    rows = [analyze(nm, pr, lf, args.horizon, args.inflation, args.resale, wr)
            for nm, pr, lf, wr in cands]
    rows.sort(key=lambda r: r["cost_per_decade"])
    best = rows[0]
    out = {
        "horizon_years": args.horizon,
        "inflation_pct": args.inflation,
        "resale_pct": args.resale,
        "winner": best["name"],
        "candidates": rows,
    }
    if len(rows) == 2:
        out["break_even_years_for_dearer"] = break_even(rows[0], rows[1])

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        print("cost per decade, ranked  (horizon %.0fy, inflation %.1f%%)"
              % (args.horizon, args.inflation))
        for r in rows:
            print("  %-22s $%8.2f/decade   $%7.2f/yr   $%9.2f over %.0fy"
                  % (r["name"], r["cost_per_decade"], r["cost_per_year"],
                     r["spend_over_horizon"], args.horizon))
        if len(rows) == 2:
            print("  break-even: %s must last %s years to win"
                  % (rows[1]["name"], out["break_even_years_for_dearer"]))
        print("  winner: %s" % best["name"])

    if args.budget is not None and best["spend_over_horizon"] > args.budget:
        if not args.json:
            print("  budget $%.0f EXCEEDED by $%.2f"
                  % (args.budget,
                     best["spend_over_horizon"] - args.budget))
        sys.exit(1)


if __name__ == "__main__":
    main()
