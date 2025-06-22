# backend/app/utils/validation.py
"""
Request validation utilities using Pydantic schemas
"""

import logging
from functools import wraps
from typing import Type, Optional, Dict, Any

from flask import request, jsonify
from pydantic import BaseModel, ValidationError as PydanticValidationError

from ..exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def validate_json_request(schema_class: Type[BaseModel], location: str = "json"):
    """
    Decorator to validate JSON request data against a Pydantic schema

    Args:
        schema_class: Pydantic model class to validate against
        location: Where to get the data from ('json', 'form', 'args')

    Usage:
        @song_bp.route("/api/songs", methods=["POST"])
        @validate_json_request(CreateSongRequest)
        def create_song(validated_data: CreateSongRequest):
            # validated_data is now a validated Pydantic model instance
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Get request data based on location
                if location == "json":
                    raw_data = request.get_json()
                    if raw_data is None:
                        raise RequestValidationError(
                            "Request must contain valid JSON data", "json", "null"
                        )
                elif location == "form":
                    raw_data = request.form.to_dict()
                elif location == "args":
                    raw_data = request.args.to_dict()
                else:
                    raise ValueError(f"Unsupported location: {location}")

                # Validate data against schema
                validated_data = schema_class.model_validate(raw_data)

                # Log successful validation
                logger.info(
                    "Request validated successfully",
                    extra={
                        "endpoint": func.__name__,
                        "schema": schema_class.__name__,
                        "fields": (list(raw_data.keys()) if isinstance(raw_data, dict) else []),
                    },
                )

                # Call the original function with validated data
                return func(validated_data, *args, **kwargs)

            except PydanticValidationError as e:
                # Convert Pydantic errors to our custom exception
                error_details = []
                for error in e.errors():
                    field_path = " -> ".join(str(loc) for loc in error["loc"])
                    error_details.append(
                        {
                            "field": field_path,
                            "message": error["msg"],
                            "type": error["type"],
                            "input": error.get("input"),
                        }
                    )

                logger.warning(
                    "Request validation failed",
                    extra={
                        "endpoint": func.__name__,
                        "schema": schema_class.__name__,
                        "errors": error_details,
                    },
                )

                raise RequestValidationError(
                    f"Request validation failed for {schema_class.__name__}",
                    "validation_errors",
                    {"errors": error_details},
                )

            except RequestValidationError:
                # Re-raise our custom validation errors
                raise

            except Exception as e:
                logger.error(
                    f"Unexpected error during request validation: {e}",
                    exc_info=True,
                    extra={"endpoint": func.__name__, "schema": schema_class.__name__},
                )
                raise RequestValidationError(
                    "Request validation failed due to internal error",
                    "internal_validation_error",
                    {"original_error": str(e)},
                )

        return wrapper

    return decorator


def validate_query_params(schema_class: Type[BaseModel]):
    """
    Decorator to validate query parameters against a Pydantic schema

    Usage:
        @song_bp.route("/api/songs", methods=["GET"])
        @validate_query_params(SongQueryParams)
        def get_songs(query_params: SongQueryParams):
            # query_params is now validated
            pass
    """
    return validate_json_request(schema_class, location="args")


def validate_form_data(schema_class: Type[BaseModel]):
    """
    Decorator to validate form data against a Pydantic schema

    Usage:
        @song_bp.route("/api/songs", methods=["POST"])
        @validate_form_data(SongFormRequest)
        def create_song_from_form(form_data: SongFormRequest):
            # form_data is now validated
            pass
    """
    return validate_json_request(schema_class, location="form")


def validate_path_params(**param_schemas):
    """
    Decorator to validate path parameters

    Usage:
        @song_bp.route("/api/songs/<song_id>", methods=["GET"])
        @validate_path_params(song_id=str)
        def get_song(song_id: str):
            # song_id is validated as string and not empty
            pass
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Validate each path parameter
                for param_name, param_type in param_schemas.items():
                    if param_name in kwargs:
                        value = kwargs[param_name]

                        # Basic validation
                        if param_type == str and (not value or value.strip() == ""):
                            raise RequestValidationError(
                                f"Path parameter '{param_name}' cannot be empty",
                                param_name,
                                value,
                            )

                        # Type validation
                        if param_type != str:
                            try:
                                kwargs[param_name] = param_type(value)
                            except (ValueError, TypeError) as e:
                                raise RequestValidationError(
                                    f"Path parameter '{param_name}' must be of type {param_type.__name__}",
                                    param_name,
                                    value,
                                )

                return func(*args, **kwargs)

            except RequestValidationError:
                raise
            except Exception as e:
                logger.error(f"Path parameter validation error: {e}", exc_info=True)
                raise RequestValidationError(
                    "Path parameter validation failed",
                    "path_validation_error",
                    {"original_error": str(e)},
                )

        return wrapper

    return decorator
