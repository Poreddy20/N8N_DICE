from flask import Flask, request, jsonify
from playwright.async_api import async_playwright
import asyncio
import time
import random
import logging
import os
from datetime import datetime
from functools import wraps

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Credentials
DICE_EMAIL = os.getenv("DICE_EMAIL", "your_email@dice.com")
DICE_PASSWORD = os.getenv("DICE_PASSWORD", "your_password")

# Human behavior configuration
MIN_WAIT_BETWEEN_APPS = 120
MAX_WAIT_BETWEEN_APPS = 180

# Global tracking
last_application_time = None
application_count = 0

def async_route(f):
    """Decorator to handle async routes in Flask"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

async def random_delay(min_sec=1, max_sec=3):
    """Simulate human thinking time"""
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"⏱️  Human delay: {delay:.2f}s")
    await asyncio.sleep(delay)

async def human_mouse_movement(page):
    """Simulate human-like mouse movements"""
    try:
        scroll_amount = random.randint(200, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await random_delay(0.5, 1.5)
        
        await page.evaluate(f"window.scrollBy(0, -{scroll_amount // 2})")
        await random_delay(0.3, 0.8)
        
        logger.info("🖱️  Simulated mouse movements")
    except Exception as e:
        logger.warning(f"Mouse simulation warning: {e}")

def enforce_human_pacing():
    """Enforce minimum time between applications"""
    global last_application_time
    
    if last_application_time:
        time_since_last = (datetime.now() - last_application_time).seconds
        required_wait = random.randint(MIN_WAIT_BETWEEN_APPS, MAX_WAIT_BETWEEN_APPS)
        
        if time_since_last < required_wait:
            wait_time = required_wait - time_since_last
            logger.info(f"⏳ Pacing: waiting {wait_time}s")
            time.sleep(wait_time)

async def create_browser():
    """Create optimized browser for Render"""
    playwright = await async_playwright().start()
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    ]
    
    # Render-optimized browser launch
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',  # Critical for Render
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--single-process',  # Use single process on Render
            '--no-zygote',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
        ]
    )
    
    context = await browser.new_context(
        user_agent=random.choice(user_agents),
        viewport={'width': 1920, 'height': 1080},
        locale='en-US',
        timezone_id='America/New_York',
        extra_http_headers={
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
        }
    )
    
    # Set generous timeout for Render
    context.set_default_timeout(90000)  # 90 seconds
    
    page = await context.new_page()
    
    # Remove webdriver detection
    await page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    return playwright, browser, context, page

async def login_to_dice(page):
    """Login with human-like behavior"""
    logger.info("🔐 Logging in to Dice.com...")
    
    try:
        await page.goto("https://www.dice.com/dashboard/login", 
                       wait_until="networkidle",
                       timeout=90000)
        await random_delay(2, 4)
        
        # Email entry
        logger.info("→ Entering email...")
        email_input = page.locator("input[type='email']")
        await email_input.wait_for(state="visible", timeout=30000)
        
        # Type like human
        for char in DICE_EMAIL:
            await email_input.type(char, delay=random.randint(50, 150))
        await random_delay(0.5, 1)
        
        # Click continue
        continue_btn = page.locator("button[data-testid='sign-in-button']")
        await continue_btn.wait_for(state="visible", timeout=20000)
        await continue_btn.click()
        await random_delay(2, 3)
        
        # Password entry
        logger.info("→ Entering password...")
        password_input = page.locator("input[type='password']")
        await password_input.wait_for(state="visible", timeout=30000)
        
        for char in DICE_PASSWORD:
            await password_input.type(char, delay=random.randint(50, 120))
        await random_delay(0.5, 1.5)
        
        # Sign in
        sign_in_btn = page.locator("button[data-testid='submit-password']")
        await sign_in_btn.wait_for(state="visible", timeout=20000)
        await sign_in_btn.click()
        await random_delay(5, 8)  # Wait for redirect
        
        # Verify login
        if "dashboard" in page.url or "jobs" in page.url:
            logger.info("✅ Login successful")
            return True
        else:
            logger.error(f"❌ Login failed - URL: {page.url}")
            await page.screenshot(path="login_error.png")
            return False
            
    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        try:
            await page.screenshot(path="login_exception.png")
        except:
            pass
        return False

async def wait_for_easy_apply_button(page):
    """Wait for Easy Apply button with multiple strategies"""
    selectors = [
        "button[data-cy='apply-button-card']",
        "button:has-text('Easy Apply')",
        "button:has-text('Apply')",
    ]
    
    # Wait for page to be fully loaded
    await page.wait_for_load_state('networkidle', timeout=60000)
    await asyncio.sleep(3)  # Let React hydrate
    
    for selector in selectors:
        try:
            button = page.locator(selector).first
            await button.wait_for(state="visible", timeout=20000)
            await button.wait_for(state="enabled", timeout=10000)
            
            # Scroll into view
            await button.scroll_into_view_if_needed()
            await asyncio.sleep(1)
            
            logger.info(f"✅ Found button: {selector}")
            return button
            
        except Exception as e:
            logger.debug(f"Button not found with {selector}: {e}")
            continue
    
    raise Exception("Easy Apply button not found")

async def apply_to_job(page, job_url):
    """Apply to job with human-like interactions"""
    global last_application_time, application_count
    
    try:
        logger.info(f"📝 Applying to: {job_url}")
        
        # Navigate to job
        await page.goto(job_url, 
                       wait_until="networkidle",
                       timeout=90000)
        await random_delay(3, 6)
        
        # Simulate reading
        await human_mouse_movement(page)
        await random_delay(2, 4)
        
        # Find and click Easy Apply
        logger.info("→ Looking for Easy Apply button...")
        easy_apply = await wait_for_easy_apply_button(page)
        
        await random_delay(0.5, 1.5)
        await easy_apply.click(timeout=15000)
        await random_delay(3, 5)
        
        # Review form
        await human_mouse_movement(page)
        await random_delay(1.5, 3)
        
        # Click Next
        logger.info("→ Clicking Next...")
        next_btn = page.locator("button[data-testid='bottom-apply-next-button']")
        await next_btn.wait_for(state="visible", timeout=30000)
        await random_delay(0.5, 1)
        await next_btn.click()
        await random_delay(2, 3)
        
        # Submit
        logger.info("→ Submitting application...")
        submit_btn = page.locator("button[data-testid='submit-application-button']")
        await submit_btn.wait_for(state="visible", timeout=30000)
        await random_delay(0.8, 1.5)
        await submit_btn.click()
        await random_delay(2, 3)
        
        # Update tracking
        last_application_time = datetime.now()
        application_count += 1
        
        logger.info(f"✅ Application #{application_count} submitted")
        
        return {
            "status": "success",
            "job_url": job_url,
            "application_number": application_count,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        try:
            await page.screenshot(path=f"error_{int(time.time())}.png")
        except:
            pass
        return {
            "status": "failed",
            "job_url": job_url,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.route('/apply', methods=['POST'])
@async_route
async def apply_endpoint():
    """Main API endpoint - ALWAYS creates fresh session on Render"""
    data = request.json
    job_url = data.get('job_url')
    
    if not job_url:
        return jsonify({"status": "error", "message": "No job URL"}), 400
    
    # Enforce pacing
    enforce_human_pacing()
    
    playwright_instance = None
    browser = None
    
    try:
        logger.info("🔄 Creating fresh browser session...")
        playwright_instance, browser, context, page = await create_browser()
        
        # Login
        if not await login_to_dice(page):
            return jsonify({"status": "error", "message": "Login failed"}), 500
        
        # Apply to job
        result = await apply_to_job(page, job_url)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    finally:
        # ALWAYS cleanup on Render
        try:
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()
        except:
            pass

@app.route('/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "running",
        "applications_count": application_count,
        "last_application": last_application_time.isoformat() if last_application_time else None
    })

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Dice Job Applier - Render Optimized")
    logger.info("=" * 60)
    logger.info(f"📧 Email: {DICE_EMAIL}")
    logger.info(f"⏱️  Min wait: {MIN_WAIT_BETWEEN_APPS}s")
    logger.info("=" * 60)
    
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
