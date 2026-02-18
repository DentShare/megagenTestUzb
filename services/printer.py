import logging
import asyncio
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
from config import config

logger = logging.getLogger(__name__)

def generate_qr_code(order_id: int) -> Image.Image:
    """Generate QR code image for order ID"""
    qr = qrcode.QRCode(
        version=1,
        box_size=6,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L
    )
    qr.add_data(f"ORDER_{order_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def generate_qr_from_data(data: str, size: int = 200) -> Image.Image:
    """Генерирует QR-код из произвольной строки."""
    qr = qrcode.QRCode(
        version=1,
        box_size=6,
        border=2,
        error_correction=qrcode.constants.ERROR_CORRECT_L
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img.resize((size, size), Image.Resampling.LANCZOS)

def generate_collected_label(
    order_id: int,
    doctor_name: str,
    manager_name: str,
    clinic_name: str,
    items_data: list,
    navigator_link: str,
    is_urgent: bool
) -> BytesIO:
    """
    Генерирует этикетку «Собрано» с двумя QR-кодами:
    QR1 — список товаров в виде текста (название — кол-во шт)
    QR2 — ссылка на навигатор до клиники
    """
    width = 500
    height = 700
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 28)
        font_medium = ImageFont.truetype("arial.ttf", 20)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    y = 20
    padding = 20
    
    # Заголовок
    header = f"ЗАКАЗ #{order_id}"
    bbox = draw.textbbox((0, 0), header, font=font_large)
    x = (width - (bbox[2] - bbox[0])) / 2
    draw.text((x, y), header, font=font_large, fill='black')
    y += 45
    
    if is_urgent:
        urgent = "!!! СРОЧНО !!!"
        bbox = draw.textbbox((0, 0), urgent, font=font_medium)
        x = (width - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), urgent, font=font_medium, fill='red')
        y += 35
    
    # Информация о заказе
    draw.text((padding, y), f"Врач: {doctor_name}", font=font_medium, fill='black')
    y += 30
    draw.text((padding, y), f"Менеджер: {manager_name}", font=font_medium, fill='black')
    y += 30
    draw.text((padding, y), f"Клиника: {clinic_name}", font=font_medium, fill='black')
    y += 45
    
    # QR1 — товары в виде текстового списка
    items_text = "\n".join(f"{item['name']} — {item['qty']} шт" for item in items_data)
    qr1 = generate_qr_from_data(items_text, size=180)
    draw.text((padding, y), "QR: Товары в заказе", font=font_small, fill='gray')
    y += 22
    image.paste(qr1, (padding, int(y)))
    qr1_x_end = padding + 180
    
    # QR2 — навигация (справа от QR1)
    qr2 = generate_qr_from_data(navigator_link, size=180)
    qr2_x = width - padding - 180
    draw.text((qr2_x, y - 22), "QR: Навигация", font=font_small, fill='gray')
    image.paste(qr2, (qr2_x, int(y)))
    y += 180 + 25
    
    buf = BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf

def generate_label(order_id: int, doctor_name: str, clinic_name: str, is_urgent: bool) -> BytesIO:
    # 58mm printer usually has ~384 dots width (at 203 DPI) or similar.
    # Let's use 400px width for good readability.
    width = 400
    # Height will be dynamic or fixed. Let's make it fixed enough to fit content + QR code.
    height = 400
    
    # White background
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # Fonts
    # Since we might not have custom fonts, use default or try to load a basic one if we had paths.
    # For this environment, load_default() is safest but it's very small.
    # We will try to create a "large" effect by scaling? Or just drawing text multiple times?
    # Better: Use simple basic font but if possible large.
    # PIL Default font is tiny. Let's assume standard system font is not reliable.
    # We can rely on 'arial.ttf' often being present in Windows/Linux or just fallback.
    try:
        font_large = ImageFont.truetype("arial.ttf", 40)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except IOError:
        # Fallback to default if arial not found (some docker containers)
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw Content
    y_cursor = 20
    
    # Header: Order ID
    header_text = f"ЗАКАЗ #{order_id}"
    # Centering (approximation if no font metrics easy to use)
    # textbbox is available in newer Pillow
    bbox = draw.textbbox((0, 0), header_text, font=font_large)
    text_width = bbox[2] - bbox[0]
    x_pos = (width - text_width) / 2
    draw.text((x_pos, y_cursor), header_text, font=font_large, fill='black')
    y_cursor += 60
    
    # Urgent Mark
    if is_urgent:
        urgent_text = "!!! СРОЧНО !!!"
        bbox = draw.textbbox((0, 0), urgent_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        x_pos = (width - text_width) / 2
        draw.text((x_pos, y_cursor), urgent_text, font=font_medium, fill='red')
        y_cursor += 40
    
    # Doctor and Clinic
    # Left align with padding
    padding = 20
    draw.text((padding, y_cursor), f"Врач:", font=font_small, fill='gray')
    y_cursor += 25
    draw.text((padding, y_cursor), f"{doctor_name}", font=font_medium, fill='black')
    y_cursor += 40
    
    draw.text((padding, y_cursor), f"Клиника:", font=font_small, fill='gray')
    y_cursor += 25
    draw.text((padding, y_cursor), f"{clinic_name}", font=font_medium, fill='black')
    y_cursor += 40
    
    # Generate and paste QR code
    qr_img = generate_qr_code(order_id)
    # Resize QR code to fit label (max 120x120 for 58mm printer)
    qr_size = 120
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    
    # Center QR code horizontally
    qr_x = (width - qr_size) // 2
    qr_y = y_cursor
    image.paste(qr_img, (qr_x, qr_y))
    
    # Save to buffer
    buf = BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)
    return buf


def _print_image_sync(printer, image: Image.Image, printer_type: str, order_id: int):
    """Синхронная функция для печати (выполняется в executor)."""
    try:
        # Печатаем изображение
        printer.image(image)
        
        # Добавляем отступы и обрезку
        printer.cut()
    except Exception as e:
        logger.error("Ошибка при синхронной печати для заказа #%s: %s", order_id, e, exc_info=True)
        raise
    finally:
        # Всегда закрываем соединение
        try:
            printer.close()
        except Exception as close_error:
            logger.warning("Ошибка при закрытии принтера: %s", close_error)


async def send_to_printer(label_buf: BytesIO, order_id: int) -> tuple[bool, str]:
    """
    Отправляет этикетку на xprinter автоматически.
    
    Args:
        label_buf: BytesIO буфер с изображением этикетки
        order_id: ID заказа для логирования
        
    Returns:
        (success: bool, message: str)
    """
    if not config.PRINTER_ENABLED:
        return False, "Принтер отключен в настройках"
    
    if not config.PRINTER_ADDRESS:
        logger.warning("PRINTER_ADDRESS не указан, пропускаем печать")
        return False, "Адрес принтера не указан"
    
    try:
        from escpos.printer import Usb, Network, Serial
        
        # Подготовка изображения для печати
        label_buf.seek(0)
        image = Image.open(label_buf)
        
        # Конвертируем в режим для термопринтера (L = grayscale)
        if image.mode != 'L':
            image = image.convert('L')
        
        # Определяем тип подключения и создаем принтер
        printer = None
        printer_type = config.PRINTER_TYPE.lower()
        
        if printer_type == "usb":
            # USB принтер: адрес должен быть в формате "vendor_id:product_id"
            # Например: "0x04e8:0x0202" или просто путь к устройству
            try:
                if ":" in config.PRINTER_ADDRESS:
                    vendor_id, product_id = config.PRINTER_ADDRESS.split(":")
                    vendor_id = int(vendor_id, 16) if vendor_id.startswith("0x") else int(vendor_id)
                    product_id = int(product_id, 16) if product_id.startswith("0x") else int(product_id)
                    printer = Usb(vendor_id, product_id)
                else:
                    # Попытка использовать адрес как путь к устройству
                    # Для USB это обычно не работает напрямую, но попробуем
                    logger.warning("USB адрес должен быть в формате vendor_id:product_id, получен: %s", config.PRINTER_ADDRESS)
                    return False, "Неверный формат USB адреса. Используйте vendor_id:product_id"
            except (ValueError, AttributeError) as e:
                logger.error("Ошибка подключения к USB принтеру: %s", e)
                return False, f"Ошибка подключения к USB принтеру: {e}"
                
        elif printer_type == "network":
            # Сетевой принтер: адрес - IP адрес
            try:
                printer = Network(host=config.PRINTER_ADDRESS, port=config.PRINTER_NETWORK_PORT)
            except Exception as e:
                logger.error("Ошибка подключения к сетевому принтеру: %s", e)
                return False, f"Ошибка подключения к сетевому принтеру: {e}"
                
        elif printer_type == "serial":
            # Serial принтер: адрес - COM порт (Windows) или /dev/tty* (Linux)
            try:
                printer = Serial(
                    devfile=config.PRINTER_ADDRESS,
                    baudrate=config.PRINTER_SERIAL_BAUDRATE
                )
            except Exception as e:
                logger.error("Ошибка подключения к serial принтеру: %s", e)
                return False, f"Ошибка подключения к serial принтеру: {e}"
        else:
            return False, f"Неподдерживаемый тип принтера: {printer_type}"
        
        if not printer:
            return False, "Не удалось создать подключение к принтеру"
        
        # Печать изображения (синхронные операции выполняем в executor)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _print_image_sync, printer, image, printer_type, order_id)
        
        logger.info("Этикетка для заказа #%s успешно отправлена на принтер (%s)", order_id, printer_type)
        return True, f"Этикетка отправлена на принтер ({printer_type})"
        
    except ImportError:
        logger.error("Библиотека python-escpos не установлена. Установите: pip install python-escpos")
        return False, "Библиотека принтера не установлена"
    except Exception as e:
        logger.error("Ошибка при отправке на принтер для заказа #%s: %s", order_id, e, exc_info=True)
        return False, f"Ошибка печати: {e}"
