from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
import json
import time


def load_keywords(path="keywords.json"):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["keywords"]
    except Exception:
        return ["test"]


def process_applications(driver, wait, keywords):
    count = 0
    apps = driver.find_elements(By.XPATH, '//h3[contains(text(), "成员申请书来自")]')
    for idx, app in enumerate(apps, 1):
        try:
            table = app.find_element(By.XPATH, './following-sibling::table[1]')
            text = table.find_element(By.XPATH, './/tr[1]/td[2]').text.strip()
            user_links = app.find_elements(By.CSS_SELECTOR, 'span.printuser a')
            user = user_links[-1].text.strip() if user_links else ""
            print(f"申请{idx} 用户:{user} 正文:{text}")
            matched = any(k.lower() in text.lower() for k in keywords)
            if matched:
                btn = table.find_element(By.XPATH, './/a[contains(@onclick, "accept") and contains(@class, "btn-primary")]')
                print("已批准")
            else:
                btn = table.find_element(By.XPATH, './/a[contains(@onclick, "decline") and contains(@class, "btn-danger")]')
                print("已拒绝")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1)
            try:
                confirm = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@value="发送决定"]')))
                driver.execute_script("arguments[0].click();", confirm)
                time.sleep(2)
            except Exception:
                pass
            count += 1
        except Exception as e:
            print(f"处理出错: {e}")
    return count


def load_config(path="config.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def wait_and_click(driver, wait, by, value, timeout=10):
    el = wait.until(EC.element_to_be_clickable((by, value)), timeout)
    driver.execute_script("arguments[0].click();", el)
    return el


def wait_and_send_keys(driver, wait, by, value, keys, timeout=10):
    el = wait.until(EC.element_to_be_clickable((by, value)), timeout)
    el.send_keys(keys)
    return el


def login_and_monitor(username, password, url, keywords, interval=60):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        orig = driver.current_window_handle
        wait_and_click(driver, wait, By.LINK_TEXT, "登入")
        if len(driver.window_handles) > 1:
            for h in driver.window_handles:
                if h != orig:
                    driver.switch_to.window(h)
                    break
        wait_and_send_keys(driver, wait, By.NAME, "login", username)
        wait_and_send_keys(driver, wait, By.NAME, "password", password)
        wait_and_click(driver, wait, By.XPATH, "//button[contains(text(), '登入')] | //input[@type='submit' and @value='登入']")
        driver.switch_to.window(orig)
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '仪表板')]")), 10)
        except Exception:
            pass
        round_num = 1
        while True:
            print(f"第{round_num}轮检查")
            if not ensure_application_page(driver, wait):
                print("未能进入申请书页面")
                break
            n = process_applications(driver, wait, keywords)
            print(f"本轮处理{n}个申请")
            print("刷新页面并重新进入申请书")
            driver.refresh()
            ensure_application_page(driver, wait)
            print(f"等待{interval}秒\n")
            WebDriverWait(driver, interval).until(lambda d: False, "等待间隔结束")
            round_num += 1
    except KeyboardInterrupt:
        print("用户中断，退出")
    except Exception as e:
        print(f"错误: {e}")
    finally:
        input("按Enter键关闭浏览器...")
        driver.quit()


def ensure_application_page(driver, wait):
    try:
        h1 = driver.find_element(By.XPATH, '//h1[contains(text(), "申请书")]')
        if h1:
            return True
    except Exception:
        pass
    try:
        member_btn = wait.until(EC.element_to_be_clickable((By.ID, "first-members")))
        driver.execute_script("arguments[0].click();", member_btn)
        time.sleep(1)
    except Exception:
        pass
    try:
        app_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="second-members"]/ul[2]/li[3]/a')))
        driver.execute_script("arguments[0].click();", app_btn)
        time.sleep(1)
    except Exception:
        pass
    try:
        h1 = driver.find_element(By.XPATH, '//h1[contains(text(), "申请书")]')
        if h1:
            return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    config = load_config("config.json")
    login_and_monitor(
        config["username"],
        config["password"],
        config["url"],
        config["keywords"],
        config.get("interval", 60)
    )


