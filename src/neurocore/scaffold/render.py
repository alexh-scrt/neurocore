"""Template rendering helpers shared by ``neurocore init`` and ``neurocore new``.

Templates use a minimal ``{{ var }}`` substitution syntax (no real Jinja2
dependency). ``render_tree`` recursively copies a template directory, rendering
every text file through the same substitution.
"""
from __future__ import annotations

from pathlib import Path

# Binary/opaque file extensions copied verbatim (not rendered as text).
_BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip"}

# Template directory shipped with the package.
TEMPLATES_DIR = Path(__file__).parent / "templates"


def render_text(content: str, context: dict[str, str]) -> str:
    """Apply ``{{ var }}`` substitutions to a string."""
    for key, value in context.items():
        content = content.replace(f"{{{{ {key} }}}}", value)
    return content


def render_template(template_path: Path, context: dict[str, str]) -> str:
    """Render a single template file to a string."""
    return render_text(template_path.read_text(), context)


def render_tree(src_dir: Path, dest_dir: Path, context: dict[str, str]) -> None:
    """Recursively copy ``src_dir`` into ``dest_dir``, rendering text files.

    Directory names and file names are rendered too, so a template file named
    ``{{ project_name }}.py`` is renamed accordingly. ``.gitkeep`` files create
    empty directories without leaving the marker behind.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in sorted(src_dir.iterdir()):
        rendered_name = render_text(item.name, context)
        if item.is_dir():
            render_tree(item, dest_dir / rendered_name, context)
        elif item.name == ".gitkeep":
            # Marker: ensure the parent directory exists, but don't copy it.
            dest_dir.mkdir(parents=True, exist_ok=True)
        elif item.suffix in _BINARY_SUFFIXES:
            (dest_dir / rendered_name).write_bytes(item.read_bytes())
        else:
            (dest_dir / rendered_name).write_text(
                render_text(item.read_text(), context)
            )
