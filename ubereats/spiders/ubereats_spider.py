import asyncio

from ubereats import constants
from ubereats import items

from playwright.async_api import async_playwright
import scrapy


class UberEatsSpider(scrapy.Spider):
    name = constants.BOT_NAME
    start_urls = [constants.GOOGLE_URL]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def setup_playwright(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            args=["--disable-blink-features=AutomationControlled"],
            headless=False,
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login_google(self):
        await self.page.goto(constants.GOOGLE_URL)
        await self.page.fill("//input[@type='email']", constants.GOOGLE_LOGIN)
        await self.page.click("//button/span[contains(text(), 'Next')]")
        await self.page.locator("//input[@aria-label='Enter your password']").wait_for()
        await self.page.fill("//input[@type='password']", constants.GOOGLE_PASS)
        await self.page.click("//button/span[contains(text(), 'Next')]")
        await self.page.locator("//a[contains(@href, 'https://accounts.google.com/SignOutOptions')]").wait_for()

    async def login_ubereats(self):
        await self.page.goto(constants.UBER_EATS_URL)
        await self.page.get_by_test_id("header-v2-wrapper").get_by_role("link", name="Log in").click()
        async with self.page.expect_popup() as popup_info:
            await self.page.get_by_test_id("google").click()
            popup = await popup_info.value
            await popup.wait_for_load_state()
            await popup.get_by_role("link", name=constants.GOOGLE_LOGIN).click()
            # await popup.get_by_role("button").last.click()  <- only first time
            ####################################################################
            # email code verification. Use Google API to get code from mailbox #
            ####################################################################

    def start_requests(self):
        data = {}
        asyncio.get_event_loop().run_until_complete(self.run_and_parse(data))
        item = items.UbereatsItem.construct(
            sensor_score=data["sensor_score"],
            visibility_score=data["visibility_score"],
            internationalization_score=data["internationalization_score"],
            downloads=data["downloads"],
            revenue=data["revenue"],
            keywords=data["keywords"],
            reviews=data["reviews"],
        )
        return item.dict()

    async def parse_ubereats(self):
        pass
        #######################################
        # select delivery options, parse data #
        #######################################

    async def run_and_parse(self, data):
        await self.setup_playwright()
        await self.login_google()
        await self.login_ubereats()
        parsed_data = await self.parse_ubereats()
        await self.release_resources()
        data.update(parsed_data)

    async def release_resources(self):
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


# if __name__ == "__main__":
#     from scrapy.crawler import CrawlerProcess
#
#     process = CrawlerProcess()
#     process.crawl(UberEatsSpider)
#     process.start()
