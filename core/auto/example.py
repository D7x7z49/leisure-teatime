import asyncio
from playwright.async_api import async_playwright, Page
import pyautogui
from PIL import Image
import win32clipboard
import win32con
import io

async def capture_screenshot(page: Page, output_path: str) -> str:
    """使用 Playwright 截取浏览器页面截图并保存到文件。"""
    await page.screenshot(path=output_path)
    return output_path

def copy_image_to_clipboard(image_path: str):
    """将图片复制到系统剪贴板。"""
    image = Image.open(image_path)
    output = io.BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # 跳过 BMP 文件头
    output.close()

    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_DIB, data)
    win32clipboard.CloseClipboard()

def automate_chat_interaction(chat_window_title: str):
    """自动化聊天软件交互：点击聊天框、粘贴图片、发送。"""
    # 定位聊天窗口（假设窗口标题已知）
    try:
        # 使用 pyautogui 定位窗口（需要窗口标题部分匹配）
        chat_window = pyautogui.getWindowsWithTitle(chat_window_title)[0]
        chat_window.activate()  # 激活窗口
    except IndexError:
        raise ValueError(f"未找到标题包含 '{chat_window_title}' 的窗口")

    # 点击聊天输入框（需要根据实际情况调整坐标）
    # 假设聊天框在窗口中心，可以使用 pyautogui 的截图定位功能更精确
    chat_window_center = (chat_window.left + chat_window.width // 2,
                          chat_window.top + chat_window.height // 2)
    pyautogui.click(chat_window_center)

    # 粘贴图片 (Ctrl+V)
    pyautogui.hotkey('ctrl', 'v')

    # 等待一小段时间确保粘贴完成
    pyautogui.sleep(1)

    # 发送消息（假设按 Enter 发送）
    pyautogui.press('enter')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://example.com")  # 替换为您要截图的网页

        # 步骤 1：截图
        screenshot_path = "screenshot.png"
        await capture_screenshot(page, screenshot_path)

        # 步骤 2：复制图片到剪贴板
        copy_image_to_clipboard(screenshot_path)

        # 步骤 3：自动化聊天软件交互
        chat_window_title = "WeChat"  # 替换为实际聊天软件的窗口标题（例如微信、WhatsApp 等）
        automate_chat_interaction(chat_window_title)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
