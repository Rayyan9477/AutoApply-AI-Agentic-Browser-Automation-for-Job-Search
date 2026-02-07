import os
import json
import streamlit as st

st.set_page_config(page_title="AutoApply AI", page_icon="🤖", layout="wide")

st.title("AutoApply AI - Smart Job Application Assistant")

st.sidebar.header("Configuration")
provider = st.sidebar.selectbox(
    "LLM Provider",
    options=["auto", "openai", "groq", "openrouter", "github", "gemini", "local"],
    index=0,
)

api_key = st.sidebar.text_input("API Key (matches provider)", type="password")
env_map = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "github": "GITHUB_TOKEN",
    "gemini": "GEMINI_API_KEY",
}
if provider in env_map and api_key:
    os.environ[env_map[provider]] = api_key

st.sidebar.caption("Change provider and paste its key to switch instantly.")

st.header("Search Jobs")
col1, col2 = st.columns(2)
with col1:
    keywords = st.text_input("Keywords (comma-separated)", value="python, software engineer")
with col2:
    location = st.text_input("Location", value="Remote")

use_linkedin = st.checkbox("Use LinkedIn", value=True)
use_browser = st.checkbox("Use Browser Automation", value=False)
job_site = st.selectbox("Job Site", options=["linkedin", "indeed", "glassdoor"], index=0)

if st.button("Search"):
    from job_application_automation.src.main import JobApplicationAutomation
    import asyncio

    async def run():
        automation = JobApplicationAutomation()
        await automation.setup()
        jobs = await automation.search_jobs(
            keywords=[k.strip() for k in keywords.split(",") if k.strip()],
            location=location,
            use_linkedin=use_linkedin,
            use_browser=use_browser,
            job_site=job_site,
        )
        return jobs

    jobs = asyncio.run(run())
    st.success(f"Found {len(jobs)} jobs")
    st.dataframe(jobs[:50])

st.header("Generate Resume & Cover Letter")
job_desc = st.text_area("Job Description")
candidate_json = st.text_area("Candidate Profile (JSON)", value=json.dumps({
    "name": "Your Name",
    "email": "you@example.com",
    "summary": "Experienced professional...",
    "skills": ["Python", "SQL", "AWS"],
}, indent=2))

if st.button("Generate Documents"):
    try:
        profile = json.loads(candidate_json)
    except Exception as e:
        st.error(f"Invalid JSON: {e}")
        profile = None

    if profile and job_desc.strip():
        from job_application_automation.src.resume_cover_letter_generator import ResumeGenerator

        gen = ResumeGenerator()
        resume_path, resume_content = gen.generate_resume(job_description=job_desc, candidate_profile=profile)
        cover_path, _ = gen.generate_cover_letter(job_description=job_desc, candidate_resume=resume_content, company_info="")

        st.success("Documents generated")
        st.write("Resume:", resume_path)
        st.write("Cover letter:", cover_path)

st.markdown("---")
st.caption("AutoApply AI - switch providers by setting the corresponding API key in the sidebar.")


