"""
Hostname generation with strict org email convention and single-char month_hex.

Public entrypoint:
    generate(config: Mapping[str, str]) -> dict

"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping, Optional, Tuple

from ..enums import OS, Environment, Location, ServerType
from .logger import get_logger
from .utils import build_parts, make_id

logger = get_logger(__name__)

# === Constants ===
DEFAULT_SUB_PROJECT_ID = ""
LOGICAL_LOCATION = "t"  # TODO: update if Nutanix layout changes
SPECIAL_PROJECT = "sssd_sbx"


# === Utility ===
def _norm(value: Optional[str]) -> Optional[str]:
    """Lowercase and strip a possibly-None string; return None for falsy/blank."""
    if value is None or not isinstance(value, str):
        return None
    value = value.strip()
    return value.lower() if value else None


def _get(
    cfg: Optional[Mapping[str, str]], key: str, default: Optional[str] = None
) -> Optional[str]:
    """Safe getter from config mapping with optional default."""
    if not cfg:
        return default
    return cfg.get(key, default)


def _extract_initials(email: str) -> Tuple[str, str]:
    """
    Extract initials according to the organization's convention:
      - firstname.lastname@irs.gov
      - firstname.middleinitial.lastname@irs.gov

    Returns:
        (first_initial, last_initial) in lowercase.

    Raises:
        ValueError: if the address doesn't match the convention.
    """
    if not isinstance(email, str):
        raise ValueError(f"Failed to parse owner email: {email!r}")

    email = email.strip().lower()
    pattern = (
        r"^([a-z]+)"  # firstname
        r"(?:\.([a-z]))?"  # optional .m (middle initial)
        r"\.([a-z]+)"  # .lastname
        r"@irs\.gov$"  # strict domain
    )
    m = re.match(pattern, email)
    if not m:
        raise ValueError(
            "Owner email must be 'firstname.lastname@irs.gov' or "
            "'firstname.middleinitial.lastname@irs.gov' (case-insensitive). "
            f"Got: {email!r}"
        )
    firstname, _middle, lastname = m.groups()
    return firstname[0], lastname[0]


# === Data carrier for validated inputs ===
@dataclass(frozen=True)
class HostnameParams:
    os_code: str
    env_code: str
    loc_code: str
    type_code: str
    project: str
    project_id: str
    sub_project_id: Optional[str]
    first_initial: str
    last_initial: str
    month_hex: str  # must be exactly one char: "1"-"9","A","B","C"
    day_dec: str  # "01"-"31"
    logical_location: str
    special_case: bool
    id_func: Callable[[int], str]
    is_linux: bool  # for case rule


def _prepare_params(
    config: Optional[Mapping[str, str]] = None,
    *,
    os_type: Optional[str] = None,
    owner_email: Optional[str] = None,
    location: Optional[str] = None,
    environment: Optional[str] = None,
    server_type: Optional[str] = None,
    project: Optional[str] = None,
    project_id: Optional[str] = None,
    sub_project_id: Optional[str] = None,
    id_func: Optional[Callable[[int], str]] = None,
) -> HostnameParams:
    """
    Normalize, validate, and convert inputs into a single params object.
    This is the single source of truth for validation.
    """
    # Resolve inputs with precedence: explicit arg > config
    os_type = _norm(os_type) or _norm(_get(config, "os_type"))
    owner_email = _norm(owner_email) or _norm(_get(config, "owner_email"))
    location = _norm(location) or _norm(_get(config, "location"))
    environment = _norm(environment) or _norm(_get(config, "environment"))
    server_type = _norm(server_type) or _norm(_get(config, "server_type"))
    project = _norm(project) or _norm(_get(config, "project"))
    project_id = _norm(project_id) or _norm(_get(config, "project_id"))
    sub_project_id = _norm(sub_project_id) or _norm(
        _get(config, "sub_project_id", DEFAULT_SUB_PROJECT_ID)
    )

    # Required fields vary by special_case
    required = {
        "os_type": os_type,
        "location": location,
        "environment": environment,
        "server_type": server_type,
        "project": project,
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Enum coercions -> codes
    os_enum = OS.from_str(os_type)  # raises KeyError on bad name
    env_enum = Environment.from_str(environment)
    loc_enum = Location.from_str(location)
    type_enum = ServerType.from_str(server_type)

    os_code = os_enum.code
    env_code = env_enum.code
    loc_code = loc_enum.code
    type_code = type_enum.code

    # special-case = project is SPECIAL_PROJECT AND env is nonprod per enum helper
    special_case = project == SPECIAL_PROJECT and env_enum.is_nonprod()

    # Only require/parse owner_email when special_case applies
    if special_case:
        required["owner_email"] = owner_email

    # Email initials (strict org convention) only if special_case
    if special_case:
        first_initial, last_initial = _extract_initials(owner_email)
    else:
        first_initial, last_initial = "", ""

    # Time parts with strong validation; month_hex must be 1 char
    now = datetime.now()
    month = now.month
    month_hex = f"{month:X}"  # 1..9, A, B, C
    day_dec = f"{now.day:02d}"

    # ID function
    id_func = id_func or make_id

    return HostnameParams(
        os_code=os_code,
        env_code=env_code,
        loc_code=loc_code,
        type_code=type_code,
        project=project,
        project_id=project_id,
        sub_project_id=sub_project_id or None,
        first_initial=first_initial,
        last_initial=last_initial,
        month_hex=month_hex,
        day_dec=day_dec,
        logical_location=LOGICAL_LOCATION,
        special_case=special_case,
        id_func=id_func,
        is_linux=(os_type == "linux"),
    )


def _build_hostname(p: HostnameParams) -> str:
    """
    Assemble the hostname from validated params.
    Minimal assertions to catch programmer errors (not user input).
    """
    assert p.os_code and p.env_code and p.loc_code and p.type_code, "Enum codes must be present"

    if p.special_case:
        base = build_parts(
            "vs",
            p.os_code,
            p.loc_code,
            p.logical_location,
            p.first_initial,
            p.last_initial,
            p.month_hex,
            p.day_dec,
            p.id_func(5),
        )
    else:
        if not p.sub_project_id:
            base = build_parts(
                "v",
                p.env_code,
                p.os_code,
                p.loc_code,
                "x",
                p.type_code,
                p.project_id,
                p.id_func(5),
            )
        else:
            base = build_parts(
                "v",
                p.env_code,
                p.os_code,
                p.loc_code,
                "x",
                p.type_code,
                p.project_id,
                p.sub_project_id,
                p.id_func(2),
            )

    # Case rule: Linux -> lower; everything else -> upper
    return base.lower() if p.is_linux else base.upper()


# === Public ===
def generate(
    config: Optional[Mapping[str, str]] = None,
    os_type: Optional[str] = None,
    owner_email: Optional[str] = None,
    location: Optional[str] = None,
    environment: Optional[str] = None,
    server_type: Optional[str] = None,
    project: Optional[str] = None,
    project_id: Optional[str] = None,
    sub_project_id: Optional[str] = None,
    hostname: Optional[str] = None,
    domain: Optional[str] = None,
    *,
    id_func: Optional[Callable[[int], str]] = None,
) -> dict:
    """
    Public boundary: returns {'hostname': ..., 'fqdn': ...}
    - Validates presence of 'domain'
    - If a hostname override is provided, OS is determined strictly by the 3rd character of the hostname.
      * If the 3rd character does not map to OS -> ValueError
      * Linux -> lowercase, non-Linux -> uppercase
    - Otherwise, builds a hostname from validated params.
    - Enforces final hostname length of exactly 15.
    """
    # Require domain for FQDN
    domain = domain or _get(config, "domain")
    if not domain:
        raise ValueError("Missing required field: 'domain'")

    # Hostname override path (strict OS-from-3rd-char rule)
    override = hostname or _get(config, "hostname")
    if override:
        if not isinstance(override, str) or len(override) < 3:
            raise ValueError(f"Hostname is too short to determine OS: {override!r}")

        third = override[2]
        try:
            os_enum_from_char = OS.from_code(third)  # strict: raises ValueError if invalid
        except ValueError as err:
            raise ValueError(
                f"Invalid OS code '{third}' in 3rd character of hostname {override!r}"
            ) from err

        normalized = override.lower() if (os_enum_from_char is OS.LINUX) else override.upper()

        if len(normalized) != 15:
            logger.error("Hostname must be 15 characters (got %d): %s", len(normalized), normalized)
            raise ValueError(
                f"Hostname must be 15 characters (got {len(normalized)}): {normalized}"
            )

        fqdn = f"{normalized}.{domain}"
        logger.info("User specified Hostname: %s", normalized)
        return {"hostname": normalized, "fqdn": fqdn}

    # Build path (no override)
    params = _prepare_params(
        config=config,
        os_type=os_type,
        owner_email=owner_email,
        location=location,
        environment=environment,
        server_type=server_type,
        project=project,
        project_id=project_id,
        sub_project_id=sub_project_id,
        id_func=id_func,
    )

    built = _build_hostname(params)
    if len(built) != 15:
        logger.error("Hostname must be 15 characters (got %d): %s", len(built), built)
        raise ValueError(f"Hostname must be 15 characters (got {len(built)}): {built}")

    fqdn = f"{built}.{domain}"
    logger.info("Generated Hostname: %s", built)
    logger.info("Generated FQDN: %s", fqdn)
    return {"hostname": built, "fqdn": fqdn}
