"""SaaS domain package."""

from domains.saas.domain import SaaSDomain
from server.domain_registry import DomainRegistry

if DomainRegistry.get("saas") is None:
    DomainRegistry.register("saas", SaaSDomain)
