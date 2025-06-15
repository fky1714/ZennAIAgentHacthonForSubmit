import pyautogui
import base64
import io


def get_cropped_screenshot_base64():
    """
    1) 全画面をスクリーンショット
    2) 指定した4点(left, top, right, bottom)で切り取り
    3) 半分の大きさにリサイズ
    4) ファイルとして保存せず、そのままBase64エンコードして返却
    """
    # 1) 全画面をスクリーンショット
    screenshot = pyautogui.screenshot()

    # 2) 指定領域で切り取り (PILのcropは (left, upper, right, lower) で定義)
    # left, top, right, bottom = 738, 263, 1191, 712
    left, top, right, bottom = 1010, 263, 1520, 712
    cropped_image = screenshot.crop((left, top, right, bottom))

    # 3) 画像のサイズを1/2に変換
    resized_image = cropped_image.resize(
        (cropped_image.width // 2, cropped_image.height // 2)
    )

    # 4) 画像を一時的にバッファに保存してBase64変換
    buffer = io.BytesIO()
    resized_image.save(buffer, format="PNG")
    buffer.seek(0)
    encoded_string = base64.b64encode(buffer.read()).decode("utf-8")

    return encoded_string
