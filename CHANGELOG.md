# Changelog / История изменений

All notable changes to this project are documented here. · Здесь описаны все заметные изменения проекта.

## [1.0.1] - 2026-10-28

### Added / Добавлено
- 🌐 **English / Русский interface** with a language button in the header. English is the default and the choice is remembered (`~/.lort_unlocker.json`); `--lang en|ru` overrides it.
  **Интерфейс English / Русский** с кнопкой языка в шапке. По умолчанию English, выбор запоминается; `--lang en|ru` переопределяет его.

### Changed / Изменено
- 🎨 **Redesigned buttons**: rounded, colour-coded (green Unlock, red Lock, gold Unlock all), with icons, hover highlight and a press effect.
  **Новые кнопки**: скруглённые, цветные по смыслу (зелёная «Разблокировать», красная «Заблокировать», золотая «Разблокировать всех»), с иконками, подсветкой при наведении и эффектом нажатия.
- README is now bilingual: `README.md` (English) and `README.ru.md` (Русский) with a language switcher.
  README теперь двуязычный: `README.md` (English) и `README.ru.md` (Русский) с переключателем.

### Fixed / Исправлено
- The window no longer resizes or "jumps" when switching languages: button and label widths are fixed to the longest text of both languages.
  Окно больше не меняет размер и не «прыгает» при смене языка: ширина кнопок и подписей зафиксирована по самому длинному тексту из двух языков.

## [1.0.0] - 2026-10-28

First release / Первый релиз.

- GUI with hero portraits, a status badge and an Unlock / Lock button under each hero.
  GUI с портретами героев, статусом и кнопкой «Разблокировать» / «Заблокировать» под каждым.
- Automatic timestamped backup before every write and a Restore button.
  Автоматический бэкап с меткой времени перед каждой записью и кнопка «Откатить».
- Refuses to write while the game is running; auto-detects saves on Windows and Linux/Proton.
  Не пишет в сохранение, пока запущена игра; автопоиск сохранений на Windows и Linux/Proton.
- CLI mode: `--list`, `--hero`, `--all`, `--lock`, `--dry-run`, `--restore`.
  Консольный режим: `--list`, `--hero`, `--all`, `--lock`, `--dry-run`, `--restore`.
- Portraits are extracted from your own game copy via retoc (not shipped).
  Портреты извлекаются из вашей копии игры через retoc (в репозиторий не входят).
