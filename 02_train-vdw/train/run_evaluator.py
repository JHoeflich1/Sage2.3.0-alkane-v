"""Run the ASHGC LJ fit, with charge checks in the driver and task process."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from preflight import ROOT, check_charges


def forcebalance_arguments(resume=False, root=ROOT):
    """Validate fresh-run/recovery state before starting fitting services."""
    root = Path(root)
    if resume:
        saved = root / "optimize.sav"
        if not saved.is_file() or saved.stat().st_size == 0:
            raise RuntimeError("--resume requires a nonempty optimize.sav from this ASHGC fit.")
        if not (root / "optimize.tmp").is_dir():
            raise RuntimeError("--resume requires the original optimize.tmp directory.")
        return ["--continue", "optimize.in"]
    previous = [p for p in ("optimize.sav", "optimize.tmp", "result",
                            "stored_data", "working-data") if (root / p).exists()]
    if previous:
        raise RuntimeError(
            f"Existing run artifacts: {previous}. Use --resume to continue this same "
            "ASHGC fit, or use a clean directory for a new fit."
        )
    return ["optimize.in"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true",
                        help="Check driver and Evaluator task charges, then exit without MD.")
    parser.add_argument("--cpu", action="store_true", help="Use CPU resources for preflight.")
    parser.add_argument("--resume", action="store_true",
                        help="Continue this ASHGC fit using optimize.sav and optimize.tmp.")
    args = parser.parse_args()
    if args.cpu and not args.preflight_only:
        parser.error("--cpu is only supported with --preflight-only")
    if args.resume and args.preflight_only:
        parser.error("--resume cannot be combined with --preflight-only")
    os.chdir(ROOT)
    fb_arguments = None if args.preflight_only else forcebalance_arguments(args.resume)

    # Report missing dependencies before Evaluator plugin imports obscure them.
    subprocess.run([sys.executable, str(ROOT / "preflight.py"), "--environment-only"], check=True)

    from forcebalance.evaluator_io import Evaluator_SMIRNOFF  # noqa: F401
    from openff.evaluator.backends import ComputeResources
    from openff.evaluator.backends.dask import DaskLocalCluster
    from openff.evaluator.server import EvaluatorServer
    from openff.evaluator.storage import LocalFileStorage

    # A new Python process verifies that the pinned registry also works outside
    # this driver (ForceBalance itself is launched in a fresh process below).
    subprocess.run([sys.executable, str(ROOT / "preflight.py")], check=True)
    if not args.cpu:
        if len(os.environ.get("CUDA_VISIBLE_DEVICES", "").split(",")) != 1 or not os.environ.get("CUDA_VISIBLE_DEVICES"):
            raise RuntimeError("Request exactly one GPU; set CUDA_VISIBLE_DEVICES for local runs.")

    resources = ComputeResources(number_of_threads=1, number_of_gpus=0 if args.cpu else 1,
                                 preferred_gpu_toolkit=ComputeResources.GPUToolkit.CUDA)
    backend = DaskLocalCluster(number_of_workers=1, resources_per_worker=resources)
    backend.start()
    server = None
    try:
        # submit_task exercises Evaluator's task subprocess, not just a Dask thread.
        result = backend.submit_task(check_charges, str(ROOT)).result()
        print("Evaluator task ASHGC preflight:", json.dumps(result, indent=2), flush=True)
        if args.preflight_only:
            return
        options_path = ROOT / "targets/pure_data/options.json"
        options = json.loads(options_path.read_text())
        port = int(os.environ.get("EVALUATOR_PORT", options["connection_options"]["server_port"]))
        if not 1 <= port <= 65535:
            raise ValueError("EVALUATOR_PORT must be between 1 and 65535.")
        # ForceBalance reads this same file, so keep client and server in sync.
        options["connection_options"]["server_port"] = port
        options_path.write_text(json.dumps(options, indent=4) + "\n")
        print(f"Evaluator server and ForceBalance client port: {port}", flush=True)
        server = EvaluatorServer(
            calculation_backend=backend,
            storage_backend=LocalFileStorage(root_directory=str(ROOT / "stored_data")),
            working_directory=str(ROOT / "working-data"),
            port=options["connection_options"]["server_port"],
        )
        server.start(asynchronous=True)
        # Use this interpreter's script, not a ForceBalance on another PATH.
        fb = Path(sys.executable).parent / "ForceBalance.py"
        if not fb.is_file():
            raise FileNotFoundError(f"ForceBalance entry point not found: {fb}")
        print("Starting ForceBalance:", " ".join(fb_arguments), flush=True)
        subprocess.run([sys.executable, str(fb), *fb_arguments], check=True)
    finally:
        if server is not None:
            server.stop()
        backend.stop()


if __name__ == "__main__":
    main()
