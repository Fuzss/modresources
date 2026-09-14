#!/usr/bin/env python3
"""Validation of CLI parameter sets against allowed values.

Purpose: normalize and validate the values the CLI accepts (open environment,
launch target, upload target, legacy scope) before they reach the Gradle
dispatchers, and reject the rest via ``error2``.

Entry points: ``main.py`` calls the ``validate_*`` functions; ``changelog.py``
reuses ``is_valid_parameter`` for changelog section names.

Side effects: validation failures print an error and terminate the process
through ``error2``. ``validate_launch_parameters`` also probes the project for
a Fabric or NeoForge subproject.

Constraints: standard library only; inputs are lowercased before comparison.
"""

from console import error2
from fs_utils import has_subproject


ENVIRONMENTS = {"finder", "idea"}
MOD_LOADERS = {"fabric", "neoforge"}
DISTRIBUTIONS = {"client", "server"}
UPLOADING_SITES = {"curseforge", "modrinth", "github"}
LEGACY_TYPES = {"properties", "tasks"}


def is_valid_parameter(value, allowed_values):
    """Exit with an error when ``value`` is not in ``allowed_values``.

    Side effects: calls ``error2`` (prints and exits) on invalid input;
    returns None on success.
    """
    if value not in allowed_values:
        error2(f"Invalid parameter '{value}'. Must be one of: {', '.join(sorted(allowed_values))}")


def validate_open_parameters(parameters, fallback_parameter):
    """Resolve the ``--open`` environment.

    Args:
        parameters: Values from ``--open`` (``None`` when the flag is absent,
            an empty list when given without a value).
        fallback_parameter: Environment returned for an empty list.

    Returns:
        The lowercased environment, ``fallback_parameter`` for an empty list,
        or None when the flag is absent.

    Side effects: exits via ``error2`` when the value is not a known
    environment.
    """
    if parameters is None:
        return None
    elif len(parameters) == 0:
        return fallback_parameter

    environment = parameters[0].lower()
    is_valid_parameter(environment, ENVIRONMENTS)
    return environment


def validate_launch_parameters(project_path, parameters):
    """Resolve one ``--launch`` entry to a ``(loader, distribution)`` pair.

    Empty input selects Fabric client, or NeoForge client when the project has
    only a NeoForge subproject. A single value defaults the distribution to
    client.

    Args:
        project_path: Project root used to detect subprojects.
        parameters: Values from one ``--launch`` occurrence.

    Returns:
        A lowercased ``(loader, distribution)`` tuple.

    Side effects: reads the project layout; exits via ``error2`` for invalid
    or undeterminable values.
    """
    if parameters is None:
        return None
    elif len(parameters) == 0:
        if has_subproject(project_path, "Fabric"):
            parameters = ("fabric", "client")
        elif has_subproject(project_path, "NeoForge"):
            parameters = ("neoforge", "client")
        else:
            error2("Unable to determine launch parameters")
    elif len(parameters) == 1:
        parameters = (parameters[0], "client")

    mod_loader = parameters[0].lower()
    other_argument = parameters[1].lower()
    is_valid_parameter(mod_loader, MOD_LOADERS)
    is_valid_parameter(other_argument, DISTRIBUTIONS)
    return (mod_loader, other_argument)


def validate_upload_parameters(parameters):
    """Resolve the ``--upload`` target.

    Args:
        parameters: Values from ``--upload``. An empty list means "all
            loaders, all sites"; a single loader or site fills the other slot
            with None.

    Returns:
        A lowercased ``(loader, site)`` tuple, ``(None, None)`` for an empty
        list, or None when the flag is absent.

    Side effects: exits via ``error2`` for values that are neither a known
    loader nor a known site.
    """
    if parameters is None:
        return None
    elif len(parameters) == 0:
        return (None, None)
    elif len(parameters) == 1:
        parameter = parameters[0].lower()
        if parameter in MOD_LOADERS:
            return (parameter, None)
        elif parameter in UPLOADING_SITES:
            return (None, parameter)

        is_valid_parameter(parameter, MOD_LOADERS | UPLOADING_SITES)

    mod_loader = parameters[0].lower()
    other_argument = parameters[1].lower()
    is_valid_parameter(mod_loader, MOD_LOADERS)
    is_valid_parameter(other_argument, UPLOADING_SITES)
    return (mod_loader, other_argument)


def validate_legacy_parameter(parameter):
    """Resolve ``--legacy`` into the set of legacy naming scopes.

    Returns:
        An empty set when the flag is absent, both scopes when it is given
        without a value, otherwise the single lowercased scope.

    Side effects: exits via ``error2`` for an unknown scope.
    """
    if parameter is None:
        return set()
    elif not isinstance(parameter, str):
        return set(LEGACY_TYPES)

    scope = parameter.lower()
    is_valid_parameter(scope, LEGACY_TYPES)
    return {scope}
