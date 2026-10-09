import os
import json
import logging
from scraper.ai_client import gemini_client

logger = logging.getLogger(__name__)

def parse_json_safely(content):
    """
    Safely parses JSON string, attempting to extract JSON block between first '{' and last '}' if needed.
    """
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as jde:
        # Try finding the first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            json_str = content[start:end+1]
            try:
                return json.loads(json_str)
            except Exception:
                raise jde
        raise jde

def semantic_extract_job(raw_payload):
    """
    Sends raw LinkedIn feed post acquisition data to Gemini for strict JSON semantic extraction matching the required schema.
    Includes robust JSON parsing with fallback and retry repair prompt for invalid escapes/malformed output.
    """
    prompt = f"""
You are an expert AI data extraction engine for a job search automation system.
Analyze the following raw LinkedIn feed post acquisition data, including post text, author info, links, and mailtos.

Raw Payload:
{json.dumps(raw_payload, indent=2)}

Extract and return valid JSON ONLY (no markdown fences, no extra text, valid JSON syntax with properly escaped backslashes if any) conforming strictly to this schema:
{{
  "source": "linkedin",
  "source_post_id": null,
  "post_url": null,
  "author_name": null,
  "author_profile_url": null,
  "posted_at": null,
  "search_keywords": null,
  "is_hiring_post": false,
  "company": null,
  "job_title": null,
  "location": null,
  "work_mode": null,
  "employment_type": null,
  "experience_requirement": null,
  "salary": null,
  "notice_period": null,
  "skills": [],
  "requirements": [],
  "recruiter_name": null,
  "recruiter_profile_url": null,
  "recruiter_email": null,
  "contact_details": [],
  "application_url": null,
  "description": null,
  "full_text": ""
}}

Rules:
- Extract information ONLY from the supplied payload.
- Never invent missing information.
- Unknown scalar values must be null.
- Unknown list values must be [].
- Preserve the original author separately from the recruiter when available.
- Do not assume the author is the hiring manager or recruiter unless the content supports it.
- Extract emails when explicitly present in the post text or supplied mailto links into contact_details and recruiter_email where appropriate.
- Extract company, job_title, location, work_mode, employment_type, experience_requirement, salary, notice_period, skills, requirements, recruiter_name, recruiter_profile_url, recruiter_email, contact_details, application_url, posted_at, description, and full_text.
- is_hiring_post should be true if the post communicates an active hiring opportunity or job opening, and false otherwise.
"""
    try:
        response = gemini_client.generate_content_with_retry(prompt)
        content = response.text.strip()
        try:
            return parse_json_safely(content)
        except Exception as json_err:
            logger.warning(f"Initial Gemini JSON parse failed ({json_err}). Attempting repair prompt...")
            repair_prompt = f"""
The previous output produced invalid JSON. Please fix the following response into strict, valid JSON ONLY matching the required schema without markdown fences or extra text:

Broken Response:
{content}

Required Schema:
{{
  "source": "linkedin",
  "source_post_id": null,
  "post_url": null,
  "author_name": null,
  "author_profile_url": null,
  "posted_at": null,
  "search_keywords": null,
  "is_hiring_post": false,
  "company": null,
  "job_title": null,
  "location": null,
  "work_mode": null,
  "employment_type": null,
  "experience_requirement": null,
  "salary": null,
  "notice_period": null,
  "skills": [],
  "requirements": [],
  "recruiter_name": null,
  "recruiter_profile_url": null,
  "recruiter_email": null,
  "contact_details": [],
  "application_url": null,
  "description": null,
  "full_text": ""
}}
"""
            repair_response = gemini_client.generate_content_with_retry(repair_prompt)
            repair_content = repair_response.text.strip()
            return parse_json_safely(repair_content)
    except Exception as e:
        logger.error(f"Gemini semantic extraction and repair failed: {e}")
        text = raw_payload.get("post_text", raw_payload.get("search_result_text", ""))
        return {
            "source": "linkedin",
            "source_post_id": raw_payload.get("source_post_id"),
            "post_url": raw_payload.get("post_url"),
            "author_name": raw_payload.get("author_name"),
            "author_profile_url": raw_payload.get("author_profile_url"),
            "posted_at": None,
            "search_keywords": raw_payload.get("search_keywords"),
            "is_hiring_post": False,
            "company": None,
            "job_title": None,
            "location": None,
            "work_mode": None,
            "employment_type": None,
            "experience_requirement": None,
            "salary": None,
            "notice_period": None,
            "skills": [],
            "requirements": [],
            "recruiter_name": None,
            "recruiter_profile_url": None,
            "recruiter_email": None,
            "contact_details": raw_payload.get("mailto_links", []),
            "application_url": None,
            "description": text[:800],
            "full_text": text
        }
