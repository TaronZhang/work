from __future__ import annotations

"""Document management API routes."""

import os
import uuid
from datetime import datetime, timezone

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.database import get_db
from app.db.models import Document, Project
from app.services.parser import parse_file
from app.services.file_service import generate_markdown_summary

router = APIRouter(prefix="/api/documents", tags=["documents"])


class ProjectResponse(BaseModel):
    id: int
    project_name: Optional[str]
    bidder_name: Optional[str]
    submission_deadline: Optional[str]
    source_file_name: str
    source_format: str
    total_chars: int
    status: str
    created_at: str

    class Config:
        from_attributes = True


class ProjectDetailResponse(BaseModel):
    project: dict
    documents: list
    tech_sections: Optional[str]


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a bid document (PDF/DOCX), parse it, and create a project record."""
    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".pdf", ".docx"):
        raise HTTPException(400, f"不支持的文件格式: {ext}，仅支持 PDF/DOCX")

    # Check size
    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"文件过大，最大 {settings.max_upload_size_mb}MB")

    # Save file
    file_id = uuid.uuid4().hex[:12]
    save_name = f"{file_id}{ext}"
    save_path = os.path.join(settings.upload_dir, save_name)
    with open(save_path, "wb") as f:
        f.write(content)

    # Parse
    try:
        parsed = parse_file(save_path, file.filename)
    except Exception as e:
        raise HTTPException(500, f"文档解析失败: {str(e)}")

    # Create project record
    project = Project(
        source_file_name=file.filename or "unknown",
        source_file_path=save_path,
        source_format=ext.lstrip("."),
        total_chars=len(parsed.full_text),
        raw_text=parsed.full_text,
        status="imported",
    )
    db.add(project)
    await db.flush()

    return {
        "id": project.id,
        "source_file_name": project.source_file_name,
        "source_format": project.source_format,
        "total_chars": project.total_chars,
        "status": project.status,
        "message": "上传成功，文档已解析",
    }


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all imported projects, newest first."""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()
    return {
        "projects": [
            {
                "id": p.id,
                "project_name": p.project_name,
                "bidder_name": p.bidder_name,
                "submission_deadline": (
                    p.submission_deadline.isoformat() if p.submission_deadline else None
                ),
                "source_file_name": p.source_file_name,
                "source_format": p.source_format,
                "total_chars": p.total_chars,
                "status": p.status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]
    }


@router.get("/{project_id}")
async def get_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Get project details including documents and tech sections."""
    result = await db.execute(
        select(Project).where(Project.id == project_id).options(
            selectinload(Project.documents)
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    return {
        "project": {
            "id": project.id,
            "project_name": project.project_name,
            "bidder_name": project.bidder_name,
            "submission_deadline": (
                project.submission_deadline.isoformat() if project.submission_deadline else None
            ),
            "source_file_name": project.source_file_name,
            "source_format": project.source_format,
            "total_chars": project.total_chars,
            "status": project.status,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        },
        "documents": [
            {
                "id": d.id,
                "doc_type": d.doc_type,
                "file_name": d.file_name,
                "file_path": d.file_path,
                "file_size": d.file_size,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in project.documents
        ],
    }


@router.delete("/{project_id}")
async def delete_project(project_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a project and its associated files."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    # Delete uploaded file
    if project.source_file_path and os.path.exists(project.source_file_path):
        try:
            os.remove(project.source_file_path)
        except OSError:
            pass

    # Delete generated documents
    for doc in project.documents:
        if doc.file_path and os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

    await db.delete(project)
    return {"message": "已删除"}


@router.get("/{document_id}/download")
async def download_document(document_id: int, db: AsyncSession = Depends(get_db)):
    """Download a generated document file."""
    from fastapi.responses import FileResponse

    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "文件不存在")
    if not os.path.exists(doc.file_path):
        raise HTTPException(404, "文件已被删除")

    return FileResponse(
        doc.file_path,
        filename=doc.file_name,
        media_type="application/octet-stream",
    )
