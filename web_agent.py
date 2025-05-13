import undetected_chromedriver as uc
import time
import random
import pickle
import os
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException,StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import quote
from config import (
    keywords,
    comments,
    private_message,
    search_interval,
    comment_interval,
    message_interval,
    max_posts_per_keyword
)
import os

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)


class XHSBot:
    def __init__(self):
        self.driver = self.init_driver()
    def init_driver(self):
        """初始化浏览器"""
        options = uc.ChromeOptions()

        # 只使用add_argument方法添加参数，避免使用add_experimental_option
        options.add_argument("--disable-blink-features=AutomationControlled")

        # 添加以下配置
        driver_executable_path = r"C:\Program Files\Google\chromedriver-win64\chromedriver.exe"  # 替换为实际路径
        browser_executable_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"  # Chrome本体路径

        driver = uc.Chrome(
            options=options,
            driver_executable_path=driver_executable_path,
            browser_executable_path=browser_executable_path
        )

        return driver

    def wait_for_element(self, by, selector, timeout=10):
        """等待元素出现"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except:
            return None

    def random_delay(self, interval):
        """随机延迟"""
        delay = random.uniform(*interval)
        time.sleep(delay)
        return delay

    def save_cookies(self):
        """保存Cookies"""
        with open('cookies.pkl', 'wb') as f:
            pickle.dump(self.driver.get_cookies(), f)
        logging.info("Cookies保存成功")

    def load_cookies(self):
        """带有效性检测的Cookie加载"""
        try:
            self.driver.get('https://www.xiaohongshu.com')
            if os.path.exists('cookies.pkl'):
                with open('cookies.pkl', 'rb') as f:
                    cookies = pickle.load(f)

                # 检查Cookie有效期
                current_time = time.time()
                expiry_times = [c.get('expiry', float('inf')) for c in cookies if 'expiry' in c]
                if expiry_times and min(expiry_times) < current_time:
                    logging.warning("Cookie已过期，需要重新登录")
                    return False

                # 加载前清空旧Cookie
                self.driver.delete_all_cookies()
                for cookie in cookies:
                    # 处理expiry类型，确保是整数
                    if 'expiry' in cookie and isinstance(cookie['expiry'], float):
                        cookie['expiry'] = int(cookie['expiry'])
                    # 防止domain不匹配导致的问题
                    if 'domain' in cookie:
                        del cookie['domain']
                    try:
                        self.driver.add_cookie(cookie)
                    except Exception as e:
                        logging.warning(f"无法添加Cookie: {str(e)}")

                self.driver.refresh()
                self.random_delay((3, 5))

                # 验证登录状态
                if "登录" not in self.driver.title:
                    logging.info("Cookies登录成功")
                    return True
                else:
                    logging.warning("Cookies已失效，需要重新登录")
                    return False
            return False
        except Exception as e:
            logging.error(f"加载Cookies失败: {str(e)}")
            return False

    def manual_login(self):
        """处理现代验证流程的登录"""
        self.driver.get("https://www.xiaohongshu.com")

        # 等待用户完成验证
        input("请完成以下步骤后按回车键继续：\n"
              "1. 点击页面上的『登录』按钮\n"
              "2. 选择扫码登录或短信验证\n"
              "3. 完成手机端验证\n"
              "4. 确保页面跳转到首页\n"
              "完成后请在此按回车...")

        # 二次验证Cookie有效性
        if "发现" in self.driver.title or "小红书" in self.driver.title:
            self.save_cookies()
            logging.info("登录状态已保存")
            return True
        else:
            logging.error("登录验证失败，请检查网络或验证方式")
            return False

    def get_qrcode_url(self):
        """提取登录二维码URL（需在手动登录前调用）"""
        try:
            qrcode_img = self.driver.find_element(
                By.XPATH, "//img[contains(@src,'qrcode')]"
            )
            return qrcode_img.get_attribute('src')
        except NoSuchElementException:
            logging.error("未找到二维码元素，可能页面改版")
            return None

    def handle_sms_login(self):
        """短信验证流程辅助"""
        try:
            # 点击短信登录
            self.driver.find_element(By.XPATH, "//span[contains(text(),'短信登录')]").click()

            # 输入手机号
            phone_input = self.driver.find_element(By.NAME, 'mobile')
            phone = input("请输入手机号: ")
            phone_input.send_keys(phone)

            # 触发验证码
            self.driver.find_element(By.XPATH, "//button[contains(.,'获取验证码')]").click()

            # 用户手动输入验证码
            code = input("请输入6位短信验证码: ")
            self.driver.find_element(By.NAME, 'code').send_keys(code)

            # 提交登录
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            return True
        except Exception as e:
            logging.error(f"短信登录辅助失败: {str(e)}")
            return False

    def check_login_status(self):
        """验证当前登录状态"""
        try:
            self.driver.refresh()
            self.random_delay((2, 3))
            # 如果有登录/注册按钮，说明未登录
            login_buttons = self.driver.find_elements(By.XPATH,
                                                      "//div[contains(text(),'登录') or contains(text(),'注册')]")
            if login_buttons:
                return False
            return True
        except Exception as e:
            logging.error(f"检查登录状态出错: {str(e)}")
            return False

    def check_risk_warning(self):
        """检测风控提示"""
        try:
            warnings = self.driver.find_elements(
                By.XPATH, "//*[contains(text(),'操作频繁') or contains(text(),'异常') or contains(text(),'验证')]"
            )
            if warnings:
                logging.warning("检测到风控提示，建议暂停运行12小时")
                return True
            return False
        except Exception:
            return False

    def search_keyword(self, keyword):
        """执行搜索"""
        try:
            # 直接使用搜索URL而不是尝试定位搜索框
            encoded_keyword = quote(keyword)
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_explore_feed"
            self.driver.get(search_url)
            logging.info(f"已搜索关键词: {keyword}")
            self.random_delay(search_interval)

            # 检查风控
            if self.check_risk_warning():
                logging.warning("搜索后检测到风控，中止操作")
                return False

            # 滚动加载内容
            self.scroll_page()
            return True
        except Exception as e:
            logging.error(f"搜索失败: {str(e)}")
            return False

    def scroll_page(self):
        """滚动页面加载更多内容"""
        last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        scroll_attempts = 0

        while scroll_attempts < 3:  # 最多滚动3次
            self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            self.random_delay((2, 3))
            new_height = self.driver.execute_script("return document.documentElement.scrollHeight")

            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

    def get_post_links(self):
        """获取帖子链接"""
        try:
            # 基于提供的HTML分析，更新XPath选择器
            selectors = [
                "//a[contains(@href,'/search_result/')]",  # 新的链接格式
                "//div[contains(@class,'cover mask')]//a",  # 尝试基于样式类找到元素
                "//a[@class='cover mask ld']",  # 直接匹配样式类
                "//a[contains(@target,'_self')]"  # 备用选择器
            ]

            found_links = []

            # 尝试每个选择器
            for selector in selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    if links:
                        logging.info(f"使用选择器 '{selector}' 找到 {len(links)} 个链接")

                        # 记录原始链接以便调试
                        for i, link in enumerate(links[:5]):  # 只记录前5个用于调试
                            href = link.get_attribute('href')
                            logging.info(f"链接 {i + 1}: {href}")

                        found_links.extend(links)
                        break
                except Exception as e:
                    logging.warning(f"使用选择器 '{selector}' 时出错: {str(e)}")

            # 如果上面的选择器都失败了，尝试使用CSS选择器
            if not found_links:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, "a.cover.mask")
                    if links:
                        logging.info(f"使用CSS选择器 'a.cover.mask' 找到 {len(links)} 个链接")
                        found_links.extend(links)
                except Exception as e:
                    logging.warning(f"使用CSS选择器时出错: {str(e)}")

            # 提取有效的链接
            valid_posts = []
            for link in found_links:
                try:
                    href = link.get_attribute('href')
                    if href and '/search_result/' in href:
                        valid_posts.append(href)
                except:
                    continue

            if not valid_posts:
                # 最后的尝试：直接用JavaScript提取所有链接
                try:
                    all_links = self.driver.execute_script(
                        """
                        var links = [];
                        var elements = document.getElementsByTagName('a');
                        for (var i = 0; i < elements.length; i++) {
                            if (elements[i].href && elements[i].href.includes('/search_result/')) {
                                links.push(elements[i].href);
                            }
                        }
                        return links;
                        """
                    )
                    logging.info(f"使用JavaScript找到 {len(all_links)} 个链接")
                    valid_posts.extend(all_links)
                except Exception as e:
                    logging.error(f"JavaScript提取链接失败: {str(e)}")

            # 去重
            valid_posts = list(set(valid_posts))

            if valid_posts:
                logging.info(f"找到 {len(valid_posts)} 个有效帖子链接")
                # 记录几个示例链接
                for i, url in enumerate(valid_posts[:3]):
                    logging.info(f"示例链接 {i + 1}: {url}")
            else:
                logging.warning("未找到任何符合条件的帖子链接")

            return valid_posts[:max_posts_per_keyword]  # 限制处理数量
        except Exception as e:
            logging.error(f"获取链接失败: {str(e)}")
            return []

    def comment_post(self, post_url):
        try:
            self.driver.get(post_url)
            self.random_delay((3, 5))

            # 滚动到评论区域
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.8);")
            self.random_delay((2, 3))

            # 获取评论内容
            post_info = self.extract_post_content()
            comment = random.choice(comments)

            logging.info(f"准备发表评论: {comment}")

            try:
                # 等待评论框出现
                comment_box = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "content-textarea"))
                )

                # 滚动到评论框位置
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                    comment_box
                )
                self.random_delay((1, 2))

                # 使用 ActionChains 输入评论（方法3）
                ActionChains(self.driver).move_to_element(comment_box).click().perform()
                self.random_delay((0.5, 1))

                # 清除已有内容
                action = ActionChains(self.driver)
                action.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                self.random_delay((0.3, 0.7))
                action.send_keys(Keys.DELETE).perform()
                self.random_delay((0.3, 0.7))

                # 输入评论字符
                for char in comment:
                    ActionChains(self.driver).send_keys(char).pause(
                        random.uniform(0.05, 0.15)
                    ).perform()

                self.random_delay((1, 2))

                # 获取输入框中的内容确认是否输入成功
                entered_text = self.driver.execute_script(
                    "return document.getElementById('content-textarea').innerText;"
                )

                if not entered_text:
                    logging.error("输入失败，评论框中无内容")
                    return False

                logging.info(f"成功输入文字: {entered_text[:30]}")

                # 查找发送按钮
                button_locators = [
                    "//div[contains(@class,'input-box')]//button[contains(@class,'submit')]",
                    "//button[contains(@class,'submit') and normalize-space()='发送']",
                    "//button[normalize-space()='发送']",
                    "//div[contains(@class,'interact-container')]//button[not(@disabled)]",
                ]

                submit_btn = None
                for selector in button_locators:
                    try:
                        submit_btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                        if submit_btn:
                            logging.info(f"找到发送按钮，使用选择器: {selector}")
                            break
                    except:
                        continue

                # 备用方式查找按钮
                if not submit_btn:
                    try:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR,
                                                            ".interact-container button, .buttons button, .engage-bar-style button")
                        for btn in buttons:
                            if "发送" in btn.text or "submit" in btn.get_attribute("class"):
                                submit_btn = btn
                                logging.info("通过周围按钮找到了发送按钮")
                                break
                    except:
                        pass

                if not submit_btn:
                    logging.warning("未找到发送按钮，尝试截图并使用 Enter 提交")
                    self.driver.save_screenshot(f"missing_button_{int(time.time())}.png")

                    try:
                        ActionChains(self.driver).move_to_element(comment_box).click().send_keys(
                            Keys.ENTER).perform()
                        logging.info("尝试使用 Enter 键提交评论")
                        self.random_delay((2, 3))
                    except:
                        pass

                    return False

                # 使用 JS 点击发送按钮
                self.driver.execute_script("arguments[0].click();", submit_btn)
                logging.info(f"已点击发送按钮，评论: {comment}")

                self.random_delay((3, 5))
                return True

            except Exception as e:
                logging.error(f"评论失败: {str(e)}")
                self.driver.save_screenshot(f"error_comment_{int(time.time())}.png")
                return False

        except Exception as e:
            logging.error(f"评论过程出现严重错误: {str(e)}")
            self.driver.save_screenshot(f"critical_error_{int(time.time())}.png")
            return False

    # Helper method to split text into natural chunks
    def _split_text_into_chunks(self, text):
        """将文本分成自然的块，模拟人类输入"""
        # 按标点符号和空格拆分
        if len(text) <= 5:
            return [text]  # 短文本不拆分

        # 找到自然断句点
        separators = ['.', '。', '!', '！', '?', '？', ',', '，', '、', ';', '；', ' ']
        chunks = []
        current_chunk = ""

        for char in text:
            current_chunk += char
            # 在分隔符处或随机位置断句
            if (char in separators or (len(current_chunk) > 5 and random.random() < 0.2)):
                chunks.append(current_chunk)
                current_chunk = ""

        if current_chunk:  # 添加最后一块
            chunks.append(current_chunk)

        return chunks

    def execute_main_workflow(self):
        """执行主要业务逻辑"""
        processed_count = 0
        max_total_posts = 15  # 一次运行最多处理的帖子总数

        for keyword in keywords:
            logging.info(f"开始处理关键词: {keyword}")
            if not self.search_keyword(keyword):
                continue

            post_urls = self.get_post_links()
            valid_posts = len(post_urls)
            logging.info(f"找到{valid_posts}个有效帖子")

            for i, url in enumerate(post_urls[:max_posts_per_keyword]):
                # 检查总处理数量限制
                if processed_count >= max_total_posts:
                    logging.info(f"已达到最大处理数量({max_total_posts})，本次运行结束")
                    return

                logging.info(f"正在处理帖子 {i + 1}/{valid_posts}: {url}")
                if self.comment_post(url):
                    # 评论成功后等待一段时间再私信
                    self.random_delay((5, 10))


                processed_count += 1
                # 帖子间添加较长随机间隔，避免操作过于频繁
                self.random_delay((15, 30))

    def extract_post_content(self):
        """提取帖子内容"""
        try:
            # 等待内容加载
            self.random_delay((2, 3))

            # 提取标题
            try:
                title_elements = self.driver.find_elements(By.XPATH, "//h1")
                title = title_elements[0].text if title_elements else ""
            except:
                title = ""
                logging.info("无法提取标题")

            # 提取正文内容
            try:
                content_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'content')]")
                content = "\n".join([elem.text for elem in content_elements if elem.text])
                if not content:
                    # 备用选择器
                    content_elements = self.driver.find_elements(By.XPATH, "//article")
                    content = "\n".join([elem.text for elem in content_elements if elem.text])
            except:
                content = ""
                logging.info("无法提取正文内容")

            # 提取用户名
            try:
                username_elements = self.driver.find_elements(By.XPATH, "//span[contains(@class, 'user-name')]")
                username = username_elements[0].text if username_elements else ""
            except:
                username = ""
                logging.info("无法提取用户名")

            post_info = {
                "title": title,
                "content": content,
                "username": username
            }

            logging.info(f"提取的帖子内容: 标题长度:{len(title)}字符, 内容长度:{len(content)}字符")
            return post_info

        except Exception as e:
            logging.error(f"提取帖子内容失败: {str(e)}")
            return {"title": "", "content": "", "username": ""}

    def run(self):
        """主运行流程"""
        try:
            # 尝试加载Cookie
            # if not self.load_cookies():
            if not self.manual_login():
                logging.critical("登录失败，终止程序")
                self.driver.quit()
                return

            # 二次验证登录状态
            if not self.check_login_status():
                logging.critical("登录状态验证失败，终止程序")
                self.driver.quit()
                return

            # 执行主业务逻辑
            self.execute_main_workflow()

        except Exception as e:
            logging.critical(f"运行过程中发生严重错误: {str(e)}")
        finally:
            # 确保关闭浏览器
            self.driver.quit()
            logging.info("程序已完成运行")


if __name__ == "__main__":
    bot = XHSBot()
    bot.run()