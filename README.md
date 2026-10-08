# Сайт «Кто-что»

Статический сайт программы «Кто-что» (в разработке): протокол договорённостей из записей
звонков для отделов продаж из 1–5 человек. Адрес — https://sergiothefirst.github.io/kto-chto/

## Команды

```
python build.py                 # site/ + site.json -> _site/
python tests/check.py --draft   # проверки; без --draft — как в CI (требует заданную почту)
python tools/shots.py           # снимки 360/430/721/768/1440 в _shots/
python tools/shots.py og        # перерисовать site/static/og.png из tools/og.html
python -m http.server -d _site  # просмотр; ссылки строятся от base_url, поэтому для
                                # локального просмотра удобнее tools/shots.py
```

Нужен только Python 3.12 (стандартная библиотека) и, для снимков, Chrome или Edge.

## Устройство

- `site/layout.html` — общая шапка и подвал; `site/pages/*.html` — страницы (шапка-комментарий
  `title`/`description`, дальше HTML). Подстановки `${имя}` — из `site.json` → `vars`.
- `site/static/` — CSS, шрифты, иконка, картинка превью; копируется как есть.
- `site.json` — адрес сайта, почта, ссылка предзаказа (пусто — кнопка «Сообщить о выходе»),
  цены и источник каждого числа.
- `tests/check.py` — гейт выкладки: метаданные, локальность ресурсов, доступность, живые ссылки,
  sitemap, словарь запретов, цены только из `site.json`, пример помечен выдуманным.
- `.github/workflows/pages.yml` — сборка → проверки → GitHub Pages.

## Правила

Ничего не выдумывать: число — только с источником в `site.json`, пример — с пометкой
«выдуман», инструкции по АТС — по официальной документации со ссылкой и датой сверки.
Ни скриптов, ни счётчиков, ни форм, ни сторонних ресурсов.

## Лицензии чужого

- Шрифты — подмножества Fira Sans Extra Condensed Black (заголовки; Mozilla и Telefonica) и Golos Text (текст; The Golos Text Project Authors), оба SIL OFL 1.1, см. `site/static/fonts/`.
- Набор проверок `tests/check.py` устроен по образцу `landing/tests/check.py` проекта
  [amanu](https://github.com/gsamat/amanu) (MIT, © Samat Galimov); код написан заново.
