import argparse
import subprocess
from pathlib import Path


def run_carveme(
    fasta_path: Path,
    output_path: Path,
    solver: str = "scip",
    cwd: Path | None = None,
) -> None:
    """Call carve to build the model."""
    workdir = cwd if cwd else Path(__file__).resolve().parents[2]
    cmd = ["carve", str(fasta_path), "--solver", solver, "-o", str(output_path)]
    try:
        subprocess.run(cmd, check=True, cwd=workdir)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "CarveMe CLI was not found. Install CarveMe and ensure the `carve` command is on PATH."
        ) from exc


def main():
    parser = argparse.ArgumentParser(
        description="Run CarveMe on a FASTA file and produce SBML"
    )
    parser.add_argument("--input", required=True, help="Path to input .faa/.fasta")
    parser.add_argument("--output", required=True, help="Path to output SBML (.xml)")
    parser.add_argument(
        "--solver", default="scip", help="Solver for CarveMe (default: scip)"
    )
    parser.add_argument(
        "--cwd", default=None, help="Working directory for carve (default: repo root)"
    )
    args = parser.parse_args()

    fasta_path = Path(args.input)
    output_path = Path(args.output)
    cwd = Path(args.cwd).resolve() if args.cwd else None

    run_carveme(
        fasta_path=fasta_path, output_path=output_path, solver=args.solver, cwd=cwd
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(str(exc))
