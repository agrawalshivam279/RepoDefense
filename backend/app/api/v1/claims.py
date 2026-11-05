"""FastAPI router for technical claim extraction from resumes and verification against code."""

import uuid
from typing import Annotated, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.claim_extractor import (
    extract_technical_claims,
    extract_text_from_pdf,
)
from app.ai.claim_verifier import verify_claims_batch
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.project import Project, User
from app.schemas.claim import (
    ClaimExtractionRequest,
    ClaimExtractionResponse,
)
from app.schemas.claim_verification import (
    BatchClaimVerificationResponse,
    ClaimVerificationRequest,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims"])
project_claims_router = APIRouter(prefix="/projects", tags=["Claims"])

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


async def _handle_claim_verification(
    project_id: uuid.UUID,
    request: ClaimVerificationRequest,
    current_user: User,
    db: AsyncSession,
) -> BatchClaimVerificationResponse:
    """Common handler to verify claims against an authenticated user's repository."""
    stmt = select(Project).where(
        Project.id == project_id,
        Project.user_id == current_user.id,
    )
    project = (await db.execute(stmt)).scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    if project.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot verify claims against a failed repository snapshot.",
        )

    try:
        return await verify_claims_batch(
            session=db,
            project_id=project_id,
            claims=request.claims,
            top_k=request.top_k_chunks,
            min_similarity=request.min_similarity_threshold,
        )
    except Exception as exc:
        logger.error("claim_verification_failed", project_id=str(project_id), error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify candidate claims.",
        ) from exc


@router.post(
    "/verify/{project_id}",
    response_model=BatchClaimVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify technical claims against codebase evidence for a project",
)
@router.post(
    "/{project_id}/verify",
    response_model=BatchClaimVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify technical claims against codebase evidence for a project",
)
async def verify_claims_endpoint(
    project_id: uuid.UUID,
    request: ClaimVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BatchClaimVerificationResponse:
    """Verifies a list of technical claims against an analyzed repository snapshot."""
    return await _handle_claim_verification(project_id, request, current_user, db)


@project_claims_router.post(
    "/{project_id}/claims/verify",
    response_model=BatchClaimVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify technical claims against codebase evidence (project path)",
)
async def verify_project_claims_alias(
    project_id: uuid.UUID,
    request: ClaimVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BatchClaimVerificationResponse:
    """Alias endpoint supporting POST /api/v1/projects/{project_id}/claims/verify."""
    return await _handle_claim_verification(project_id, request, current_user, db)
