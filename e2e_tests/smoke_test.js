const puppeteer = require('puppeteer');

(async () => {
    console.log("Starting E2E Smoke Test...");
    const browser = await puppeteer.launch({
        headless: 'new', // Use new headless mode
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });

    try {
        console.log("Navigating to http://localhost:3000");
        await page.goto('http://localhost:3000', { waitUntil: 'networkidle2' });

        // Wait for setup or login to render
        await new Promise(r => setTimeout(r, 1000));

        const isSetupPage = await page.$('#confirmPassword') !== null;

        if (isSetupPage) {
            console.log("Detected Setup Page. Filling out form...");
            await page.type('#username', 'admin', { delay: 50 });
            await page.type('#email', 'admin@example.com', { delay: 50 });
            await page.type('#password', 'adminadmin', { delay: 50 });
            await page.type('#confirmPassword', 'adminadmin', { delay: 50 });

            console.log("Taking screenshot: setup_filled.png");
            await page.screenshot({ path: 'setup_filled.png' });

            console.log("Submitting Setup Form...");
            await page.click('button[type="submit"]');

            // Wait for redirect to /login
            await page.waitForNavigation({ waitUntil: 'networkidle0' });
            console.log("Navigated after setup.");
        }

        const isLoginPage = await page.$('#username') !== null && await page.$('#password') !== null;

        if (isLoginPage) {
            console.log("Detected Login Page. Logging in...");
            // Ensure inputs are clear if redirected with values
            await page.evaluate(() => {
                document.getElementById('username').value = '';
                document.getElementById('password').value = '';
            });
            await page.type('#username', 'admin', { delay: 50 });
            await page.type('#password', 'adminadmin', { delay: 50 });

            console.log("Submitting Login Form...");
            await page.click('button[type="submit"]');

            // Wait for redirect to dashboard
            await page.waitForNavigation({ waitUntil: 'networkidle0' });
            console.log("Logged in successfully. Navigated to Dashboard.");
        }

        // We should now be on the dashboard
        console.log("Taking screenshot: 1_dashboard.png");
        await page.screenshot({ path: '1_dashboard.png', fullPage: true });

        // Navigate to Hosts
        console.log("Navigating to Hosts...");
        // Look for the "Hosts" or "Inventory" link in the nav bar.
        // Assuming there are anchor tags with text content or specific hrefs.
        const hostsLinkCount = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('a'));
            const hostsLink = links.find(el => el.textContent.includes('Hosts') || el.textContent.includes('Inventory'));
            if (hostsLink) {
                hostsLink.click();
                return 1;
            }
            return 0;
        });

        if (hostsLinkCount > 0) {
            await new Promise(r => setTimeout(r, 2000)); // Give the table time to render
            console.log("Taking screenshot: 2_hosts.png");
            await page.screenshot({ path: '2_hosts.png', fullPage: true });
        } else {
            console.log("Could not find Hosts navigation link, attempting direct navigation.");
            await page.goto('http://localhost:3000/hosts', { waitUntil: 'networkidle2' });
            await new Promise(r => setTimeout(r, 2000));
            await page.screenshot({ path: '2_hosts.png', fullPage: true });
        }

        // Navigate to Alerts
        console.log("Navigating to Alerts...");
        const alertsLinkCount = await page.evaluate(() => {
            const links = Array.from(document.querySelectorAll('a'));
            const alertsLink = links.find(el => el.textContent.includes('Alerts'));
            if (alertsLink) {
                alertsLink.click();
                return 1;
            }
            return 0;
        });

        if (alertsLinkCount > 0) {
            await new Promise(r => setTimeout(r, 2000));
            console.log("Taking screenshot: 3_alerts.png");
            await page.screenshot({ path: '3_alerts.png', fullPage: true });
        } else {
            console.log("Could not find Alerts navigation link, attempting direct navigation.");
            await page.goto('http://localhost:3000/alerts', { waitUntil: 'networkidle2' });
            await new Promise(r => setTimeout(r, 2000));
            await page.screenshot({ path: '3_alerts.png', fullPage: true });
        }

        console.log("All E2E tests completed successfully!");

    } catch (e) {
        console.error("Test failed: ", e);
        await page.screenshot({ path: 'error_screenshot.png' });
    } finally {
        await browser.close();
    }
})();
