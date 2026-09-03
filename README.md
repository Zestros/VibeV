# Vibe Viewer

Универсальный файловый просмотрщик на Python и PyQt6. Слева находится встроенная область
просмотра, справа — дерево файлов с сортировкой по имени, размеру, типу и дате. Приложение
не запускает Word, LibreOffice, браузер, медиаплеер, архиватор или другие внешние программы.

## Возможности

- подсветка исходного кода и просмотр обычного/структурированного текста;
- таблицы CSV, TSV, XLS, XLSX, XLSM, ODS;
- изображения, включая WebP, AVIF, HEIC, TIFF, PSD и SVG;
- PDF, XPS, EPUB, MOBI, FB2 и CBZ с навигацией по страницам;
- DOC/DOCX, PPT/PPTX, RTF, ODT и ODP;
- встроенное аудио и видео через Qt Multimedia;
- безопасный список содержимого ZIP, TAR, GZ, BZ2, XZ и 7Z;
- SQLite, NumPy, Parquet, Feather, HDF5 и DICOM;
- EML, MBOX, VCF, ICS, TTF и OTF;
- RAW/HDR-изображения, RAR/ISO/DEB/RPM и современные потоки Zstandard/LZ4;
- FITS, NetCDF, MATLAB, SPSS, DBF, ORC, Avro и XLSB;
- GPX, KML/KMZ, Shapefile, GML и WKT;
- субтитры, плейлисты, 3D-модели, PCAP и структуры PE/ELF/Java/WASM;
- Outlook MSG/PST, web-шрифты и BitTorrent-метаданные;
- HEX-предпросмотр любого неизвестного файла;
- автоматический список реально зарегистрированных расширений;
- встроенный выбор папки или файла без macOS-фильтра, скрывающего файлы.

Полный список показывается в приложении через **Вид → Поддерживаемые форматы**.

## Быстрый запуск на macOS/Linux

```bash
cd /Users/zestros/my_prog/vibe
make install
make run
```

Команда `make install` создаёт локальное окружение `.venv` и устанавливает все зависимости.
Повторный запуск выполняется через `make run` или `./scripts/run.sh`.

## Чистая Ubuntu

```bash
git clone <repository-url>
cd vibe
make ubuntu-install
make run
```

Установщик добавляет шрифты и необходимые графические библиотеки Qt. Мультимедиа
декодируется встроенным backend-модулем Qt/FFmpeg, без отдельной программы `ffmpeg`.
Все Python-зависимости перечислены в `requirements.txt`. В виртуальных машинах приложение
по умолчанию отключает проблемное аппаратное декодирование. Чтобы явно вернуть его,
запустите `VIBE_VIEWER_HARDWARE_ACCELERATION=1 make run`.

## Сборка

```bash
make build
```

Готовый wheel появится в `dist/`. Доступные команды можно посмотреть через `make`.

## Проверка через OrbStack/Docker

Контейнер используется для воспроизводимой проверки Ubuntu без подключения графического
окна macOS:

```bash
docker compose build tests
docker compose run --rm tests
docker compose run --rm gui-smoke
```

Для визуальной проверки настоящего X11-интерфейса выполните `make screenshot-ubuntu`.
Снимок появится в `work/ubuntu-ui.png`.

Основное GUI удобнее запускать локально из `.venv`. На Linux-хосте контейнер можно
подключить к X11/Wayland, но это зависит от окружения рабочего стола.

## Демонстрационные файлы

```bash
.venv/bin/python scripts/generate_samples.py
.venv/bin/vibe-viewer
```

Откройте `samples/generated`. Скрипт создаёт текст, JSON, YAML, HTML, CSV, ZIP, TAR.GZ,
SQLite, EML, VCF, ICS, WAV, PNG, WebP, PDF, DOCX, XLSX, PPTX, NPY и NPZ.
Также создаются доступные без загрузки из сети образцы субтитров, плейлистов, GPX/KML,
3D-моделей, PCAP, WebAssembly, AR/DEB, FITS, NetCDF, MATLAB и современных архивных потоков.

## Тесты

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
make check
```

## Расширение

Каждый тип просмотра является отдельным классом `BaseViewer`. Инструкция и контракт
находятся в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Добавление нового обработчика
не требует изменять главное окно.

## Документация Doxygen

Опциональный пункт задания:

```bash
doxygen Doxyfile
```

Результат появится в `docs/html`.

## Честные ограничения

- Office-файлы показываются как структурированное содержимое, а не как точная копия
  интерфейса Word или PowerPoint.
- Старые бинарные DOC/PPT поддерживаются экспериментально.
- Набор воспроизводимых мультимедиаформатов зависит от кодеков GStreamer.
- Повреждённый или неподдерживаемый файл автоматически переходит в безопасный HEX-режим.
