"""Nonblocking cross-process admission for project-managed model/training work."""

from contextlib import contextmanager
from functools import wraps
import psutil
from fastapi import HTTPException
from nexora.artifacts import lock
from nexora.config import STORE


@contextmanager
def admission(kind, store=None):
    if psutil.virtual_memory().available < 500 * 1024**2:
        raise HTTPException(503, "Available RAM below 500 MiB; postpone compute")
    # Separate acquisition from the body: never disguise application ValueErrors.
    manager = lock((store or STORE) / ".compute.lock")
    try:
        manager.__enter__()
    except ValueError as exc:
        raise HTTPException(
            429, "Another project-managed inference/training job is active"
        ) from exc
    try:
        yield {"kind": kind}
    finally:
        manager.__exit__(None, None, None)


def compute_job(kind):
    def decorate(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            with admission(kind):
                return fn(*args, **kwargs)

        return wrapped

    return decorate
