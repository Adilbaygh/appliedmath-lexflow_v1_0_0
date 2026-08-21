"""Deterministic lexicographic flow allocation on lossy capacitated trees."""

from .domain import Benchmark, Edge, User
from .io import load_benchmark
from .lexicographic import solve_three_stage
from .stage1 import solve_stage1_closed_form, solve_stage1_lp

__all__ = [
    "Benchmark",
    "Edge",
    "User",
    "load_benchmark",
    "solve_stage1_closed_form",
    "solve_stage1_lp",
    "solve_three_stage",
]

__version__ = "0.4.1"
