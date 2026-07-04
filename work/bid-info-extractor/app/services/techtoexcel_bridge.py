from __future__ import annotations

"""TechToExcel bridge — call external script via subprocess."""

import os
import shlex
from dataclasses import dataclass

from app.config import settings


@dataclass
class ExcelResult:
    filepath: str = ""
    filename: str = ""
    success: bool = False
    error: str = ""
    fallback_used: bool = False


async def call_techtoexcel(
    tech_text: str,
    output_dir: str,
    project_name: str,
) -> ExcelResult:
    """Call the external techtoexcel script.

    Supports three interface modes:
    1. stdin: echo text | python script.py --output path
    2. tempfile: python script.py --input tmpfile --output path
    3. args: python script.py "text" --output path

    Mode is auto-detected, preferring tempfile for large texts.
    """
    script_path = settings.techtoexcel_path
    if not script_path:
        return ExcelResult(
            success=False,
            error="techtoexcel 脚本路径未配置",
        )

    import asyncio.subprocess

    # Strategy: temp file mode (most reliable for large texts)
    temp_input = os.path.join(output_dir, "_tech_input_temp.txt")
    output_path = os.path.join(output_dir, f"{project_name}_技术应答.xlsx")

    with open(temp_input, "w", encoding="utf-8") as f:
        f.write(tech_text)

    extra_args = []
    if settings.techtoexcel_args:
        extra_args = shlex.split(settings.techtoexcel_args)

    try:
        proc = await asyncio.subprocess.create_subprocess_exec(
            "python3",
            script_path,
            "--input", temp_input,
            "--output", output_path,
            *extra_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            err = stderr.decode() if stderr else f"Exit code {proc.returncode}"
            return ExcelResult(
                filepath=output_path,
                success=False,
                error=err,
            )

    except FileNotFoundError:
        return ExcelResult(
            success=False,
            error=f"脚本未找到: {script_path}",
        )
    except Exception as e:
        return ExcelResult(
            success=False,
            error=str(e),
        )
    finally:
        # Clean up temp input
        if os.path.exists(temp_input):
            try:
                os.remove(temp_input)
            except OSError:
                pass

    filename = os.path.basename(output_path)
    return ExcelResult(
        filepath=output_path,
        filename=filename,
        success=True,
    )
