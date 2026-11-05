"""Compatibility import for code that used the old Stage 1 module.

Authorization now lives in ``padars.permissions_site``; membership does not
grant access.
"""

from padars.permissions_site import *  # noqa: F403
