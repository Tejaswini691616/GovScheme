"""
SmartGov AI - RPA Service

Purpose:
1. Read government schemes from SmartGov SQLite database.
2. Open official government sources using Selenium with Microsoft Edge.
3. Extract visible webpage content and detect error, empty, or alert pages.
4. Categorize results with strict, truthful status categories:
   - SUCCESS: Live government portal loaded, verified, and content extracted.
   - UNAVAILABLE: Government website unreachable or HTTP connection refused.
   - TIMEOUT: Government server timed out (> 20s) after bounded retries.
   - DNS_ERROR: Domain resolution failed (e.g. net::ERR_NAME_NOT_RESOLVED).
   - EMPTY_RESPONSE: Webpage loaded with insufficient or empty text.
   - NOT_CONFIRMED: Webpage loaded, but scheme-specific details not found.
   - ALERT_ERROR: Native JavaScript alert encountered on page.
5. Record and persist 8 standardized attributes directly in SQLite database:
   scheme_id, scheme_name, category, official_url, source_name,
   rpa_status, rpa_last_checked, rpa_content, rpa_error.
6. Non-destructive content preservation: never overwrites existing valid content
   with empty content when a later run encounters a temporary downtime.
7. Bounded retries only (MAX_RETRIES = 2). Never loops infinitely.
8. Error isolation: individual failed websites never stop subsequent schemes.
"""

import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure Windows terminal standard streams handle UTF-8 symbols reliably
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path so rpa_service can run from any working directory
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.db import DB_PATH, get_db_connection

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    UnexpectedAlertPresentException,
    NoAlertPresentException
)


# ============================================================
# CONFIGURATION
# ============================================================

PAGE_LOAD_TIMEOUT = 20
CONTENT_WAIT = 3
MAX_RETRIES = 2
PREVIEW_LENGTH = 400


# ============================================================
# CREATE EDGE DRIVER
# ============================================================

def create_driver(headless=False):
    """Initializes and returns a Microsoft Edge WebDriver instance."""
    print("Browser:")
    mode = "Headless" if headless else "GUI"
    print(f"Starting Microsoft Edge ({mode})...")

    options = webdriver.EdgeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-gpu")
    options.add_argument("--ignore-certificate-errors")
    if headless:
        options.add_argument("--headless=new")

    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    print("Microsoft Edge started successfully.")
    return driver


# ============================================================
# LOAD SCHEMES FROM DATABASE
# ============================================================

def load_schemes(limit=None):
    """
    Load active government schemes from the canonical SQLite database.
    """
    print("\nDatabase:")
    print(f"Checking location: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("❌ Database not found.")
        print(f"Expected location: {DB_PATH}")
        return []

    conn = get_db_connection()

    try:
        query = """
            SELECT
                id,
                scheme_id,
                scheme_name,
                category,
                official_url,
                source_name,
                rpa_status,
                rpa_last_checked,
                rpa_content,
                rpa_error
            FROM schemes
            WHERE is_active = 1
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {int(limit)}"

        cursor = conn.execute(query)
        rows = cursor.fetchall()

        schemes = []
        for row in rows:
            schemes.append({
                "id": row["id"],
                "scheme_id": row["scheme_id"],
                "scheme_name": row["scheme_name"],
                "category": row["category"],
                "official_url": row["official_url"],
                "source_name": row["source_name"],
                "rpa_status": row["rpa_status"],
                "rpa_last_checked": row["rpa_last_checked"],
                "rpa_content": row["rpa_content"],
                "rpa_error": row["rpa_error"]
            })

        print(f"{len(schemes)} schemes loaded from database.")
        return schemes

    except Exception as error:
        print(f"❌ Unable to read schemes from database: {error}")
        return []

    finally:
        conn.close()


# ============================================================
# PERSIST RPA RESULTS TO DATABASE
# ============================================================

def save_scheme_rpa_result(result):
    """
    Persists the RPA outcome for a single scheme into the SQLite database.
    Non-destructive: preserves existing valid rpa_content if current run failed or returned empty.
    """
    conn = get_db_connection()

    try:
        scheme_id = result["scheme_id"]

        # Fetch existing record to avoid overwriting valid prior content
        existing = conn.execute(
            "SELECT rpa_content FROM schemes WHERE scheme_id = ?",
            (scheme_id,)
        ).fetchone()

        new_content = result.get("content")
        if not new_content and existing and existing["rpa_content"]:
            final_content = existing["rpa_content"]
        else:
            final_content = new_content

        conn.execute(
            """
            UPDATE schemes
            SET
                official_url = ?,
                source_name = ?,
                rpa_status = ?,
                rpa_last_checked = ?,
                rpa_content = ?,
                rpa_error = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE scheme_id = ?
            """,
            (
                result["official_url"],
                result["source_name"],
                result["status"],
                result["last_checked"],
                final_content,
                result["error_message"],
                scheme_id
            )
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        print(f"⚠️ Failed to persist RPA result for {result.get('scheme_name')}: {e}")

    finally:
        conn.close()


# ============================================================
# OFFICIAL GOVERNMENT SOURCES
# ============================================================

def get_official_source(scheme_name, db_url=None):
    """
    Resolves the official government source name and URL.
    Prefers URL stored in database, falls back to official scheme mapping.
    """
    if db_url and str(db_url).strip().startswith("http"):
        return {
            "name": f"{scheme_name} Official Portal",
            "url": str(db_url).strip()
        }

    name = scheme_name.lower().strip()

    if "pm-kisan" in name or "pm kisan" in name or "kisan samman" in name:
        return {
            "name": "PM-KISAN Official Government Portal",
            "url": "https://pmkisan.gov.in/"
        }

    if "ayushman" in name or "pm-jay" in name or "pmjay" in name:
        return {
            "name": "Ayushman Bharat PM-JAY Official Government Portal",
            "url": "https://pmjay.gov.in/"
        }

    if "scholarship" in name:
        return {
            "name": "National Scholarship Portal",
            "url": "https://scholarships.gov.in/"
        }

    if "mudra" in name or "pmmy" in name:
        return {
            "name": "Pradhan Mantri MUDRA Yojana Portal",
            "url": "https://www.mudra.org.in/"
        }

    if "ujjwala" in name or "pmuy" in name:
        return {
            "name": "Pradhan Mantri Ujjwala Yojana Portal",
            "url": "https://www.pmuy.gov.in/"
        }

    if "svanidhi" in name:
        return {
            "name": "PM SVANidhi Official Portal",
            "url": "https://pmsvanidhi.mohua.gov.in/"
        }

    if "vishwakarma" in name:
        return {
            "name": "PM Vishwakarma Official Portal",
            "url": "https://pmvishwakarma.gov.in/"
        }

    if "stand-up" in name or "stand up" in name:
        return {
            "name": "Stand-Up India Official Portal",
            "url": "https://www.standupmitra.in/"
        }

    # Jan Suraksha official rules/scheme notifications page lists APY, PMJJBY, and PMSBY
    if "atal pension" in name or "pmjjby" in name or "pmsby" in name:
        return {
            "name": "Jan Suraksha Government Schemes Portal",
            "url": "https://www.jansuraksha.gov.in/Rules.aspx"
        }

    if "housing" in name or "pmay" in name or "awas" in name:
        return {
            "name": "Pradhan Mantri Awaas Yojana (Gramin) Portal",
            "url": "https://pmayg.nic.in/"
        }

    if "social assistance" in name or "old age" in name or "disability" in name or "senior citizen" in name:
        return {
            "name": "National Social Assistance Programme Portal",
            "url": "https://nsap.nic.in/"
        }

    if "kisan credit" in name or "kcc" in name:
        return {
            "name": "Kisan Credit Card / PM-KISAN Portal",
            "url": "https://pmkisan.gov.in/"
        }

    return {
        "name": "myScheme National Government Portal",
        "url": "https://www.myscheme.gov.in/"
    }


# ============================================================
# ERROR PAGE DETECTION
# ============================================================

def is_error_page(text):
    """
    Detects whether the extracted webpage text represents a browser or server error page.
    """
    if not text or len(text.strip()) == 0:
        return True

    text_lower = text.lower()

    error_phrases = [
        "this page isn’t working",
        "this page isn't working",
        "didn’t send any data",
        "didn't send any data",
        "err_empty_response",
        "err_connection_timed_out",
        "err_connection_refused",
        "err_name_not_resolved",
        "err_connection_closed",
        "err_ssl_protocol_error",
        "site can't be reached",
        "site cannot be reached",
        "something went wrong",
        "error 404",
        "404 not found",
        "500 internal server error",
        "502 bad gateway",
        "503 service unavailable",
        "504 gateway timeout",
        "access denied",
        "request timed out"
    ]

    for phrase in error_phrases:
        if phrase in text_lower:
            return True

    return False


# ============================================================
# SCHEME CONTENT VERIFICATION
# ============================================================

def verify_scheme_content(scheme_name, page_text):
    """
    Verifies that the extracted webpage contains meaningful, scheme-related content.
    Combines exact match, normalized variations, and domain keywords.
    """
    if not page_text or is_error_page(page_text):
        return False

    text_clean = re.sub(r"[^a-z0-9 ]", " ", page_text.lower())
    text_clean = re.sub(r"\s+", " ", text_clean)

    scheme_clean = re.sub(r"[^a-z0-9 ]", " ", scheme_name.lower())
    scheme_clean = re.sub(r"\s+", " ", scheme_clean).strip()

    # 1. Direct name match
    if scheme_clean in text_clean:
        return True

    # 2. Scheme-specific aliases
    aliases = {
        "pm-kisan": ["pm kisan", "kisan samman nidhi", "pmkisan", "pradhan mantri kisan"],
        "ayushman": ["ayushman bharat", "pm jay", "pmjay", "jan arogya", "ab pmjay", "national health authority"],
        "scholarship": ["scholarship", "scholarships", "fellowship", "stipend", "merit"],
        "mudra": ["mudra", "pmmy", "micro units", "pradhan mantri mudra yojana"],
        "atal pension": ["atal pension yojana", "atal pension", "apy", "pension fund", "pfrda"],
        "pmjjby": ["pradhan mantri jeevan jyoti bima yojana", "jeevan jyoti", "pmjjby", "life insurance", "jansuraksha"],
        "pmsby": ["pradhan mantri suraksha bima yojana", "suraksha bima", "pmsby", "accident insurance", "jansuraksha"],
        "pm ujjwala": ["ujjwala", "pmuy", "lpg connection", "pradhan mantri ujjwala"],
        "pm svanidhi": ["svanidhi", "street vendor", "atmanirbhar nidhi", "pmsvanidhi"],
        "pm vishwakarma": ["vishwakarma", "artisan", "craftsperson", "pmvishwakarma"],
        "stand-up": ["stand up india", "standup india", "greenfield enterprise", "sidbi"],
        "pmay-g": ["pmay", "awaas yojana", "rural housing", "pradhan mantri gramin awas"],
        "social assistance": ["nsap", "national social assistance", "old age pension", "ignops"],
        "disability": ["disability", "divyangjan", "disabled support", "nsap"],
        "kisan credit": ["kisan credit card", "kcc", "crop loan", "pm-kisan"]
    }

    for key, keywords in aliases.items():
        if key in scheme_name.lower():
            for kw in keywords:
                if kw in text_clean:
                    return True

    # 3. Generic token overlap (at least 2 significant keywords found)
    stopwords = {"and", "for", "the", "with", "support", "prototype", "scheme", "welfare", "national"}
    tokens = [w for w in scheme_clean.split() if w not in stopwords and len(w) > 2]
    if tokens:
        matched_tokens = [t for t in tokens if t in text_clean]
        if len(matched_tokens) >= min(2, len(tokens)):
            return True

    return False


# ============================================================
# EXTRACT PAGE TEXT
# ============================================================

def extract_page_information(driver):
    """
    Extracts visible text from the webpage body and performs quality checks.
    Safely handles alerts if triggered during DOM access.
    """
    try:
        # Check if an alert was triggered
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.dismiss()
            return {
                "success": False,
                "content": "",
                "status": "ALERT_ERROR",
                "message": f"Browser alert: {alert_text}"
            }
        except NoAlertPresentException:
            pass

        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text.strip()

        # Clean excessive blank lines
        text = re.sub(r"\n\s*\n+", "\n", text).strip()

        if not text:
            return {
                "success": False,
                "content": "",
                "status": "EMPTY_RESPONSE",
                "message": "Webpage loaded but returned empty content."
            }

        if len(text) < 60:
            return {
                "success": False,
                "content": text,
                "status": "EMPTY_RESPONSE",
                "message": "Webpage content is insufficient (< 60 characters)."
            }

        if is_error_page(text):
            return {
                "success": False,
                "content": text,
                "status": "UNAVAILABLE",
                "message": "Webpage displayed an error or unavailable response."
            }

        return {
            "success": True,
            "content": text,
            "status": "SUCCESS",
            "message": "Information extracted successfully."
        }

    except UnexpectedAlertPresentException as uae:
        alert_msg = str(uae.alert_text or uae)
        try:
            alert = driver.switch_to.alert
            alert.dismiss()
        except Exception:
            pass
        return {
            "success": False,
            "content": "",
            "status": "ALERT_ERROR",
            "message": f"Browser alert: {alert_msg}"
        }

    except Exception as error:
        return {
            "success": False,
            "content": "",
            "status": "UNAVAILABLE",
            "message": f"Failed to extract page text: {str(error)}"
        }


# ============================================================
# OPEN GOVERNMENT WEBSITE (WITH BOUNDED RETRIES)
# ============================================================

def open_government_source(driver, url, max_retries=MAX_RETRIES):
    """
    Opens the official URL using Selenium with bounded retries.
    Classifies errors into:
    - LOADED (Ready for extraction)
    - ALERT_ERROR (Browser JavaScript alert popup)
    - DNS_ERROR (Domain name resolution failed)
    - TIMEOUT (Server response timed out)
    - UNAVAILABLE (Connection refused / network failure)
    """
    attempt = 1

    while attempt <= max_retries:
        try:
            if attempt > 1:
                print(f"Retry {attempt}/{max_retries}...")
                time.sleep(2)

            driver.get(url)

            # Check if a JavaScript alert appeared on load
            try:
                alert = driver.switch_to.alert
                alert_text = alert.text
                alert.dismiss()
                print(f"⚠️ Alert detected: {alert_text}")
                return {
                    "success": False,
                    "status": "ALERT_ERROR",
                    "message": f"Browser alert: {alert_text}"
                }
            except NoAlertPresentException:
                pass

            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            time.sleep(CONTENT_WAIT)
            return {
                "success": True,
                "status": "LOADED",
                "message": "Website loaded successfully."
            }

        except UnexpectedAlertPresentException as uae:
            alert_msg = str(uae.alert_text or uae)
            print(f"⚠️ Unexpected alert: {alert_msg}")
            try:
                alert = driver.switch_to.alert
                alert.dismiss()
            except Exception:
                pass
            return {
                "success": False,
                "status": "ALERT_ERROR",
                "message": f"Browser alert: {alert_msg}"
            }

        except TimeoutException:
            print(f"⚠️ Attempt {attempt}/{max_retries}: Website timed out ({PAGE_LOAD_TIMEOUT}s).")
            if attempt >= max_retries:
                return {
                    "success": False,
                    "status": "TIMEOUT",
                    "message": f"Connection timed out after {max_retries} attempts."
                }
            attempt += 1

        except WebDriverException as error:
            err_msg = str(error)
            if "net::ERR_NAME_NOT_RESOLVED" in err_msg:
                print(f"⚠️ Attempt {attempt}/{max_retries}: DNS resolution failed.")
                if attempt >= max_retries:
                    return {
                        "success": False,
                        "status": "DNS_ERROR",
                        "message": "Domain could not be resolved (DNS error)."
                    }
            elif "ERR_CONNECTION_TIMED_OUT" in err_msg or "TIMEOUT" in err_msg.upper():
                print(f"⚠️ Attempt {attempt}/{max_retries}: Connection timed out.")
                if attempt >= max_retries:
                    return {
                        "success": False,
                        "status": "TIMEOUT",
                        "message": "Connection timed out."
                    }
            elif "ERR_CONNECTION_REFUSED" in err_msg or "ERR_CONNECTION_CLOSED" in err_msg:
                print(f"⚠️ Attempt {attempt}/{max_retries}: Connection refused or closed.")
                if attempt >= max_retries:
                    return {
                        "success": False,
                        "status": "UNAVAILABLE",
                        "message": "Government server refused or closed connection."
                    }
            else:
                print(f"⚠️ Attempt {attempt}/{max_retries}: Web error ({err_msg[:60]}).")
                if attempt >= max_retries:
                    return {
                        "success": False,
                        "status": "UNAVAILABLE",
                        "message": f"Website unavailable: {err_msg[:100]}"
                    }
            attempt += 1

        except Exception as error:
            print(f"⚠️ Attempt {attempt}/{max_retries}: Unexpected error: {error}")
            if attempt >= max_retries:
                return {
                    "success": False,
                    "status": "UNAVAILABLE",
                    "message": str(error)
                }
            attempt += 1

    return {
        "success": False,
        "status": "UNAVAILABLE",
        "message": "Maximum retries exceeded."
    }


# ============================================================
# PROCESS ONE SCHEME
# ============================================================

def process_scheme(driver, scheme, index, total):
    """
    Executes the RPA pipeline for a single government scheme:
    1. Resolve official government source
    2. Open URL with retry bounding and error classification
    3. Extract text
    4. Verify scheme-specific information
    5. Persist the outcome into SQLite immediately
    6. Return 8 standardized attributes
    """
    scheme_id = scheme["scheme_id"]
    scheme_name = scheme["scheme_name"]
    category = scheme.get("category", "General")
    last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\n" + "-" * 60)
    print(f"SCHEME {index}/{total}")
    print("-" * 60)
    print(f"{scheme_name}")
    print(f"ID: {scheme_id}")
    print(f"Category: {category}")

    source = get_official_source(scheme_name, scheme.get("official_url"))
    print(f"\nSource:\n{source['name']}\nURL: {source['url']}")

    # 1. Open Website
    open_result = open_government_source(driver, source["url"])

    if not open_result["success"]:
        status = open_result["status"]
        error_message = open_result["message"]
        print(f"\nStatus:\n{status}")
        print("Data extracted:\nNO")

        result = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "category": category,
            "official_url": source["url"],
            "source_name": source["name"],
            "status": status,
            "extracted_content_available": False,
            "last_checked": last_checked,
            "error_message": error_message,
            "content": ""
        }
        save_scheme_rpa_result(result)
        return result

    # 2. Extract Content
    page_result = extract_page_information(driver)

    if not page_result["success"]:
        status = page_result["status"]
        error_message = page_result["message"]
        print(f"\nStatus:\n{status}")
        print("Data extracted:\nNO")

        result = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "category": category,
            "official_url": source["url"],
            "source_name": source["name"],
            "status": status,
            "extracted_content_available": False,
            "last_checked": last_checked,
            "error_message": error_message,
            "content": ""
        }
        save_scheme_rpa_result(result)
        return result

    page_text = page_result["content"]

    # 3. Verify Scheme Information
    is_confirmed = verify_scheme_content(scheme_name, page_text)

    if is_confirmed:
        print("\nStatus:\nSUCCESS")
        print("Data extracted:\nYES")
        print("\nInformation Preview:")
        print(page_text[:PREVIEW_LENGTH] + ("..." if len(page_text) > PREVIEW_LENGTH else ""))

        result = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "category": category,
            "official_url": source["url"],
            "source_name": source["name"],
            "status": "SUCCESS",
            "extracted_content_available": True,
            "last_checked": last_checked,
            "error_message": "",
            "content": page_text
        }
        save_scheme_rpa_result(result)
        return result

    else:
        print("\nStatus:\nNOT_CONFIRMED")
        print("Data extracted:\nPARTIAL (Scheme keywords not matched)")

        result = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "category": category,
            "official_url": source["url"],
            "source_name": source["name"],
            "status": "NOT_CONFIRMED",
            "extracted_content_available": False,
            "last_checked": last_checked,
            "error_message": "Webpage loaded, but scheme-specific details could not be confirmed.",
            "content": page_text
        }
        save_scheme_rpa_result(result)
        return result


# ============================================================
# DISPLAY SUMMARY
# ============================================================

def display_summary(results):
    """
    Renders a clear, professional console summary of the RPA execution
    with exact counts for every category.
    """
    total = len(results)
    successful = sum(1 for r in results if r["status"] == "SUCCESS")
    unavailable = sum(1 for r in results if r["status"] == "UNAVAILABLE")
    timeout = sum(1 for r in results if r["status"] == "TIMEOUT")
    dns_errors = sum(1 for r in results if r["status"] == "DNS_ERROR")
    not_confirmed = sum(1 for r in results if r["status"] == "NOT_CONFIRMED")
    alert_errors = sum(1 for r in results if r["status"] == "ALERT_ERROR")
    empty_responses = sum(1 for r in results if r["status"] == "EMPTY_RESPONSE")
    other_errors = total - (successful + unavailable + timeout + dns_errors + not_confirmed + alert_errors + empty_responses)

    print("\n" + "=" * 60)
    print("RPA SUMMARY")
    print("=" * 60)
    print(f"Total schemes: {total}")
    print(f"Successful:    {successful}")
    print(f"Unavailable:   {unavailable}")
    print(f"Timeout:       {timeout}")
    print(f"DNS errors:    {dns_errors}")
    print(f"Alert errors:  {alert_errors}")
    print(f"Not confirmed: {not_confirmed}")
    print(f"Empty:         {empty_responses}")
    print(f"Other errors:  {other_errors}")
    print("-" * 60)
    print("Detailed Scheme Breakdown:")
    for r in results:
        indicator = "✅" if r["status"] == "SUCCESS" else ("⚠️" if r["status"] in ["TIMEOUT", "ALERT_ERROR", "NOT_CONFIRMED"] else "❌")
        content_flag = "YES" if r["extracted_content_available"] else "NO"
        print(f"  {indicator} {r['scheme_id']} | {r['scheme_name']:45} | {r['status']:14} | Extracted: {content_flag}")

    print("------------------------------------------------------------")
    print("RPA process completed. Results persisted in SmartGov SQLite database.")
    print("============================================================\n")


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

def run_rpa(limit=None, headless=False):
    """
    Main orchestrator for SmartGov AI RPA automation:
    - Loads schemes from SQLite
    - Manages browser lifecycle
    - Handles per-scheme failures without terminating the entire run
    - Persists every result into SQLite database
    - Returns structured summary
    """
    print("============================================================")
    print("SMARTGOV AI - RPA AUTOMATION")
    print("============================================================")

    schemes = load_schemes(limit=limit)

    if not schemes:
        print("\n❌ No schemes loaded. Aborting RPA run.")
        return {
            "success": False,
            "total": 0,
            "successful": 0,
            "results": []
        }

    driver = None
    results = []
    total = len(schemes)

    try:
        driver = create_driver(headless=headless)

        for index, scheme in enumerate(schemes, start=1):
            try:
                result = process_scheme(driver, scheme, index, total)
                results.append(result)

            except WebDriverException as wde:
                print(f"❌ Browser exception on {scheme['scheme_name']}: {wde}")
                res = {
                    "scheme_id": scheme["scheme_id"],
                    "scheme_name": scheme["scheme_name"],
                    "category": scheme.get("category", "General"),
                    "official_url": "",
                    "source_name": "",
                    "status": "UNAVAILABLE",
                    "extracted_content_available": False,
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error_message": str(wde),
                    "content": ""
                }
                save_scheme_rpa_result(res)
                results.append(res)

                # Reinitialize driver if crashed
                try:
                    driver.quit()
                except Exception:
                    pass
                print("🔄 Restarting Microsoft Edge...")
                driver = create_driver(headless=headless)

            except Exception as e:
                print(f"❌ Unexpected error on {scheme['scheme_name']}: {e}")
                res = {
                    "scheme_id": scheme["scheme_id"],
                    "scheme_name": scheme["scheme_name"],
                    "category": scheme.get("category", "General"),
                    "official_url": "",
                    "source_name": "",
                    "status": "UNAVAILABLE",
                    "extracted_content_available": False,
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "error_message": str(e),
                    "content": ""
                }
                save_scheme_rpa_result(res)
                results.append(res)

            time.sleep(1)

        display_summary(results)

        successful = sum(1 for r in results if r["status"] == "SUCCESS")
        return {
            "success": successful > 0,
            "total": total,
            "successful": successful,
            "results": results
        }

    finally:
        if driver:
            try:
                print("Closing Microsoft Edge...")
                driver.quit()
                print("Browser closed successfully.")
            except Exception:
                pass


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_rpa()