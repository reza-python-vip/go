"""Health package exports.

Re-export symbols from the module `src.health` so that importing the
package `src.health` provides the expected `app` FastAPI instance and
`main_loop_active` variable.
"""

from .health import app, main_loop_active  # noqa: F401

__all__ = ["app", "main_loop_active"]
