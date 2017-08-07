# Version is set for releases by our build system.
# Be extremely careful when modifying.
version = 'SNAPSHOT'
"""DC/OS version"""

from . import cli  # noqa: E402
__all__ = ['cli']
