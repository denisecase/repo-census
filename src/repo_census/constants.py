"""Project-wide census configuration."""

AUTHENTICATED_OWNER = "denisecase"

ORGANIZATION_ALLOWLIST = (
    "aauw-ely",
    "adaptive-interfaces",
    "analytics-toolworks",
    "applied-models",
    "civic-interconnect",
    "composable-data",
    "denisecase-org",
    "ely-has-pride",
    "ely-monday",
    "elytc",
    "genealogy-clusiau",
    "genealogy-hall",
    "genealogy-johnson",
    "genealogy-kokkinen",
    "humanity-lab",
    "kapsch-genealogy",
    "mn-area35-d08",
    "pup-pack",
    "structural-explainability",
    "toy-gpt",
    "wmnlp-materials",
)

DEFAULT_OWNERS = (AUTHENTICATED_OWNER, *ORGANIZATION_ALLOWLIST)
