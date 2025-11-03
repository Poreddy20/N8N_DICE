from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import time
import random
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Credentials (use environment variables in production)
DICE_EMAIL = os.getenv("DICE_EMAIL", "your_email@dice.com")
DICE_PASSWORD = os.getenv("DICE_PASSWORD", "your_password")

# Global session state
browser_context = None
last_application_time = None
application_count = 0
session_start_time = None

# Human behavior configuration
MIN_WAIT_BETWEEN_APPS = 120  # 2 minutes minimum
MAX_WAIT_BETWEEN_APPS = 180  # 3 minutes maximum
MAX_APPS_PER_SESSION = 15    # Max applications before relogin
SESSION_MAX_DURATION = 7200  # 2 hours max session

def random_delay(min_sec=1, max_sec=3):
    """Simulate human thinking/reading time"""
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"⏱️  Human delay: {delay:.2f}s")
    time.sleep(delay)

def human_mouse_movement(page):
    """Simulate human-like mouse movements"""
    try:
        # Random scrolling (humans read job descriptions)
        scroll_amount = random.randint(200, 600)
        page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        random_delay(0.5, 1.5)
        
        # Scroll back up a bit (reading behavior)
        page.evaluate(f"window.scrollBy(0, -{scroll_amount // 2})")
        random_delay(0.3, 0.8)
        
        logger.info("🖱️  Simulated mouse movements")
    except Exception as e:
        logger.warning(f"Mouse simulation warning: {e}")

def should_relogin():
    """Determine if we need to create a new session"""
    global last_application_time, application_count, session_start_time, browser_context
    
    # No browser yet
    if browser_context is None:
        return True
    
    # Too many applications in this session
    if application_count >= MAX_APPS_PER_SESSION:
        logger.info("⚠️  Max applications per session reached")
        return True
    
    # Session too old
    if session_start_time and (datetime.now() - session_start_time).seconds > SESSION_MAX_DURATION:
        logger.info("⚠️  Session duration exceeded")
        return True
    
    return False

def enforce_human_pacing():
    """Enforce minimum time between applications"""
    global last_application_time
    
    if last_application_time:
        time_since_last = (datetime.now() - last_application_time).seconds
        required_wait = random.randint(MIN_WAIT_BETWEEN_APPS, MAX_WAIT_BETWEEN_APPS)
        
        if time_since_last < required_wait:
            wait_time = required_wait - time_since_last
            logger.info(f"⏳ Human pacing: waiting {wait_time}s before next application")
            time.sleep(wait_time)

def create_human_like_browser():
    """Create browser with human-like characteristics"""
    playwright = sync_playwright().start()
    
    # Rotate user agents
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ]
    
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',  # Hide automation
            '--disable-dev-shm-usage',
            '--no-sandbox'
        ]
    )
    
    context = browser.new_context(
        user_agent=random.choice(user_agents),
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
        timezone_id='America/New_York',
        # Add realistic browser fingerprint
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
    )
    
    # Remove webdriver detection
    page = context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return playwright, browser, context, page

def login_to_dice(page):
    """Login with human-like behavior"""
    global session_start_time, application_count
    
    logger.info("🔐 Logging in to Dice.com...")
    
    try:
        page.goto("https://www.dice.com/dashboard/login", wait_until="networkidle")
        random_delay(2, 4)  # Read the page
        
        # Step 1: Email
        logger.info("→ Entering email...")
        email_input = page.wait_for_selector("input[type='email']", timeout=10000)
        
        # Type like a human (not instant paste)
        for char in DICE_EMAIL:
            email_input.type(char, delay=random.randint(50, 150))
        random_delay(0.5, 1)
        
        # Click continue
        continue_btn = page.wait_for_selector("button[data-testid='sign-in-button']")
        continue_btn.click()
        random_delay(2, 3)
        
        # Step 2: Password
        logger.info("→ Entering password...")
        password_input = page.wait_for_selector("input[type='password']", timeout=10000)
        
        # Type password like human
        for char in DICE_PASSWORD:
            password_input.type(char, delay=random.randint(50, 120))
        random_delay(0.5, 1.5)
        
        # Click sign in
        sign_in_btn = page.wait_for_selector("button[data-testid='submit-password']")
        sign_in_btn.click()
        random_delay(3, 5)
        
        # Verify login
        if "dashboard" in page.url or "jobs" in page.url:
            logger.info("✅ Login successful")
            session_start_time = datetime.now()
            application_count = 0
            return True
        else:
            logger.error(f"❌ Login failed - URL: {page.url}")
            page.screenshot(path="login_error.png")
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        page.screenshot(path="login_exception.png")
        return False

def apply_to_job(page, job_url, behavior_profile):
    """Apply to job with human-like interactions"""
    global last_application_time, application_count
    
    try:
        logger.info(f"📝 Applying to: {job_url}")
        
        # Navigate to job
        page.goto(job_url, wait_until="networkidle")
        random_delay(3, 6)  # Read job description
        
        # Simulate reading behavior
        human_mouse_movement(page)
        random_delay(2, 4)
        
        # Click Easy Apply
        logger.info("→ Clicking Easy Apply...")
        easy_apply = page.wait_for_selector("button[data-cy='apply-button-card']", timeout=15000)
        random_delay(0.5, 1.5)  # Hesitate before clicking
        easy_apply.click()
        random_delay(2, 3)
        
        # Review application form (humans read before clicking next)
        human_mouse_movement(page)
        random_delay(1.5, 3)
        
        # Click Next
        logger.info("→ Clicking Next...")
        next_btn = page.wait_for_selector("button[data-testid='bottom-apply-next-button']", timeout=15000)
        random_delay(0.5, 1)
        next_btn.click()
        random_delay(2, 3)
        
        # Final review before submit
        random_delay(1, 2)
        
        # Click Submit
        logger.info("→ Submitting application...")
        submit_btn = page.wait_for_selector("button[data-testid='submit-application-button']", timeout=15000)
        random_delay(0.8, 1.5)  # Brief hesitation
        submit_btn.click()
        random_delay(2, 3)
        
        # Update tracking
        last_application_time = datetime.now()
        application_count += 1
        
        logger.info(f"✅ Application #{application_count} submitted successfully")
        
        return {
            "status": "success",
            "job_url": job_url,
            "application_number": application_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        page.screenshot(path="application_error.png")
        return {
            "status": "failed",
            "job_url": job_url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.route('/apply', methods=['POST'])
def apply_endpoint():
    """Main API endpoint for job applications"""
    global browser_context
    
    data = request.json
    job_url = data.get('job_url')
    behavior_profile = data.get('behavior_profile', {})
    
    if not job_url:
        return jsonify({"status": "error", "message": "No job URL provided"}), 400
    
    # Enforce human pacing
    enforce_human_pacing()
    
    playwright_instance = None
    browser = None
    
    try:
        # Check if we need new session
        if should_relogin():
            logger.info("🔄 Creating new browser session...")
            playwright_instance, browser, browser_context, page = create_human_like_browser()
            
            if not login_to_dice(page):
                return jsonify({
                    "status": "error",
                    "message": "Login failed"
                }), 500
        else:
            # Reuse existing session
            page = browser_context.new_page()
            logger.info("♻️  Reusing existing session")
        
        # Apply to job
        result = apply_to_job(page, job_url, behavior_profile)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    
    finally:
        if page:
            page.close()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "running",
        "session_active": browser_context is not None,
        "applications_count": application_count,
        "last_application": last_application_time.isoformat() if last_application_time else None
    })

@app.route('/reset', methods=['POST'])
def reset_session():
    """Force session reset"""
    global browser_context, application_count, session_start_time
    browser_context = None
    application_count = 0
    session_start_time = None
    return jsonify({"status": "success", "message": "Session reset"})

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Dice Job Applier - Cloud Ready")
    logger.info("=" * 60)
    logger.info(f"📧 Email: {DICE_EMAIL}")
    logger.info(f"⏱️  Min wait between apps: {MIN_WAIT_BETWEEN_APPS}s")
    logger.info(f"📊 Max apps per session: {MAX_APPS_PER_SESSION}")
    logger.info("=" * 60)
    
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
