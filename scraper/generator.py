import os
import json
import logging
from scraper.ai_client import gemini_client

logger = logging.getLogger(__name__)

PROFILE_PATH = "profile/profile.json"

def load_profile():
    if not os.path.exists(PROFILE_PATH):
        return {}
    with open(PROFILE_PATH, "r") as f:
        return json.load(f)

def generate_outreach_email(job_or_post, profile):
    """
    Uses Gemini 1.5 Flash via the multi-key manager to generate a professional outreach message.
    """
    try:
        prompt = f"""
Candidate Profile:
{json.dumps(profile, indent=2)}

Job / Post Details:
Title/Content: {job_or_post.get('title', job_or_post.get('text', ''))}
Company: {job_or_post.get('company', 'Hiring Company')}
Description: {job_or_post.get('description', job_or_post.get('full_text', ''))}

You are writing a professional, concise outreach message to a recruiter or engineering manager who posted about a role. Highlight relevant automation experience (Playwright, TypeScript). Keep it under 100 words.
Return JSON ONLY with:
- subject
- body
"""
        response = gemini_client.generate_content_with_retry(prompt)
        content = response.text.strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")

        result = json.loads(content)
        return result.get("subject", "Opportunity Inquiry"), result.get("body", "Hi, interested in your role.")
    except Exception as e:
        logger.error(f"Gemini email generation failed: {e}")
        return "Automation Engineering Role Inquiry", f"Hi,\n\nI am interested in your open role. I bring strong Playwright and TypeScript expertise.\n\nBest,\n{profile.get('name', 'Candidate')}"
