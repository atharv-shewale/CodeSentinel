"""
CodeSentinel Requirements Test Fixtures: Sample Documents.
"""

# 1. Well-structured SRS document with explicit acceptance criteria
STRUCTURED_SRS_MARKDOWN = """# Software Requirements Specification (SRS)

## REQ-AUTH-001: User Authentication Service
The system shall provide a secure user authentication mechanism using username and hashed credentials.

### Acceptance Criteria:
1. When valid username and password hash are submitted, the system shall return a valid session token.
2. When either username or password hash is empty, the system shall return None or an HTTP 401 error.
3. The session token must expire after the configured TTL (default 3600 seconds).

## REQ-SEC-002: Password Hashing Standard
All stored passwords must be hashed using a cryptographic hash function with salt support.

### Acceptance Criteria:
* The system shall produce a deterministic salted hash when a salt string is provided.
* Password hashing must never store plain text passwords in memory or database.
"""

# 2. Loosely-written user story document with NO explicit acceptance criteria
LOOSE_USER_STORY_MARKDOWN = """# Product Backlog & Ideas

## User Story: Profile Avatar Upload
As a registered user, I would like to upload a custom profile picture so that other users can recognize me.
We should probably support JPEG and PNG and maybe crop it to a square.

## User Story: Dark Mode Theme
As a developer using the platform at night, I want a dark mode theme to reduce eye strain.
It would be cool to use OLED black colors and auto-detect system preferences.
"""

# 3. Deliberately ambiguous prose document (vague notes, no headers, no criteria)
AMBIGUOUS_PROSE_DOCUMENT = """
Notes from the stakeholder brainstorming session on Tuesday:
We were talking about maybe adding some sort of notification system or email alerts whenever
something happens. Users might want alerts on critical events, but we haven't decided what counts
as critical yet. Bob suggested SMS, Alice thought webhook was better. Let's revisit next quarter.
"""
