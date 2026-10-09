# CSS Selectors for Job Boards (e.g. LinkedIn)
# Note: Selectors may change when platforms update their DOM structure.

LINKEDIN_SELECTORS = {
    "job_card": ".job-search-card, .base-search-card, .jobs-search__results-list li",
    "title": ".base-search-card__title, .job-card-list__title, h3.base-search-card__title",
    "company": ".base-search-card__subtitle, .job-card-container__company-name",
    "location": ".job-search-card__location, .job-card-container__metadata-item",
    "link": ".base-card__full-link, .job-card-list__title, a.job-card-container__link",
    "description": ".show-more-less-html__markup, .jobs-description__content, .job-details__content"
}
