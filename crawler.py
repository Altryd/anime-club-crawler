import os
from typing import List
import time
import requests
from bs4 import BeautifulSoup
import json
import argparse
import logging
from functools import wraps


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def safe_request_with_retry(
        return_on_error=None,
        retry_statuses: List[int] = [405],
        max_retries: int = 2,
        base_delay: float = 8.0,
        backoff_factor: float = 5.0
):
    """
    Декоратор для безопасного выполнения HTTP-запросов с повторными попытками.

    Args:
        return_on_error: Значение, возвращаемое при ошибке
        retry_statuses: Список HTTP статусов для повтора
        max_retries: Максимальное количество повторов
        base_delay: Базовая задержка в секундах
        backoff_factor: Множитель для увеличения задержки
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    response = func(*args, **kwargs)

                    # Проверяем статус код ответа
                    if hasattr(response, 'status_code') and response.status_code in retry_statuses:
                        url = args[0] if args else "неизвестный URL"

                        if attempt < max_retries:
                            delay = base_delay * (backoff_factor ** attempt)
                            logging.warning(
                                f"Получен статус {response.status_code} для {url}. "
                                f"Повтор через {delay:.1f} сек (попытка {attempt + 1}/{max_retries + 1})"
                            )
                            time.sleep(delay)
                            continue
                        else:
                            logging.error(
                                f"Исчерпаны все попытки для {url}. "
                                f"Последний статус: {response.status_code}"
                            )
                            return return_on_error

                    # Если все OK, возвращаем ответ
                    return response

                except requests.exceptions.RequestException as e:
                    last_exception = e
                    url = args[0] if args else "неизвестный URL"

                    if attempt < max_retries:
                        delay = base_delay * (backoff_factor ** attempt)
                        logging.warning(
                            f"Ошибка запроса к {url}: {e}. "
                            f"Повтор через {delay:.1f} сек (попытка {attempt + 1}/{max_retries + 1})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logging.error(f"Исчерпаны все попытки для {url}. Последняя ошибка: {e}")
                        break

            return return_on_error

        return wrapper

    return decorator


def safe_request(return_on_error=None):
    """Декоратор для безопасного выполнения HTTP-запросов."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.RequestException as e:
                # Получаем URL из аргументов функции (предполагаем, что это первый аргумент)
                url = args[0] if args else "неизвестный URL"
                logging.error(f"Ошибка при запросе {url}: {e}")
                return return_on_error
        return wrapper
    return decorator


def load_config(config_file='config.json'):
    """Загружает настройки из JSON файла."""
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        logging.warning(f"Файл конфигурации {config_file} не найден. Используем значения по умолчанию.")
        return {
            "num_characters": 15,
            "anime_urls_file": None
        }


@safe_request_with_retry(return_on_error=(None, None))
def create_save_folder(anime_url):
    """Создаёт папку с именем аниме на основе URL."""
    # Извлекаем имя аниме из ссылки на Characters & Staff
    response = requests.get(anime_url)
    response.raise_for_status()  # проверяем на HTTP ошибки
    soup = BeautifulSoup(response.text, 'lxml')
    nav_div = soup.find('div', id='horiznav_nav')
    characters_link = nav_div.find('a', string='Characters & Staff')
    if characters_link:
        anime_name = characters_link['href'].split('/')[-2].replace("_", " ").title().replace(" ", "_")
    else:
        anime_name = "unknown_anime"
    main_folder = f"titles/{anime_name}"
    scene_folder = f"{main_folder}/scene"
    save_folder = f"{main_folder}/char"
    if not os.path.exists(save_folder):
        os.makedirs(scene_folder)
        os.makedirs(save_folder)
    return save_folder, characters_link['href']


@safe_request_with_retry(return_on_error=None)
def extract_character_links(characters_url):
    """Извлекает ссылки на страницы персонажей."""
    response = requests.get(characters_url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    character_tables = soup.find_all('table', class_='js-anime-character-table')
    character_links = []
    for table in character_tables:
        character_link = table.find('a', href=True)
        if character_link and '/character/' in character_link['href']:
            character_links.append(character_link['href'])
    return character_links


@safe_request_with_retry(return_on_error=None)
def download_character_image(character_url, save_folder):
    """Скачивает изображение персонажа и сохраняет его с именем персонажа."""
    session = requests.Session()
    response = session.get(character_url)
    response.raise_for_status()
    character_soup = BeautifulSoup(response.text, 'lxml')

    name_tag = character_soup.find('h1', class_='title-name')
    character_name = (name_tag.get_text(strip=True).replace(" ", "_")
                      .replace("/", "_").replace("\"", "")) if name_tag else \
        character_url.split("/")[-1]

    img_tag = character_soup.find('img', class_='portrait-225x350')
    if img_tag and 'data-src' in img_tag.attrs:
        img_url = img_tag['data-src']
        try:
            img_response = session.get(img_url)
            img_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка при запросе {img_url}: {e}")
        else:
            file_path = os.path.join(save_folder, f"{character_name}.jpg")
            with open(file_path, 'wb') as f:
                f.write(img_response.content)
            logging.info(f"Скачано: {character_name}.jpg")
    else:
        logging.warning(f"Изображение для {character_name} не найдено")


def save_links_to_file(character_links, anime_url, save_folder):
    """Сохраняет ссылки на персонажей и аниме в текстовый файл."""
    links_file = os.path.join(save_folder, "character_links.txt")
    with open(links_file, 'w', encoding='utf-8') as f:
        f.write(f"{anime_url}\n")
        for link in character_links:
            f.write(f"{link}\n")
    logging.info(f"Ссылки сохранены в {links_file}")


def process_anime(anime_url, num_characters):
    save_folder, characters_url = create_save_folder(anime_url)
    if not characters_url:
        logging.warning(f"Не удалось найти ссылку на Characters & Staff (либо произошла ошибка) для {anime_url}")
        return
    logging.info(f"Ссылка на Characters & Staff: {characters_url}")

    character_links = extract_character_links(characters_url)[:num_characters]

    for character_url in character_links:
        download_character_image(character_url, save_folder)
        time.sleep(1)

    save_links_to_file(character_links, anime_url, save_folder)


def main():
    parser = argparse.ArgumentParser(description="Скрипт для выгрузки изображений персонажей из MyAnimeList")
    parser.add_argument('--anime_url', type=str, help='URL аниме '
                                                      '(используется только если нету файла конфигурации)')
    parser.add_argument('--config', type=str, default='config.json', help='Путь к файлу конфигурации')
    args = parser.parse_args()

    config = load_config(args.config)
    num_characters = config.get('num_characters', 15)
    anime_urls_file = config.get('anime_urls_file', None)

    anime_urls = []
    if anime_urls_file and os.path.exists(anime_urls_file):
        with open(anime_urls_file, 'r', encoding='utf-8') as f:
            anime_urls = [line.strip() for line in f if line.strip() and "https://myanimelist.net" in line]
    elif args.anime_url:
        anime_urls = [args.anime_url]

    if not anime_urls:
        logging.error("Нет URL аниме для обработки. Укажите в конфиге или через аргумент.")
        return

    for url in anime_urls:
        process_anime(url, num_characters)
        logging.info(f"Characters from anime: {url} have been downloaded. Sleeping 5 seconds to avoid anti-DDoS measures")
        time.sleep(20)


if __name__ == "__main__":
    main()
    input("Программа завершена, для выхода нажмите Enter")
