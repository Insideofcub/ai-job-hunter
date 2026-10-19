import asyncio
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from ..config import settings
from ..models import Application, CandidateProfile
from .application_workflow import (
    SUPPORTED_APPLICATION_HOSTS, detect_email_phone, host_is_supported,
    parse_json, safe_resume_path,
)
from .ai_provider import draft_screening_answers_with_ai

BACKEND_DIR = Path(__file__).resolve().parents[2]
RESUME_DIR = BACKEND_DIR / "data" / "resumes"
BROWSER_PROFILE_DIR = BACKEND_DIR / settings.application_browser_profile_dir
BROWSER_SESSIONS: dict[int, tuple[object, object]] = {}


def windows_playwright_loop_issue(loop_type: str, platform: str = sys.platform) -> str | None:
    """Return actionable guidance for Windows loops that cannot spawn Playwright's driver."""
    if platform.lower() == "win32" and "selector" in (loop_type or "").lower():
        return (
            "Playwright's async API cannot start under Windows SelectorEventLoop because it needs async subprocess support. "
            "This commonly happens when Uvicorn is started with --reload or multiple workers. Stop the backend (Ctrl+C) "
            "and restart it without --reload: `python run_server.py` from the backend folder, or "
            "`python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` (no --reload, one worker). "
            "Do not change or reinstall Python; this is an event-loop configuration issue."
        )
    return None


def current_windows_playwright_loop_issue() -> tuple[str, str | None]:
    """Inspect the event loop currently serving this request."""
    try:
        loop_type = type(asyncio.get_running_loop()).__name__
    except RuntimeError:
        loop_type = "no running event loop"
    return loop_type, windows_playwright_loop_issue(loop_type)


async def browser_runtime_diagnostics() -> dict:
    """Inspect the active backend Python environment without opening a browser window."""
    loop_type, loop_issue = current_windows_playwright_loop_issue()
    result = {
        "ready": False,
        "playwright_installed": False,
        "chromium_installed": False,
        "python_executable": sys.executable,
        "event_loop_type": loop_type,
        "event_loop_compatible": loop_issue is None,
        "chromium_path": "",
        "profile_directory": str(BROWSER_PROFILE_DIR),
        "message": "",
        "install_command": "python -m pip install -r requirements.txt; python -m playwright install chromium",
    }
    if loop_issue:
        result["message"] = loop_issue
        result["install_command"] = "python run_server.py  # from the backend folder; no --reload"
        return result

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        result["message"] = (
            "Playwright is not installed in the Python environment running this backend. "
            f"Active interpreter: {sys.executable}. Run the install command in this same backend terminal, "
            "then restart Uvicorn."
        )
        return result

    result["playwright_installed"] = True
    playwright = None
    try:
        playwright = await async_playwright().start()
        chromium_path = Path(playwright.chromium.executable_path)
        result["chromium_path"] = str(chromium_path)
        result["chromium_installed"] = chromium_path.is_file()
    except Exception as exc:
        result["message"] = (
            "The Playwright driver could not start in the active backend environment: "
            f"{type(exc).__name__}: {exc}. Reinstall the backend requirements and Chromium, then restart Uvicorn."
        )
        return result
    finally:
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                pass

    if not result["chromium_installed"]:
        result["message"] = (
            f"Playwright is installed, but Chromium is missing at {result['chromium_path']}. "
            "Run `python -m playwright install chromium` from the same terminal/environment used to start Uvicorn, "
            "then restart the backend."
        )
        return result

    try:
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        result["message"] = (
            f"Chromium is installed, but the browser profile folder is not writable: {BROWSER_PROFILE_DIR}. "
            f"{type(exc).__name__}: {exc}"
        )
        return result

    result["ready"] = True
    result["message"] = "Playwright and Chromium are installed, and the browser profile directory is accessible."
    return result


def _normalise_question(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).split())


async def _cleanup_session(application_id: int, playwright) -> None:
    BROWSER_SESSIONS.pop(application_id, None)
    try:
        await playwright.stop()
    except Exception:
        pass


def _classify_field(meta: dict) -> str | None:
    text = " ".join(str(meta.get(key) or "") for key in ("label", "name", "id", "placeholder", "ariaLabel")).lower()
    field_type = (meta.get("type") or "").lower()
    if field_type in {"hidden", "submit", "button", "reset", "password"}:
        return None
    if "email" in text or field_type == "email":
        return "email"
    if any(x in text for x in ("phone", "mobile", "telephone")) or field_type == "tel":
        return "phone"
    if any(x in text for x in ("first name", "firstname", "given name")):
        return "first_name"
    if any(x in text for x in ("last name", "lastname", "surname", "family name")):
        return "last_name"
    if "full name" in text or text.strip() in {"name", "candidate_name"}:
        return "full_name"
    if any(x in text for x in ("resume", "curriculum vitae", "cv upload")) and (field_type == "file" or meta.get("tag") == "input"):
        return "resume"
    if any(x in text for x in ("cover letter", "letter of interest")):
        return "cover_letter"
    if "linkedin" in text:
        return "linkedin"
    if any(x in text for x in ("portfolio", "website", "personal site")):
        return "website"
    if any(x in text for x in ("current employer", "current company")):
        return "current_company"
    if any(x in text for x in ("current title", "job title", "current role")):
        return "current_title"
    if any(x in text for x in ("city", "current location", "location")):
        return "location"
    if meta.get("tag") in {"textarea", "select"} or field_type in {"text", "search", "url"}:
        return "screening_question"
    return None


async def fill_application_form(application: Application, profile: CandidateProfile, resume_dir: Path = RESUME_DIR, confirm_submit: bool = False) -> dict:
    """Open a visible browser and fill only supported, mapped fields; never bypass human checks."""
    if not host_is_supported(application.source_url):
        return {
            "status": "needs_manual_action", "opened_url": application.source_url,
            "filled_fields": [], "missing_required": [], "needs_human_verification": False,
            "submitted": False, "message": "This job site is not in the supported Greenhouse/Lever host allowlist. Open the application URL and apply manually.",
        }

    if confirm_submit and not settings.auto_submit_enabled:
        raise PermissionError(automation_disabled_message())

    loop_type, loop_issue = current_windows_playwright_loop_issue()
    if loop_issue:
        raise RuntimeError(loop_issue)

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed in the Python environment running this backend. "
            f"Active interpreter: {sys.executable}. From the same backend terminal run "
            "`python -m pip install -r requirements.txt` and `python -m playwright install chromium`, "
            "then restart Uvicorn."
        ) from exc

    facts = parse_json(profile.verified_facts_json, dict, {})
    personal = parse_json(profile.personal_details_json, dict, {})
    career = parse_json(profile.career_profile_json, dict, {})
    profile_text = "\n".join([profile.resume_text or "", profile.profile_summary or "", profile.employment_highlights or ""])
    email, phone = detect_email_phone(profile_text, {**personal, **facts})
    full_name = (profile.full_name or "").strip()
    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    resume_path = safe_resume_path(profile, resume_dir)
    linkedin_url = ""
    website_url = ""
    for row in parse_json(profile.online_profiles_json, list, []):
        if not isinstance(row, dict):
            continue
        value = str(row.get("url") or "").strip()
        hay = (str(row.get("name") or "") + " " + value).lower()
        if "linkedin" in hay and not linkedin_url:
            linkedin_url = value
        if any(term in hay for term in ("portfolio", "website", "github", "behance")) and not website_url:
            website_url = value
    employment = parse_json(profile.employment_history_json, list, [])
    current_job = next((item for item in employment if isinstance(item, dict)), {})
    cover_letter = f"Dear Hiring Team,\n\nI am interested in the {application.title} position at {application.company}. {profile.profile_summary or profile.employment_highlights or profile.resume_headline}\n\nBest regards,\n{full_name}".strip()
    mapped = {
        "email": email, "phone": phone, "first_name": first_name, "last_name": last_name,
        "full_name": full_name, "cover_letter": cover_letter, "linkedin": linkedin_url,
        "website": website_url, "current_company": str(current_job.get("company") or ""),
        "current_title": str(current_job.get("title") or profile.resume_headline or ""),
        "location": str(personal.get("city") or personal.get("location") or ""),
    }

    if confirm_submit and not resume_path:
        return {
            "status": "needs_manual_action", "opened_url": application.source_url,
            "filled_fields": [], "missing_required": ["Attach a valid resume to the candidate profile"],
            "needs_human_verification": False, "submitted": False,
            "message": "Automatic submission stopped because no supported resume file is attached to the profile. Upload your resume first.",
        }

    try:
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Could not create the browser profile folder at {BROWSER_PROFILE_DIR}. "
            f"Check folder permissions. Details: {type(exc).__name__}: {exc}"
        ) from exc

    # Keep the visible browser alive after this API response so the user can review it.
    # Chromium persistent profiles cannot be opened twice simultaneously. Keep one visible session at a time.
    for old_id, old_session in list(BROWSER_SESSIONS.items()):
        BROWSER_SESSIONS.pop(old_id, None)
        old_playwright, old_context = old_session
        try:
            await old_context.close()
        except Exception:
            pass
        try:
            await old_playwright.stop()
        except Exception:
            pass

    try:
        playwright = await async_playwright().start()
    except Exception as exc:
        raise RuntimeError(
            "The Playwright browser driver could not start in the active backend environment. "
            f"Python: {sys.executable}. Details: {type(exc).__name__}: {exc}. "
            "Run `python -m pip install -r requirements.txt` and `python -m playwright install chromium`, then restart Uvicorn."
        ) from exc

    chromium_path = Path(playwright.chromium.executable_path)
    if not chromium_path.is_file():
        try:
            await playwright.stop()
        except Exception:
            pass
        raise RuntimeError(
            f"Playwright is installed, but Chromium is missing at {chromium_path}. "
            "Run `python -m playwright install chromium` from the same backend terminal/environment used to start Uvicorn, "
            "then restart the backend."
        )

    try:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR), headless=False, accept_downloads=False,
        )
    except Exception as exc:
        try:
            await playwright.stop()
        except Exception:
            pass
        detail = f"{type(exc).__name__}: {exc}"
        if "user data directory is already in use" in str(exc).lower() or "singletonlock" in str(exc).lower():
            hint = "Close other AI Job Hunter browser windows that use this browser profile, then retry."
        elif "executable doesn't exist" in str(exc).lower() or "browser executable" in str(exc).lower():
            hint = "Install Chromium in the same backend environment with `python -m playwright install chromium`."
        else:
            hint = "Confirm the backend environment has Playwright Chromium installed and that the browser profile folder is writable."
        raise RuntimeError(f"Chromium could not launch. {hint} Details: {detail}") from exc

    BROWSER_SESSIONS[application.id] = (playwright, context)
    context.on("close", lambda: asyncio.create_task(_cleanup_session(application.id, playwright)))
    try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(application.source_url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(900)
            if not host_is_supported(page.url):
                return {
                    "status": "needs_manual_action", "opened_url": page.url, "filled_fields": [],
                    "missing_required": [], "needs_human_verification": False, "submitted": False,
                    "message": "The job page redirected to an unsupported host. For safety, the agent did not fill or submit that site.",
                }
            page_text = (await page.locator("body").inner_text())[:40000].lower()
            captcha = bool(
                await page.locator('iframe[src*="captcha" i], iframe[src*="recaptcha" i], iframe[src*="hcaptcha" i], [id*="captcha" i], [class*="captcha" i]').count()
                or any(term in page_text for term in ("verify you are human", "complete the captcha", "unusual traffic"))
            )
            fields = await page.locator('input:not([type="hidden"]), textarea, select').evaluate_all("""els => els.map((el, index) => {
              const id = el.id;
              const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : el.closest('label');
              const fieldset = el.closest('fieldset');
              const legend = fieldset ? fieldset.querySelector('legend') : null;
              return {index, tag: el.tagName.toLowerCase(), type: (el.type || '').toLowerCase(), name: el.name || '', id: el.id || '', placeholder: el.placeholder || '', ariaLabel: el.getAttribute('aria-label') || '', label: label?.innerText || legend?.innerText || '', required: !!el.required, value: el.value || ''};
            })""")
            screening_questions = []
            for meta in fields:
                if _classify_field(meta) == "screening_question":
                    label = " ".join(str(meta.get(k) or "") for k in ("label", "name", "id", "placeholder", "ariaLabel")).strip()
                    if label and label not in screening_questions:
                        screening_questions.append(label)
            try:
                existing_answers = json.loads(application.answers_json or "[]")
                if not isinstance(existing_answers, list):
                    existing_answers = []
            except (ValueError, TypeError):
                existing_answers = []
            if screening_questions:
                generated_answers = await draft_screening_answers_with_ai(profile, application, screening_questions)
                by_question = {_normalise_question(str(row.get("question") or "")): row for row in existing_answers if isinstance(row, dict)}
                for generated in generated_answers:
                    key = _normalise_question(generated.get("question", ""))
                    previous = by_question.get(key)
                    if previous and previous.get("status") == "verified":
                        continue
                    if previous and not generated.get("answer") and previous.get("answer"):
                        continue
                    by_question[key] = generated
                existing_answers = list(by_question.values())
                application.answers_json = json.dumps(existing_answers, ensure_ascii=False)

            filled: list[str] = []
            missing: list[str] = []
            for meta in fields:
                kind = _classify_field(meta)
                locator = page.locator('input:not([type="hidden"]), textarea, select').nth(meta["index"])
                if not kind:
                    if meta.get("required"):
                        missing.append(meta.get("label") or meta.get("name") or meta.get("id") or f"Required field {meta['index'] + 1}")
                    continue
                if kind == "resume":
                    if meta["type"] == "file" and resume_path:
                        await locator.set_input_files(str(resume_path))
                        filled.append(f"Resume: {resume_path.name}")
                    elif meta.get("required"):
                        missing.append(meta.get("label") or "Resume upload")
                    continue
                if kind == "screening_question":
                    label = " ".join(str(meta.get(k) or "") for k in ("label", "name", "id", "placeholder", "ariaLabel")).strip()
                    normalized = _normalise_question(label)
                    exact_answer_rows = [
                        row for row in existing_answers if isinstance(row, dict) and
                        normalized == _normalise_question(str(row.get("question") or ""))
                    ]
                    if exact_answer_rows:
                        # Prefer an exact question match before considering shorter, similar prompts.
                        answer_row = next((row for row in exact_answer_rows if row.get("status") == "verified"), exact_answer_rows[0])
                    else:
                        similar_answer_rows = [
                            row for row in existing_answers if isinstance(row, dict) and len(normalized) > 16 and
                            (normalized in _normalise_question(str(row.get("question") or "")) or
                             _normalise_question(str(row.get("question") or "")) in normalized)
                        ]
                        answer_row = max(similar_answer_rows, key=lambda row: len(_normalise_question(str(row.get("question") or ""))), default=None)
                    answer = str(answer_row.get("answer") or "").strip() if answer_row else ""
                    answer_status = str(answer_row.get("status") or "needs_review") if answer_row else "needs_review"
                    if answer and answer_status in {"draft", "verified"}:
                        if meta["tag"] == "select":
                            options = await locator.locator("option").evaluate_all("els => els.map(el => ({value: el.value, text: (el.label || el.innerText || '').trim()}))")
                            target = _normalise_question(answer)
                            exact = next((option for option in options if option.get("value") and (_normalise_question(option.get("value")) == target or _normalise_question(option.get("text")) == target)), None)
                            if exact:
                                await locator.select_option(value=exact["value"])
                                filled.append(label or f"Screening field {meta['index'] + 1}")
                            elif meta.get("required"):
                                missing.append(label or meta.get("name") or f"Required question {meta['index'] + 1}")
                        else:
                            await locator.fill(answer)
                            filled.append(label or f"Screening field {meta['index'] + 1}")
                        if confirm_submit and answer_status != "verified":
                            missing.append(f"Review and verify screening answer before submission: {label or 'Question'}")
                    elif meta.get("required"):
                        missing.append(label or meta.get("name") or f"Required question {meta['index'] + 1}")
                    continue
                value = mapped.get(kind, "")
                if value and meta["tag"] != "select" and meta["type"] not in {"checkbox", "radio", "file"}:
                    await locator.fill(value)
                    filled.append(meta.get("label") or meta.get("name") or kind.replace("_", " "))
                elif meta.get("required"):
                    missing.append(meta.get("label") or meta.get("name") or meta.get("id") or kind.replace("_", " "))
            submit = False
            message = "Form opened and mapped fields filled. Review everything in the visible browser before submitting."
            status = "ready_for_review"
            if captcha:
                message = "Human verification appears on this site. Complete it manually; the agent will not bypass CAPTCHA or verification checks."
                status = "needs_manual_action"
            elif confirm_submit:
                if missing:
                    message = "Submission stopped because required fields remain unmapped. Complete them manually and review the form."
                    status = "needs_manual_action"
                else:
                    buttons = page.get_by_role("button", name=re.compile(r"submit application|submit|send application", re.I))
                    button_count = await buttons.count()
                    if button_count == 0:
                        buttons = page.locator('input[type="submit"]')
                        button_count = await buttons.count()
                    if button_count:
                        await buttons.first.click()
                        await page.wait_for_timeout(1800)
                        post_text = (await page.locator("body").inner_text())[:20000].lower()
                        success_words = ("application submitted", "thanks for applying", "thank you for applying", "successfully submitted", "application received")
                        if any(word in post_text for word in success_words):
                            submit = True
                            status = "submitted"
                            message = "The site displayed a submission confirmation. Please check the visible page and application history."
                        else:
                            submit = False
                            status = "submitted_unconfirmed"
                            message = "The submit control was clicked, but the site did not display a clear confirmation. Verify the application on the site."
                    else:
                        message = "No recognizable submit control was found. Review and submit manually."
                        status = "needs_manual_action"
            if captcha:
                # Don't attempt to submit or work around a verification challenge.
                submit = False
            return {
                "status": status, "opened_url": page.url, "filled_fields": filled,
                "missing_required": missing, "needs_human_verification": captcha,
                "submitted": submit, "message": message,
            }
    except Exception:
        BROWSER_SESSIONS.pop(application.id, None)
        try:
            await context.close()
        finally:
            await playwright.stop()
        raise
