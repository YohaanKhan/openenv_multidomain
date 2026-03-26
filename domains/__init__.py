"""Domain plugin package for multi-domain OpenEnv."""

# Importing each domain package triggers DomainRegistry.register() via their __init__.py
# This file is imported at the TOP of server/app.py before create_app() is called
from domains import saas  # noqa: F401
from domains import hr  # noqa: F401
from domains import legal  # noqa: F401
