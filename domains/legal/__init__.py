from domains.legal.domain import LegalDomain
from server.domain_registry import DomainRegistry

if DomainRegistry.get("legal") is None:
    DomainRegistry.register("legal", LegalDomain)
