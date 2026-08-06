"""Shared speech, language, retrieval and telemetry layer.

Importing the package loads the environment, so entrypoints do not each have to.
"""

from core import config  # noqa: F401  - imported for its load-on-import effect
