import json
import os

PROFILE_PATH = "profile/profile.json"

def load_profile():
    if not os.path.exists(PROFILE_PATH):
        return {
            "name": "Candidate",
            "title": "Professional",
            "skills": [],
            "contact": {"email": "candidate@example.com"}
        }
    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_outreach_prompt(job_data, profile):
    """
    Builds a professional, truthful prompt for Gemini supporting any job category or industry.
    """
    return f"""
You are an expert career advisory AI generating truthful, professional, and personalized outreach for a candidate.
Support any job category or industry (Engineering, Product, Marketing, Sales, Operations, Finance, Data Science, QA, etc.).

Candidate Profile:
{json.dumps(profile, indent=2)}

Job Opportunity Details:
Title: {job_data.get('title', 'Open Role')}
Company: {job_data.get('company', 'Target Company')}
Description: {job_data.get('description', job_data.get('full_text', ''))}
Requirements: {json.dumps(job_data.get('requirements', []))}
Required Skills: {json.dumps(job_data.get('skills', []))}

Rules & Constraints:
1. Never invent employment history, qualifications, certifications, achievements, or skills not present in the Candidate Profile.
2. Never claim that the candidate has already applied, spoken to someone, or received a referral unless explicitly confirmed.
3. Keep messages concise, professional, specific, and non-spammy (under 120 words).
4. Highlight genuine alignment between candidate skills and job requirements.
5. Extract or format response as valid JSON ONLY (no markdown fences, no extra text) with this exact schema:
{{
  "subject": "Email subject line",
  "body": "Professional email body addressing the hiring manager or recruiter",
  "linkedin_message": "Short, professional 300-character LinkedIn connection note or message",
  "relevance_explanation": "Brief explanation of why this candidate is a credible fit",
  "followup_draft": "Optional polite follow-up message draft for 5 days later"
}}
"""
