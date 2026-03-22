import os
import tempfile
import shutil
import subprocess
from typing import Optional


class GEMBuildError(RuntimeError):
    pass


def _has_carveme() -> bool:
    return shutil.which("carve") is not None


def build_gem_from_genome(genome_bytes: bytes, filename: str, model_id: Optional[str] = None) -> str:
    """
    Build a GEM from a genome FASTA/GBK using CarveMe CLI if available.

    Returns path to generated SBML file. Raises GEMBuildError on failure.
    """
    if not _has_carveme():
        raise GEMBuildError("CarveMe CLI ('carve') not found on PATH. Install carveme and ensure 'carve' is available.")

    suffix = os.path.splitext(filename)[1] or '.fasta'
    tmpdir = tempfile.mkdtemp(prefix='gem_build_')
    genome_path = os.path.join(tmpdir, f'genome{suffix}')
    with open(genome_path, 'wb') as f:
        f.write(genome_bytes)

    out_path = os.path.join(tmpdir, f"{model_id or 'auto_model'}.xml")
    cmd = ["carve", "-o", out_path, genome_path]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except Exception as e:
        raise GEMBuildError(f"Failed to invoke CarveMe: {e}")

    if res.returncode != 0 or not os.path.exists(out_path):
        raise GEMBuildError(f"CarveMe failed (code {res.returncode}). stderr: {res.stderr.strip()}")

    return out_path
