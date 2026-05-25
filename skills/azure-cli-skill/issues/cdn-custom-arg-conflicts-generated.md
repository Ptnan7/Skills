# CDN Custom Args Conflict with Generated Args

## Symptom

After upgrading to a new swagger version, `azdev linter cdn` fails with:

  AAZConflictFieldDefinitionError: "Model 'AAZArgumentsSchema' has conflict defined field 'probe_interval_in_seconds': Key already been defined before"

## Cause

A new swagger version added those fields directly to the generated AAZ schema. The custom class still manually defines the same args, causing double-registration.

After upgrading cdn to 2025-09-01-preview, `afd origin-group create/update` AAZ now include probe settings as top-level HealthProbeSettings args. The custom classes in custom_afdx.py also added them.

## Fix

Use a guard that only adds the arg when the generated schema does not already include it:

    from azure.cli.core.aaz.exceptions import AAZUnknownFieldError

    def _has_arg(args_schema, name):
        try:
            getattr(args_schema, name)
        except AAZUnknownFieldError:
            return False
        return True

    def _add_health_probe_args(args_schema):
        if not _has_arg(args_schema, 'probe_interval_in_seconds'):
            args_schema.probe_interval_in_seconds = AAZIntArg(...)
        if not _has_arg(args_schema, 'probe_path'):
            args_schema.probe_path = AAZStrArg(...)
        # same for probe_protocol, probe_request_type

## Key Rule

Never use Python `in args_schema` to check for an existing field.
AAZArgumentsSchema.__contains__ interprets the string as index keys and raises
AAZUnknownFieldError: has no field named '0'. Always use getattr + except AAZUnknownFieldError.

## Affected File (2025-09-01-preview)

extension/src/cdn/azext_cdn/custom/custom_afdx.py
AFDOriginGroupCreate._build_arguments_schema and AFDOriginGroupUpdate._build_arguments_schema.
