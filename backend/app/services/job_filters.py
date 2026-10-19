"""Geography, work-arrangement, and employment-type filters for discovery results.

These filters run against listings returned by configured providers. They do not
expand a provider's inventory; a region can only return jobs the enabled sources expose.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from .job_sources.base import NormalizedPosting

REGIONS = {
    "global",
    "india",
    "asia",
    "europe",
    "americas",
    "middle_east",
    "africa",
    "oceania",
    "custom",
}

WORK_MODES = {"remote", "hybrid", "onsite", "unknown"}
EMPLOYMENT_TYPES = {"full_time", "part_time", "contract_freelance", "internship", "temporary", "unknown"}

# City, state, and country aliases let India-wide filtering include common city-only
# listings that do not explicitly append the country name. This is intentionally a
# useful practical list, not an assertion that every city can be recognized by name.
_REGION_TERMS = {
    "india": {
        "india", "indian", "new delhi", "delhi", "ncr", "gurugram", "gurgaon", "noida", "greater noida",
        "faridabad", "ghaziabad", "mumbai", "bombay", "bengaluru", "bangalore", "hyderabad", "pune",
        "chennai", "madras", "kolkata", "calcutta", "ahmedabad", "jaipur", "indore", "bhopal", "kochi",
        "cochin", "thiruvananthapuram", "trivandrum", "lucknow", "kanpur", "patna", "ranchi", "bhubaneswar",
        "chandigarh", "ludhiana", "amritsar", "surat", "vadodara", "baroda", "nagpur", "nashik", "agra",
        "meerut", "dehradun", "jabalpur", "sagar", "khandwa", "damoh", "raipur", "jodhpur", "udaipur",
        "mysuru", "mysore", "mangalore", "mangaluru", "visakhapatnam", "vizag", "vijayawada", "tiruchirappalli",
        "trichy", "madurai", "salem", "vellore", "warangal", "guwahati", "jammu", "srinagar", "shimla",
        "manali", "panaji", "goa", "meghalaya", "assam", "andhra pradesh", "arunachal pradesh", "bihar",
        "chhattisgarh", "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
        "madhya pradesh", "maharashtra", "manipur", "mizoram", "nagaland", "odisha", "orissa", "punjab",
        "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
        "andaman", "ladakh", "puducherry", "pondicherry", "remote, india", "india remote", "remote - india",
    },
    "asia": {
        "asia", "apac", "asia pacific", "india", "china", "hong kong", "japan", "south korea", "korea",
        "singapore", "malaysia", "indonesia", "philippines", "thailand", "vietnam", "taiwan", "bangladesh",
        "pakistan", "sri lanka", "nepal", "bhutan", "maldives", "mongolia", "cambodia", "laos", "myanmar",
        "brunei", "kazakhstan", "uzbekistan", "kyrgyzstan", "tajikistan", "turkmenistan", "afghanistan",
        "sydney", "tokyo", "seoul", "shanghai", "beijing", "shenzhen", "hong kong", "manila", "jakarta",
        "kuala lumpur", "bangkok", "hanoi", "ho chi minh", "taipei", "mumbai", "delhi", "bengaluru", "bangalore",
        "hyderabad", "pune", "chennai", "kolkata", "gurugram", "gurgaon", "noida", "remote, apac", "apac remote",
    },
    "europe": {
        "europe", "europa", "united kingdom", "uk", "england", "scotland", "wales", "ireland", "france", "germany",
        "spain", "portugal", "italy", "netherlands", "holland", "belgium", "luxembourg", "switzerland", "austria",
        "poland", "czech republic", "czechia", "slovakia", "hungary", "romania", "bulgaria", "greece", "croatia",
        "slovenia", "serbia", "bosnia", "montenegro", "albania", "north macedonia", "kosovo", "norway", "sweden",
        "finland", "denmark", "iceland", "estonia", "latvia", "lithuania", "ukraine", "moldova", "belarus", "malta",
        "cyprus", "london", "manchester", "birmingham", "edinburgh", "dublin", "paris", "berlin", "munich", "hamburg",
        "frankfurt", "amsterdam", "rotterdam", "brussels", "zurich", "geneva", "vienna", "warsaw", "krakow", "prague",
        "barcelona", "madrid", "lisbon", "rome", "milan", "stockholm", "oslo", "copenhagen", "helsinki", "remote, europe",
    },
    "americas": {
        "americas", "north america", "south america", "central america", "united states", "usa", "us", "u s", "u s a", "u s remote", "u.s.a", "us remote",
        "canada", "mexico", "brazil", "argentina", "chile", "colombia", "peru", "ecuador", "uruguay", "paraguay",
        "bolivia", "venezuela", "costa rica", "panama", "guatemala", "honduras", "el salvador", "nicaragua", "belize",
        "dominican republic", "puerto rico", "jamaica", "trinidad", "barbados", "new york", "san francisco", "los angeles",
        "seattle", "austin", "chicago", "boston", "atlanta", "miami", "denver", "dallas", "houston", "toronto", "vancouver",
        "montreal", "ottawa", "calgary", "sao paulo", "rio de janeiro", "buenos aires", "bogota", "santiago", "remote, americas",
    },
    "middle_east": {
        "middle east", "mena", "united arab emirates", "uae", "dubai", "abu dhabi", "saudi arabia", "riyadh", "jeddah",
        "qatar", "doha", "kuwait", "kuwait city", "bahrain", "manama", "oman", "muscat", "jordan", "amman", "lebanon",
        "beirut", "iraq", "baghdad", "iran", "tehran", "israel", "tel aviv", "jerusalem", "palestine", "egypt", "cairo",
        "turkey", "türkiye", "istanbul", "ankara", "remote, mena", "mena remote",
    },
    "africa": {
        "africa", "south africa", "johannesburg", "cape town", "durban", "nigeria", "lagos", "abuja", "kenya", "nairobi",
        "ghana", "accra", "ethiopia", "addis ababa", "uganda", "kampala", "tanzania", "dar es salaam", "rwanda", "kigali",
        "senegal", "dakar", "ivory coast", "cote d ivoire", "morocco", "casablanca", "rabat", "algeria", "tunisia", "libya",
        "botswana", "namibia", "zambia", "zimbabwe", "mozambique", "angola", "cameroon", "ivory coast", "remote, africa",
    },
    "oceania": {
        "oceania", "australia", "new zealand", "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra", "auckland",
        "wellington", "christchurch", "fiji", "papua new guinea", "samoa", "tonga", "vanuatu", "solomon islands", "remote, oceania",
    },
}

# Place names indicating an explicit country/region help avoid treating a US-only
# remote listing as India-eligible just because it contains the word "remote".
_ALL_GEOGRAPHY_TERMS = set().union(*_REGION_TERMS.values()) | {
    "worldwide", "anywhere", "global", "remote", "remote worldwide", "work from anywhere", "work from anywhere in the world"
}


def _norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    normalized = f" {_norm(text)} "
    return any(f" {_norm(term)} " in normalized for term in terms if term)


def normalize_region(region: str | None) -> str:
    value = (region or "global").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {"america": "americas", "americas": "americas", "middleeast": "middle_east", "all": "global", "worldwide": "global", "all_regions": "global"}
    value = aliases.get(value, value)
    return value if value in REGIONS else "global"


def location_matches_region(posting: NormalizedPosting, region: str = "global", custom_location: str = "") -> bool:
    region = normalize_region(region)
    if region == "global":
        return True
    # For web-search leads only, country-targeted search context is a fallback when
    # the original page did not expose a location. Keep the displayed location unknown
    # and flag it in the research report rather than presenting the target country as fact.
    if getattr(posting, "provider", "") == "brave_web_search" and getattr(posting, "search_region_hint", ""):
        code = str(posting.search_region_hint).upper()
        country_regions = {
            "IN": {"india", "asia"}, "SG": {"asia"}, "JP": {"asia"}, "KR": {"asia"},
            "DE": {"europe"}, "FR": {"europe"}, "NL": {"europe"}, "GB": {"europe"},
            "US": {"americas"}, "CA": {"americas"}, "BR": {"americas"},
            "AE": {"middle_east"}, "SA": {"middle_east"}, "QA": {"middle_east"},
            "ZA": {"africa"}, "NG": {"africa"}, "EG": {"africa"}, "AU": {"oceania"}, "NZ": {"oceania"},
        }
        if region in country_regions.get(code, set()):
            return True
        if region == "custom":
            custom = _norm(custom_location)
            hint_names = {"IN": "india", "US": "united states", "GB": "united kingdom", "SG": "singapore", "DE": "germany", "AE": "united arab emirates", "AU": "australia", "CA": "canada", "FR": "france", "NL": "netherlands", "JP": "japan"}
            if any(term in custom for term in [hint_names.get(code, ""), code.lower()] if term):
                return True
    location = posting.location or ""
    location_text = _norm(location)
    if region == "custom":
        terms = [_norm(item) for item in re.split(r"[,;|]+", custom_location or "") if _norm(item)]
        if not terms:
            return True
        if any(f" {term} " in f" {location_text} " for term in terms):
            return True
        is_remote = "remote" in _norm(posting.work_mode) or "remote" in location_text or "work from home" in _norm(posting.description[:4000])
        if is_remote:
            description_text = f" {_norm(posting.description[:5000])} "
            return any(f" {term} " in description_text for term in terms)
        return False

    terms = _REGION_TERMS.get(region, set())
    if _contains_any(location, terms):
        return True

    mode = _norm(posting.work_mode)
    is_remote = "remote" in mode or "remote" in location_text or "work from home" in _norm(posting.description[:4000])
    if not is_remote:
        return False

    # Remote descriptions frequently contain explicit regional eligibility not copied
    # into the location field. Check that evidence before considering generic Remote.
    evidence = f"{location} {posting.description[:4000]}"
    if _contains_any(evidence, terms):
        return True
    if _contains_any(evidence, {"worldwide", "anywhere", "global", "work from anywhere", "remote worldwide"}):
        return True

    # If the feed only says "Remote" and provides no geographic eligibility, keep the
    # lead visible for all selected regions; the person must verify work eligibility.
    location_has_known_geography = _contains_any(location, _ALL_GEOGRAPHY_TERMS - {"remote", "global", "anywhere", "worldwide"})
    return not location_has_known_geography


def classify_work_mode(posting: NormalizedPosting) -> str:
    text = _norm(f"{posting.work_mode} {posting.location} {posting.description[:2500]}")
    mode = _norm(posting.work_mode)
    if mode in {"remote", "fully remote", "work from home", "wfh"} or "remote" in mode:
        return "remote"
    if mode == "hybrid" or "hybrid" in mode:
        return "hybrid"
    if mode in {"on site", "onsite", "in office"} or "on site" in text or "onsite" in text or "in office" in text:
        return "onsite"
    if "hybrid" in text:
        return "hybrid"
    if "on site" in text or "onsite" in text or "in office" in text or "office based" in text:
        return "onsite"
    if "remote" in text or "work from home" in text or "distributed team" in text or "wfh" in text:
        return "remote"
    return "unknown"


def classify_employment_type(posting: NormalizedPosting) -> str:
    text = _norm(f"{posting.title} {posting.description[:5000]}")
    if re.search(r"\b(intern|internship|internships|trainee program)\b", text):
        return "internship"
    if re.search(r"\b(freelance|freelancer|independent contractor|contract role|contract position|contractor|contractual|fixed term|fixed-term|consultant contract)\b", text):
        return "contract_freelance"
    if re.search(r"\b(part time|part time role|part time position|part time employment|part timer)\b", text):
        return "part_time"
    if re.search(r"\b(temporary|temp role|seasonal|short term assignment)\b", text):
        return "temporary"
    if re.search(r"\b(full time|full time role|full time position|permanent|regular employment)\b", text):
        return "full_time"
    return "unknown"


def matches_search_filters(
    posting: NormalizedPosting,
    *,
    region: str = "global",
    custom_location: str = "",
    work_modes: list[str] | None = None,
    employment_types: list[str] | None = None,
) -> bool:
    selected_modes = set(work_modes or WORK_MODES)
    selected_types = set(employment_types or EMPLOYMENT_TYPES)
    if not location_matches_region(posting, region, custom_location):
        return False
    if classify_work_mode(posting) not in selected_modes:
        return False
    if classify_employment_type(posting) not in selected_types:
        return False
    return True
