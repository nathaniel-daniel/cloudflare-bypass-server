import asyncio
import tornado
import multiprocessing
from urllib.parse import urlparse
from concurrent.futures.thread import ThreadPoolExecutor
from seleniumbase import SB
import json
from datetime import datetime
from email.utils import formatdate
from time import mktime
import tornado.options
import tornado.log
import platform

tornado.options.define("port", default="8080", help="The port to run on")
tornado.options.define("debug", default=False, help="Whether the server should be run in debug mode")
tornado.options.define("user-agent", default=None, help="Override the user agent")
tornado.options.define("xvfb", default=False, help="Use the xvfb for the browser. Only works on Linux.")

executor = ThreadPoolExecutor(2)

def scraper(url):
    headless = True
    use_xvfb = tornado.options.options.xvfb 
    if use_xvfb:
        headless = False
    with SB(
        uc=True, 
        headless=headless, 
        agent=tornado.options.options.user_agent,
        xvfb=use_xvfb,
    ) as sb:
        sb.uc_open_with_reconnect(url, reconnect_time=4)
        sb.sleep(2)
        
        if use_xvfb:
            sb.uc_gui_click_captcha()
            sb.sleep(2)
            sb.uc_gui_handle_captcha()
        else:
            sb.switch_to_frame("iframe")
            sb.driver.uc_click("span")
        sb.sleep(4)
        
        sb.assert_element_absent('[name="cf-turnstile-response"]', timeout=4)
        sb.sleep(4)
        
        user_agent = sb.get_user_agent()
        cookies = sb.driver.get_cookies()
        
        cf_clearance = get_cookie_by_name(cookies, 'cf_clearance')
        
    return {
        'user_agent': user_agent,
        'cf_clearance': stringify_cookie(cf_clearance),
    }
    
def get_cookie_by_name(cookies, name):
    for cookie in cookies:
        if cookie['name'] == name:
            return cookie
    raise RuntimeError(f'Missing Cookie \"{name}\"')
    
def stringify_cookie(cookie):
    cookie_name = cookie['name']
    cookie_value = cookie['value']
    
    cookie_domain = cookie.get('domain')
    
    cookie_path = cookie.get('path')
    
    cookie_expiry = cookie.get('expiry')
    
    output = f'{cookie_name}={cookie_value}; '
    if cookie_domain is not None:
        output += f'Domain={cookie_domain}; '
        
    if cookie_path is not None:
        output += f'Path={cookie_path}; '
        
    if cookie_expiry is not None:
        cookie_expiry = httpdate(datetime.fromtimestamp(cookie_expiry))
        output += f'Expires={cookie_expiry}; '
        
    if cookie.get('secure') == True:
        output += 'Secure; '
        
    if cookie.get('httpOnly') == True:
        output += 'HttpOnly; '
    
    return output
    
def httpdate(date):
    stamp = mktime(date.timetuple())
    return formatdate(
        timeval = stamp,
        localtime = False,
        usegmt = True,
    )

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Cloudflare Bypass Server')
        
class BypassHandler(tornado.web.RequestHandler):
    async def post(self):
        url = self.get_argument('url')
        
        # Validate url
        parsed_url = urlparse(url)
        if parsed_url.scheme == '' or parsed_url.netloc == '':
            raise tornado.web.HTTPError(400)
            
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, scraper, url)
        
        self.write(json.dumps(result))
        
        await self.flush()

def make_app():
    return tornado.web.Application(
        [
            (r'/', MainHandler),
            (r'/api/bypass', BypassHandler),
        ],
        debug=tornado.options.options.debug,
    )

async def main():
    tornado.options.parse_command_line()
    
    use_xvfb = tornado.options.options.xvfb
    if use_xvfb and platform.system() != 'Linux':
        raise RuntimeError('The xvfb option only works on Linux')
    
    app = make_app()
    app.listen(tornado.options.options.port)
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())