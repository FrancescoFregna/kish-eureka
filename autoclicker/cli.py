"""Interfaccia a riga di comando per l'autoclicker."""

from __future__ import annotations

import argparse
import sys
import time

from .engine import ClickEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Autoclicker multipiattaforma con interfaccia moderna e CLI."
        )
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=0.1,
        help="Intervallo in secondi tra un click e l'altro (default: 0.1)",
    )
    parser.add_argument(
        "--button",
        choices=["left", "right", "middle"],
        default="left",
        help="Pulsante del mouse da utilizzare",
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Numero massimo di click da eseguire",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Durata massima in secondi",
    )
    parser.add_argument(
        "--countdown",
        type=float,
        default=0.0,
        help="Ritardo iniziale prima di iniziare i click (secondi)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Avvia l'interfaccia grafica moderna",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.gui:
        from .gui import launch_app

        launch_app()
        return 0

    try:
        engine = ClickEngine(interval=args.interval, button=args.button)
    except Exception as exc:  # pragma: no cover - dipende dall'ambiente
        parser.error(str(exc))
        return 2

    if args.count is not None and args.count <= 0:
        parser.error("--count deve essere maggiore di zero")
    if args.duration is not None and args.duration <= 0:
        parser.error("--duration deve essere maggiore di zero")
    if args.countdown < 0:
        parser.error("--countdown deve essere maggiore o uguale a zero")

    if args.count is not None or args.duration is not None:
        if args.countdown > 0:
            print(f"Avvio tra {args.countdown:.2f}s...")
            time.sleep(args.countdown)
        engine.run_blocking(count=args.count, duration=args.duration)
    else:
        print("Premi Ctrl+C per fermare l'autoclicker.")
        if args.countdown > 0:
            print(f"Avvio tra {args.countdown:.2f}s...")
            time.sleep(args.countdown)
        engine.start()
        try:
            while engine.is_running():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nInterruzione richiesta, arresto...")
        finally:
            engine.stop()

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
