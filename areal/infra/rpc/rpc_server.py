# SPDX-License-Identifier: Apache-2.0

"""AReaL Sync RPC Server — Guard + Data + Engine composition.

This module composes the shared Guard with data and engine blueprints
to create the full RPC server used by training workers.

Usage::

    python -m areal.infra.rpc.rpc_server \\
        --experiment-name exp1 --trial-name trial1 \\
        --role actor --worker-index 0
"""

from __future__ import annotations

import logging as stdlib_logging
import os
import sys

from areal.infra.rpc.guard.app import (
    GuardState,
    configure_state_from_args,
    create_app,
    make_base_parser,
    run_server,
)
from areal.infra.rpc.guard.data_blueprint import data_bp
from areal.infra.rpc.guard.engine_blueprint import engine_bp, register_engine_hooks
from areal.utils import logging, perf_tracer

logger = logging.getLogger("SyncRPCServer")


def _worker_role_from_argv() -> str | None:
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == "--role" and i + 1 < len(argv):
            return argv[i + 1]
    return None


def _maybe_enable_debugpy() -> None:
    port_str = os.environ.get("AREAL_DEBUGPY_PORT", "").strip()
    if not port_str:
        return
    # Forked workers (e.g. eval-rollout) inherit AREAL_DEBUGPY_PORT from the parent
    # rollout process; only the primary rollout RPC server should bind the port.
    role = _worker_role_from_argv()
    if role is not None and role != "rollout":
        logger.info(
            "Skipping debugpy for role %r (AREAL_DEBUGPY_PORT is set on parent only)",
            role,
        )
        return
    import debugpy

    port = int(port_str)
    debugpy.listen(("0.0.0.0", port))
    logger.info("debugpy listening on 0.0.0.0:%s (attach from VS Code)", port)


def main():
    _maybe_enable_debugpy()

    parser = make_base_parser(
        description="AReaL Sync RPC Server for TrainEngine/InferenceEngine"
    )
    parser.add_argument(
        "--werkzeug-log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level for Werkzeug (Flask's WSGI server). Default: WARNING",
    )

    args, _ = parser.parse_known_args()

    werkzeug_logger = stdlib_logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(getattr(stdlib_logging, args.werkzeug_log_level))

    state = GuardState()
    bind_host = configure_state_from_args(state, args)

    app = create_app(state)
    app.register_blueprint(data_bp)
    app.register_blueprint(engine_bp)
    register_engine_hooks(state)

    state.register_cleanup_hook(lambda: perf_tracer.save(force=True))

    logger.info(f"Werkzeug log level: {args.werkzeug_log_level}")

    run_server(state, app, bind_host, args.port)


if __name__ == "__main__":
    main()
