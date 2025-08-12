# Anime Crawler
Программа для автоматического скачивания изображений персонажей аниме с MyAnimeList.

# Использование
## Автоматический режим запуска с помощью исполняемого файла
0) Перейдите в [раздел релизов](https://github.com/Altryd/anime-club-crawler/releases) и найдите [самую новую версию программы](https://github.com/Altryd/anime-club-crawler/releases/latest)
1) Загрузите файлы anime_urls.txt, config.json, AnimeCharacterScraper.exe и переместите их в одну и ту же папку на своем компьютере
2) В файле anime_urls.txt укажите ссылки на аниме с сайта MAL, с которых хотите загрузить картинки персонажей.

Формат:
```chatinput
https://myanimelist.net/anime/5680/K-On
https://myanimelist.net/anime/59277/Kanojo_Okarishimasu_4th_Season
https://myanimelist.net/anime/53065/Sono_Bisque_Doll_wa_Koi_wo_Suru_Season_2
https://myanimelist.net/anime/39486/Gintama__The_Final
```
**Каждая ссылка должна располагаться на отдельной строчке**

3) *(опционально)* Укажите в файле config.json максимальное количество загружаемых персонажей для каждого аниме.
Стандартное значение: `"num_characters": 15`
4) Запустите программу с помощью командной строки: 
``AnimeCharacterScraper.exe``



## Запуск из исходного кода
```bash
# Клонировать репозиторий
git clone https://github.com/ваш-username/anime-character-scraper.git
cd anime-character-scraper

# Создать виртуальное окружение (либо можно использовать anaconda)
python -m venv venv
venv\Scripts\activate  # Windows
# или для Linux:
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Запустить
python crawler.py
```
