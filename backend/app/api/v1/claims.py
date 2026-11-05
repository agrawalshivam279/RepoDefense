"""FastAPI router for technical claim extraction from resumes and text profiles."""

from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.ai.claim_extractor import (
    extract_technical_claims,
    extract_text_from_pdf,
)
from app.schemas.claim import (
    ClaimExtractionRequest,
    ClaimExtractionResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims"])

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


@router.post(
    "/extract",
    response_model=ClaimExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract technical claims from resume text or PDF upload",
)
async def extract_claims_from_input(
    request: Optional[ClaimExtractionRequest] = None,
) -> ClaimExtractionResponse:
    """Extracts structured, verifiable technical claims from raw resume text JSON."""
    if not request or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume text payload is required.",
        )

    try:
        return await extract_technical_claims(request.text)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("claim_extraction_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract technical claims.",
        ) from exc


@router.post(
    "/upload",
    response_model=ClaimExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a PDF resume or submit form text to extract technical claims",
)
async def upload_and_extract_claims(
    file: Annotated[Optional[UploadFile], File()] = None,
    text: Annotated[Optional[str], Form()] = None,
) -> ClaimExtractionResponse:
    """Extracts technical claims from an uploaded PDF file or multipart text form."""
    extracted_text = ""

    if file:
        filename = (file.filename or "").lower()
        content_type = (file.content_type or "").lower()

        if not (filename.endswith(".pdf") or "pdf" in content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must be a PDF document (.pdf).",
            )

        content = await file.read()
        max_mb = MAX_PDF_SIZE_BYTES // (1024 * 1024)
        if len(content) > MAX_PDF_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_mb}MB.",
            )

        try:
            extracted_text = extract_text_from_pdf(content)
        except ValueError as pdf_err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(pdf_err),
            ) from pdf_err
    elif text and text.strip():
        extracted_text = text.strip()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a PDF file upload or text content must be provided.",
        )

    try:
        return await extract_technical_claims(extracted_text)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("claim_upload_endpoint_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to extract technical claims.",
        ) from exc
