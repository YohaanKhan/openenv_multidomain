from domains.hr.domain import HRDomain
from server.domain_registry import DomainRegistry

if DomainRegistry.get("hr") is None:
    DomainRegistry.register("hr", HRDomain)
