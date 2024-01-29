"""Allow `python -m autoflow ...`."""

import sys

from .cli import main

sys.exit(main())
