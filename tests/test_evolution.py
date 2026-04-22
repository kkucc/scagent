import ast

import pytest

from stem_core.evolution import SecurityASTVisitor, SecurityError


# helper to run visitor on source
def _visit_src(src: str, allowed=None):
    if allowed is None:
        allowed = {"requests", "json", "urllib", "re", "time", "datetime"}
    tree = ast.parse(src)
    SecurityASTVisitor(set(allowed)).visit(tree)


@pytest.mark.parametrize(
    "mod",
    [
        "os",
        "sys",
        "subprocess",
        "socket",
        "pandas",
        "numpy",
        "torch",
    ],
)
def test_top_level_imports_denied(mod: str):
    # building 'import X' should fail for non-whitelisted mods
    src = f"import {mod}\n"
    with pytest.raises(SecurityError):
        _visit_src(src)


@pytest.mark.parametrize(
    "mod",
    [
        "requests",
        "json",
        "urllib",
        "re",
        "time",
        "datetime",
    ],
)
def test_whitelisted_imports_allowed(mod: str):
    # allowed imports should pass
    src = f"import {mod}\n"
    _visit_src(src)  # no raise


@pytest.mark.parametrize(
    "stmt",
    [
        "from . import local_module\n",
        "from ..util import helpers\n",
        "from ...pkg import thing\n",
    ],
)
def test_relative_imports_forbidden(stmt: str):
    # relative imports banned hard
    with pytest.raises(SecurityError):
        _visit_src(stmt)


@pytest.mark.parametrize(
    "stmt",
    [
        "from pandas import DataFrame\n",
        "from numpy import array\n",
        "from httpx import Client\n",
    ],
)
def test_from_disallowed_module_forbidden(stmt: str):
    # from X import Y must respect whitelist
    with pytest.raises(SecurityError):
        _visit_src(stmt)


def test_mixed_allowed_and_disallowed_imports_fails():
    # any disallowed in the tree should fail even if others ok
    src = "import json\nimport os\nimport time\n"
    with pytest.raises(SecurityError):
        _visit_src(src)


def test_no_imports_is_ok():
    # pure code no imports ok
    src = "def foo():\n    return 1 + 2\n"
    _visit_src(src)  # no raise
