from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio

from job_application_automation.src.main import JobApplicationAutomation
from job_application_automation.src.resume_cover_letter_generator import ResumeGenerator


def create_app() -> FastAPI:
    app = FastAPI(title="AutoApply AI API", version="0.1.0")

    class SearchRequest(BaseModel):
        keywords: List[str]
        location: str = "Remote"
        use_linkedin: bool = True
        use_browser: bool = True
        job_site: str = "linkedin"

    class GenerateRequest(BaseModel):
        job_description: str
        candidate_profile: Dict[str, Any]

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok"}

    @app.post("/search")
    async def search(req: SearchRequest) -> Dict[str, Any]:
        automation = JobApplicationAutomation()
        await automation.setup()
        jobs = await automation.search_jobs(
            keywords=req.keywords,
            location=req.location,
            use_linkedin=req.use_linkedin,
            use_browser=req.use_browser,
            job_site=req.job_site,
        )
        return {"count": len(jobs), "jobs": jobs[:50]}

    @app.post("/generate")
    async def generate(req: GenerateRequest) -> Dict[str, Any]:
        gen = ResumeGenerator()
        resume_path, resume_content = gen.generate_resume(req.job_description, req.candidate_profile)
        cover_path, _ = gen.generate_cover_letter(req.job_description, resume_content, "")
        return {"resume_path": resume_path, "cover_letter_path": cover_path}

    return app


