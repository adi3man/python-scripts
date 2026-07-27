#!/usr/bin/env python3
"""
ATS Resume Checker
==================

Checks a resume (PDF) against common Applicant Tracking System (ATS)
best practices, gives a 1-10 quality rating, and lists concrete
improvement suggestions.

Usage:
    python resumechecker.py resume.pdf
"""

import sys
import os
import re

try:
    import pdfplumber
except ImportError:
    print("Missing dependency 'pdfplumber'. Install it with:")
    print("    pip install pdfplumber")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

SECTION_KEYWORDS = {
    "contact": ["email", "phone", "linkedin", "@"],
    "summary": ["summary", "profile", "objective", "about me"],
    "experience": ["experience", "work history", "employment"],
    "education": ["education", "university", "degree", "diploma"],
    "skills": ["skills", "technical skills", "competencies"],
}

ACTION_VERBS = [
    "managed", "led", "developed", "created", "designed", "implemented",
    "improved", "increased", "decreased", "reduced", "built", "launched",
    "coordinated", "analyzed", "optimized", "achieved", "delivered",
    "streamlined", "automated", "resolved", "supervised", "trained",
    "negotiated", "generated", "maintained", "administered", "configured",
]

WEAK_PHRASES = [
    "responsible for", "duties included", "worked on", "helped with",
    "in charge of", "team player", "hard worker", "detail oriented",
    "go-getter", "results-driven", "think outside the box",
]

DATE_PATTERN = re.compile(
    r"(0?[1-9]|1[0-2])[/\-.](19|20)\d{2}|"
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|"
    r"(19|20)\d{2}\s*(-|to|–)\s*(present|current|(19|20)\d{2})",
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(r"[\w.\-+]+@[\w\-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
BULLET_PATTERN = re.compile(r"^[•\-\*\u2022\u25CF\u2013]\s+", re.MULTILINE)


# ---------------------------------------------------------------------------
# PDF extraction and structural checks
# ---------------------------------------------------------------------------

def extract_pdf_data(path):
    """Extract text plus structural signals (tables, images, columns, fonts)."""
    data = {
        "text": "",
        "page_count": 0,
        "has_tables": False,
        "has_images": False,
        "fonts": set(),
        "font_sizes": set(),
        "multi_column_pages": 0,
    }

    with pdfplumber.open(path) as pdf:
        data["page_count"] = len(pdf.pages)

        for page in pdf.pages:
            page_text = page.extract_text() or ""
            data["text"] += page_text + "\n"

            if page.find_tables():
                data["has_tables"] = True

            if page.images:
                data["has_images"] = True

            for ch in page.chars:
                data["fonts"].add(ch.get("fontname", "unknown"))
                data["font_sizes"].add(round(ch.get("size", 0), 1))

            # crude multi-column detection: check word x-positions cluster
            words = page.extract_words()
            if words:
                mid = page.width / 2
                left = sum(1 for w in words if w["x0"] < mid - 20)
                right = sum(1 for w in words if w["x0"] > mid + 20)
                if left > 5 and right > 5:
                    data["multi_column_pages"] += 1

    return data


# ---------------------------------------------------------------------------
# Scoring checks
# ---------------------------------------------------------------------------

def check_contact_info(text):
    issues = []
    points = 0
    if EMAIL_PATTERN.search(text):
        points += 1
    else:
        issues.append("No email address detected. Add a professional email near the top.")
    if PHONE_PATTERN.search(text):
        points += 1
    else:
        issues.append("No phone number detected. Include a reachable phone number.")
    return points, issues


def check_sections(text):
    lower = text.lower()
    found = {}
    missing = []
    for section, keywords in SECTION_KEYWORDS.items():
        found[section] = any(kw in lower for kw in keywords)
        if not found[section]:
            missing.append(section)
    return found, missing


def check_action_verbs(text):
    lower = text.lower()
    hits = sum(1 for v in ACTION_VERBS if re.search(r"\b" + v + r"\b", lower))
    return hits


def check_weak_phrases(text):
    lower = text.lower()
    hits = [p for p in WEAK_PHRASES if p in lower]
    return hits


def check_quantified_achievements(text):
    # numbers, percentages, currency as a proxy for measurable impact
    matches = re.findall(r"\b\d+%|\$\s?\d+|\b\d{2,}\b", text)
    return len(matches)


def check_dates(text):
    return len(DATE_PATTERN.findall(text))


def check_bullets(text):
    return len(BULLET_PATTERN.findall(text))


def check_length(text, page_count):
    words = len(text.split())
    return words, page_count


def check_formatting(pdf_data):
    issues = []
    if pdf_data["has_tables"]:
        issues.append(
            "Tables detected. Many ATS parsers misread table layouts; "
            "use plain text sections and bullet points instead."
        )
    if pdf_data["multi_column_pages"] > 0:
        issues.append(
            "Multi-column layout detected on at least one page. ATS often reads "
            "columns left-to-right across the whole line, scrambling content. "
            "Use a single-column layout."
        )
    if pdf_data["has_images"]:
        issues.append(
            "Images/graphics detected (e.g. a photo, icons, or a logo). ATS cannot "
            "read text embedded in images and photos can trigger bias filters. "
            "Remove them."
        )
    if len(pdf_data["fonts"]) > 3:
        issues.append(
            f"{len(pdf_data['fonts'])} different fonts detected. Stick to 1-2 fonts "
            "for consistency and easier parsing."
        )
    if pdf_data["page_count"] > 2:
        issues.append(
            f"Resume is {pdf_data['page_count']} pages long. Most ATS and recruiters "
            "prefer 1 page (entry/mid-level) or 2 pages (senior/extensive experience)."
        )
    return issues


# ---------------------------------------------------------------------------
# Scoring model
# ---------------------------------------------------------------------------

def score_resume(text, pdf_data):
    """
    Returns (score_out_of_10, breakdown_dict, suggestions_list)
    """
    suggestions = []
    score = 0.0
    max_score = 10.0

    # 1. Contact info (1 point)
    contact_points, contact_issues = check_contact_info(text)
    score += contact_points * 0.5
    suggestions.extend(contact_issues)

    # 2. Core sections present (2 points)
    found_sections, missing_sections = check_sections(text)
    section_score = (len(SECTION_KEYWORDS) - len(missing_sections)) / len(SECTION_KEYWORDS) * 2
    score += section_score
    for m in missing_sections:
        suggestions.append(f"Missing or unclear '{m.title()}' section. Add a clearly labeled section for it.")

    # 3. Action verbs (1.5 points)
    verb_hits = check_action_verbs(text)
    if verb_hits >= 10:
        score += 1.5
    elif verb_hits >= 5:
        score += 1.0
        suggestions.append("Use more strong action verbs (e.g. 'led', 'built', 'optimized') to start bullet points.")
    else:
        score += 0.3
        suggestions.append(
            "Very few action verbs found. Rewrite bullet points to start with strong action verbs "
            "instead of passive phrases."
        )

    # 4. Weak phrases penalty (up to -1)
    weak_hits = check_weak_phrases(text)
    if weak_hits:
        score -= min(1.0, 0.25 * len(weak_hits))
        suggestions.append(
            "Replace generic/weak phrases such as "
            + ", ".join(f"'{w}'" for w in weak_hits[:5])
            + " with specific, measurable statements."
        )

    # 5. Quantified achievements (1.5 points)
    quant_hits = check_quantified_achievements(text)
    if quant_hits >= 8:
        score += 1.5
    elif quant_hits >= 3:
        score += 1.0
        suggestions.append("Add more numbers/metrics (%, amounts, counts) to quantify your achievements.")
    else:
        score += 0.2
        suggestions.append(
            "Almost no quantified results found. Add measurable outcomes, e.g. "
            "'reduced ticket resolution time by 30%' instead of 'improved support process'."
        )

    # 6. Dates present (1 point)
    date_hits = check_dates(text)
    if date_hits >= 2:
        score += 1.0
    else:
        suggestions.append("Add clear employment/education date ranges (e.g. 'Jan 2022 - Present') for each entry.")

    # 7. Bullet point usage (1 point)
    bullet_hits = check_bullets(text)
    if bullet_hits >= 5:
        score += 1.0
    else:
        score += 0.3
        suggestions.append("Use bullet points for experience details instead of long paragraphs.")

    # 8. Length (1 point)
    word_count, page_count = check_length(text, pdf_data["page_count"])
    if 300 <= word_count <= 800 and page_count <= 2:
        score += 1.0
    elif word_count < 200:
        score += 0.3
        suggestions.append("Resume content looks too short. Add more detail about your experience and impact.")
    elif word_count > 1000:
        score += 0.5
        suggestions.append("Resume content looks too long/dense. Trim to the most relevant, recent, and impactful points.")
    else:
        score += 0.7

    # 9. Formatting / ATS-parseability (1 point, deducted per issue)
    formatting_issues = check_formatting(pdf_data)
    format_score = max(0, 1.0 - 0.3 * len(formatting_issues))
    score += format_score
    suggestions.extend(formatting_issues)

    score = max(0.0, min(max_score, round(score, 1)))

    breakdown = {
        "Contact info": f"{contact_points}/2 fields found",
        "Core sections found": f"{len(SECTION_KEYWORDS) - len(missing_sections)}/{len(SECTION_KEYWORDS)}",
        "Action verbs used": verb_hits,
        "Weak phrases found": len(weak_hits),
        "Quantified results": quant_hits,
        "Date entries found": date_hits,
        "Bullet points found": bullet_hits,
        "Word count": word_count,
        "Page count": page_count,
        "Formatting issues": len(formatting_issues),
    }

    return score, breakdown, suggestions


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def rating_label(score):
    if score >= 9:
        return "Excellent - highly ATS-friendly"
    if score >= 7:
        return "Good - minor improvements needed"
    if score >= 5:
        return "Fair - noticeable gaps to fix"
    if score >= 3:
        return "Weak - significant revision needed"
    return "Poor - resume needs a major rewrite"


def print_report(path, score, breakdown, suggestions):
    line = "=" * 60
    print(line)
    print("ATS RESUME QUALITY REPORT")
    print(line)
    print(f"File: {path}")
    print()
    print(f"Overall Rating: {score}/10  -  {rating_label(score)}")
    print()
    print("-" * 60)
    print("BREAKDOWN")
    print("-" * 60)
    for key, value in breakdown.items():
        print(f"  {key:<28}: {value}")
    print()
    print("-" * 60)
    print("SUGGESTIONS FOR IMPROVEMENT")
    print("-" * 60)
    if suggestions:
        for i, s in enumerate(suggestions, 1):
            print(f"  {i}. {s}")
    else:
        print("  No major issues found. Great work.")
    print()
    print(line)


def main():
    if len(sys.argv) != 2:
        print("Usage: python resumechecker.py <resume.pdf>")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.isfile(path):
        print(f"Error: file not found: {path}")
        sys.exit(1)

    if not path.lower().endswith(".pdf"):
        print("Error: only PDF files are supported.")
        sys.exit(1)

    try:
        pdf_data = extract_pdf_data(path)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)

    text = pdf_data["text"]
    if not text.strip():
        print("Error: no extractable text found in this PDF.")
        print("This resume may be a scanned image, which most ATS systems cannot read at all.")
        sys.exit(1)

    score, breakdown, suggestions = score_resume(text, pdf_data)
    print_report(path, score, breakdown, suggestions)


if __name__ == "__main__":
    main()
