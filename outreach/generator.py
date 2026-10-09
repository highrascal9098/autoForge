import json
import logging
from scraper.ai_client import gemini_client
from outreach.templates import load_profile, get_outreach_prompt

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
    except json.JSONDecodeError:
        # Try finding the first '{' and last '}'
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(content[start:end+1])
        raise

def generate_outreach_draft(job_data, profile=None):
    """
    Generates structured outreach JSON using Gemini, with robust error handling/repair.
    """
    if profile is None:
        profile = load_profile()
    prompt = get_outreach_prompt(job_data, profile)

    try:
        response = gemini_client.generate_content_with_retry(prompt)
        content = response.text.strip()
        try:
            return parse_json_safely(content)
        except Exception:
            # Simple repair attempt
            repair_prompt = f"Fix this broken JSON to match required schema:\n{content}"
            repair_resp = gemini_client.generate_content_with_retry(repair_prompt)
            return parse_json_safely(repair_resp.text.strip())
    except Exception as e:
        logger.error(f"Outreach generation failed: {e}")
        return {
            "subject": f"Inquiry regarding {job_data.get('title', 'open role')} at {job_data.get('company', 'your company')}",
            "body": "Hi,\n\nI am interested in your open role and would love to connect.\n\nBest,\nCandidate",
            "linkedin_message": "Hi, I'm interested in your open role and would love to connect.",
            "relevance_explanation": "Manual review required: automatic generation failed.",
            "followup_draft": "Hi, just checking in."
        }
