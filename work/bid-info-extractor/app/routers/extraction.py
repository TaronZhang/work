from __future__ import annotations

"""Extraction API routes — metadata, technical sections, Excel generation."""

import json
import os

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import Document, Project
from app.services.file_service import generate_markdown_summary, generate_tech_excel
from app.services.metadata_extractor import extract_metadata
from app.services.section_identifier import identify_tech_sections

router = APIRouter(prefix="/api/extraction", tags=["extraction"])


class ExtractRequest(BaseModel):
    project_id: int


class MetadataResponse(BaseModel):
    project_name: str
    bidder_name: str
    submission_deadline: Optional[str]
    deadline_found: bool
    confidence: str


@router.post("/metadata", response_model=MetadataResponse)
async def extract_project_metadata(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Extract project name, bidder name, and deadline using LLM."""
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.raw_text:
        raise HTTPException(400, "文档尚未解析，请先上传")

    if not settings.llm_api_key:
        raise HTTPException(400, "请先在设置中配置 LLM API Key")

    # Call LLM
    meta = await extract_metadata(
        doc_text=project.raw_text,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    # Update project
    project.project_name = meta.project_name or project.project_name
    project.bidder_name = meta.bidder_name or project.bidder_name
    project.submission_deadline = meta.submission_deadline
    project.status = "extracted"
    await db.flush()

    return MetadataResponse(
        project_name=meta.project_name,
        bidder_name=meta.bidder_name,
        submission_deadline=(
            meta.submission_deadline.isoformat() if meta.submission_deadline else None
        ),
        deadline_found=meta.deadline_found,
        confidence=meta.confidence,
    )


@router.post("/tech-sections")
async def extract_tech_sections(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Identify technical requirement sections in the document."""
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.raw_text:
        raise HTTPException(400, "文档尚未解析")

    if not settings.llm_api_key:
        raise HTTPException(400, "请先在设置中配置 LLM API Key")

    tech_result = await identify_tech_sections(
        doc_text=project.raw_text,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    sections_data = [
        {"title": s.title, "content": s.content}
        for s in tech_result.sections
    ]

    return {
        "sections": sections_data,
        "combined_text": tech_result.combined_text,
        "total_chars": tech_result.total_chars,
        "has_tech_content": tech_result.has_tech_content,
    }


@router.post("/generate-markdown")
async def generate_markdown(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate the summary markdown file."""
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.project_name:
        raise HTTPException(400, "请先提取元数据")

    filepath = generate_markdown_summary(
        project_name=project.project_name,
        bidder_name=project.bidder_name or "",
        deadline=project.submission_deadline,
        source_filename=project.source_file_name,
    )

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)

    doc = Document(
        project_id=project.id,
        doc_type="markdown",
        file_name=filename,
        file_path=filepath,
        file_size=file_size,
    )
    db.add(doc)
    project.status = "completed"
    await db.flush()

    return {"file_name": filename, "file_path": filepath, "file_size": file_size}


@router.post("/generate-excel")
async def generate_excel(
    req: ExtractRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate point-by-point response Excel.
    Uses external techtoexcel script if configured, otherwise generates basic template.
    """
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    # First, get tech sections text
    if not settings.llm_api_key:
        raise HTTPException(400, "请先配置 LLM API Key")

    tech_result = await identify_tech_sections(
        doc_text=project.raw_text,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    tech_text = tech_result.combined_text
    if not tech_text:
        raise HTTPException(400, "未识别到技术要求内容")

    # Try external techtoexcel script first
    if settings.techtoexcel_path:
        filepath = await _call_techtoexcel_script(tech_text, project.project_name or "项目")
    else:
        filepath = generate_tech_excel(tech_text, project.project_name or "项目")

    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

    doc = Document(
        project_id=project.id,
        doc_type="excel",
        file_name=filename,
        file_path=filepath,
        file_size=file_size,
    )
    db.add(doc)
    await db.flush()

    return {"file_name": filename, "file_path": filepath, "file_size": file_size}


async def _call_techtoexcel_script(tech_text: str, project_name: str) -> str:
    """Call external techtoexcel script via subprocess."""
    import asyncio.subprocess
    import shlex

    script_path = settings.techtoexcel_path
    output_path = os.path.join(
        settings.export_dir,
        f"{project_name}_技术应答.xlsx",
    )

    # Strategy: write tech_text to temp file, pass to script
    temp_path = os.path.join(settings.upload_dir, "_tech_input.txt")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(tech_text)

    extra_args = shlex.split(settings.techtoexcel_args) if settings.techtoexcel_args else []

    try:
        proc = await asyncio.subprocess.create_subprocess_exec(
            "python3",
            script_path,
            "--input", temp_path,
            "--output", output_path,
            *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err_msg = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"techtoexcel 执行失败 (exit {proc.returncode}): {err_msg}")

    except FileNotFoundError:
        # Script not found, fall back to built-in generator
        return generate_tech_excel(tech_text, project_name)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return output_path
