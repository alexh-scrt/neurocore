"""Sphinx configuration for NeuroCore documentation."""

import os
import sys

# Make the package importable for autodoc / autoapi
sys.path.insert(0, os.path.abspath("../src"))

# ---------------------------------------------------------------------------
# Project metadata
# ---------------------------------------------------------------------------
project = "NeuroCore"
copyright = "2025, NeuroCore Contributors"
author = "NeuroCore Contributors"
release = "0.1.0"

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
extensions = [
    # Markdown support
    "myst_parser",
    # Auto-generates API reference from source (no import required)
    "autoapi.extension",
    # Standard Sphinx extras
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    # Mermaid diagram rendering (used in ARCHITECTURE.md)
    "sphinxcontrib.mermaid",
]

# ---------------------------------------------------------------------------
# Source files
# ---------------------------------------------------------------------------
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Tell Sphinx to accept both .rst and .md
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# ---------------------------------------------------------------------------
# MyST parser options
# ---------------------------------------------------------------------------
myst_enable_extensions = [
    "colon_fence",   # ::: fences as an alternative to ```
    "deflist",       # Definition lists
    "tasklist",      # - [ ] task items
]
# Render ```mermaid code fences as proper Mermaid diagrams
myst_fence_as_directive = ["mermaid"]
myst_heading_anchors = 3

# ---------------------------------------------------------------------------
# AutoAPI — static analysis of src/neurocore, no imports needed
# ---------------------------------------------------------------------------
autoapi_dirs = ["../src"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]
autoapi_own_page_level = "class"
autoapi_add_toctree_entry = True    # Let autoapi inject its toctree entry into the master doc

# Suppress noisy warnings from markdown code fences in docstrings and
# duplicate symbol descriptions caused by re-exports in __init__.py
suppress_warnings = [
    "ref.python",
    "autoapi",
]

# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------
html_theme = "furo"
html_title = "NeuroCore"

# ---------------------------------------------------------------------------
# Intersphinx
# ---------------------------------------------------------------------------
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
