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
from app.logger import log_error
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
    try:
        meta = await extract_metadata(
            doc_text=project.raw_text,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    except Exception as e:
        log_error("extraction.metadata", str(e), {"project_id": req.project_id})
        raise HTTPException(500, f"LLM 提取失败: {str(e)}")

    # Update project
    project.project_name = meta.project_name or project.project_name
    project.bidder_name = meta.bidder_name or project.bidder_name
    project.submission_deadline = meta.submission_deadline
    project.bid_obtain_deadline = meta.bid_obtain_deadline
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
    if not req.project_id or req.project_id <= 0:
        raise HTTPException(400, "无效的项目 ID")

    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")
    if not project.project_name:
        raise HTTPException(400, "请先提取元数据（项目名称不能为空）")

    try:
        filepath = generate_markdown_summary(
            project_name=project.project_name,
            bidder_name=project.bidder_name or "",
            deadline=project.submission_deadline,
            source_filename=project.source_file_name,
        )
    except Exception as e:
        raise HTTPException(500, f"Markdown 生成失败: {str(e)}")

    if not os.path.exists(filepath):
        raise HTTPException(500, "文件生成失败，请检查磁盘空间和目录权限")

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
    """Generate point-by-point technical deviation table Excel.

    Integration with full techtoexcel pipeline:
    1. Identify tech sections via LLM → get chapter name
    2. If source is .docx: extract chapter paragraphs/tables → LLM split entries
       → clean_resp → write_excel (professional 4-column format)
    3. If source is .pdf: use text-based generation as fallback
    """
    result = await db.execute(select(Project).where(Project.id == req.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "项目不存在")

    if not project.raw_text:
        raise HTTPException(400, "文档尚未解析，请重新上传")

    if not settings.llm_api_key:
        raise HTTPException(400, "请先配置 LLM API Key")

    # Step 1: Identify tech sections to get chapter name
    try:
        tech_result = await identify_tech_sections(
            doc_text=project.raw_text,
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )
    except Exception as e:
        raise HTTPException(500, f"技术要求识别失败: {str(e)}")

    if not tech_result.has_tech_content:
        raise HTTPException(400, "未识别到技术要求内容")

    # Get chapter name from first identified section
    chapter_name = ""
    if tech_result.sections:
        chapter_name = tech_result.sections[0].title

    # Step 2: Try full techtoexcel pipeline (only for .docx source)
    pipeline_result = None
    if project.source_format == "docx" and os.path.exists(project.source_file_path):
        from app.services.techtoexcel_bridge import run_techtoexcel_pipeline

        pipeline_result = await run_techtoexcel_pipeline(
            source_docx_path=project.source_file_path,
            chapter_name=chapter_name or "采购需求",
            output_dir=settings.export_dir,
            project_name=project.project_name or "项目",
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    # Step 3: Fall back to text-based generation
    if pipeline_result is None or not pipeline_result.success:
        if pipeline_result and pipeline_result.error:
            # Log the error but continue with fallback
            pass

        tech_text = tech_result.combined_text
        filepath = generate_tech_excel(tech_text, project.project_name or "项目")
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        entry_count = 0
        issues = []
    else:
        filepath = pipeline_result.filepath
        filename = pipeline_result.filename
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        entry_count = pipeline_result.entry_count
        issues = pipeline_result.issues

    # Save document record
    doc = Document(
        project_id=project.id,
        doc_type="excel",
        file_name=filename,
        file_path=filepath,
        file_size=file_size,
    )
    db.add(doc)
    await db.flush()

    return {
        "file_name": filename,
        "file_path": filepath,
        "file_size": file_size,
        "entry_count": entry_count,
        "issues": issues,
        "method": "techtoexcel" if pipeline_result and pipeline_result.success else "fallback",
    }
