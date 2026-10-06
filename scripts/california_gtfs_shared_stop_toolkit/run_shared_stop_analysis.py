"""Command-line runner for the California GTFS Shared-Stop Toolkit.

Usage (from the toolkit folder, in an ArcGIS Pro Python environment):
    python run_shared_stop_analysis.py --warehouse-dir "C:\\path\\to\\gtfs_warehouse"

Optional:
    --output-root   where outputs go (default: <warehouse-dir>\\outputs)
    --out-gdb       existing geodatabase to write layers into (default: a new
                    analysis.gdb inside the output folder)
    --offline-context-only   use only cached served-shape and road context
    --road-cache-gdb          geodatabase containing an existing road cache
    --replace-existing-outputs   allow overwriting outputs made by different toolkit code
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared_stop_toolkit.workflow import run_shared_stop_analysis


def main():
    p = argparse.ArgumentParser(description="California GTFS Shared-Stop Toolkit")
    p.add_argument("--warehouse-dir", required=True)
    p.add_argument("--output-root")
    p.add_argument("--out-gdb")
    p.add_argument("--offline-context-only", action="store_true")
    p.add_argument("--road-cache-gdb")
    p.add_argument("--replace-existing-outputs", action="store_true")
    a = p.parse_args()
    result = run_shared_stop_analysis(
        warehouse_dir=a.warehouse_dir,
        output_root=a.output_root,
        out_gdb=a.out_gdb,
        add_to_map=False,
        offline_context_only=a.offline_context_only,
        road_cache_gdb=a.road_cache_gdb,
        replace_existing_outputs=a.replace_existing_outputs,
    )
    print(f"Outputs: {result['output_dir']}")


if __name__ == "__main__":
    main()
