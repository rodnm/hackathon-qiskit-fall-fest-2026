"""Fija la referencia al módulo `backend` para que pytest resuelva `app.*`."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
