#!/usr/bin/env python3
"""Validation of CLI parameter sets against their allowed values."""

from console import error2
from fs_utils import has_subproject


ENVIRONMENTS = {"finder", "idea"}
MOD_LOADERS = {"fabric", "neoforge"}
DISTRIBUTIONS = {"client", "server"}
UPLOADING_SITES = {"curseforge", "modrinth", "github"}
LEGACY_TYPES = {"properties", "tasks"}


def is_valid_parameter(value, allowed_values):
    if value not in allowed_values:
        error2(f"Invalid parameter '{value}'. Must be one of: {', '.join(sorted(allowed_values))}")


def validate_open_parameters(parameters, fallback_parameter):
    if parameters is None:
        return None
    elif len(parameters) == 0:
        return fallback_parameter

    environment = parameters[0].lower()
    is_valid_parameter(environment, ENVIRONMENTS)
    return environment


def validate_launch_parameters(project_path, parameters):
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
    if parameter is None:
        return set()
    elif not isinstance(parameter, str):
        return set(LEGACY_TYPES)

    scope = parameter.lower()
    is_valid_parameter(scope, LEGACY_TYPES)
    return {scope}
