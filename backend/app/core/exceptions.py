import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import request_id_ctx

logger = logging.getLogger("app.error")


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def install_exception_handlers(app: FastAPI) -> None:
    def error_response(status_code: int, code: str, message: str, details: list | dict | str | None = None) -> JSONResponse:
        request_id = request_id_ctx.get()
        payload = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            },
        }
        response = JSONResponse(status_code=status_code, content=payload)
        if request_id:
            response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            exc.errors(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error")
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "database_error",
            "Database operation failed. Please contact support with the request ID.",
            str(exc.__class__.__name__),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error")
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "server_error",
            "Unexpected server error. Please contact support with the request ID.",
            str(exc.__class__.__name__),
        )
