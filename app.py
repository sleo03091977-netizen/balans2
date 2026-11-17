import os
import uuid
import sqlite3
from functools import wraps
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    session, send_file, abort, Response
)
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'educraft.db')
UPLOAD_PDF_DIR = os.path.join(BASE_DIR, 'uploads', 'pdfs')
UPLOAD_HTML_DIR = os.path.join(BASE_DIR, 'uploads', 'html')

os.makedirs(UPLOAD_PDF_DIR, exist_ok=True)
os.makedirs(UPLOAD_HTML_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'educraft-dev-secret-key-change-in-prod-2026')
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # Лимит загрузки файлов: 32 МБ


# =========================================================================
# РАБОТА С БАЗОЙ ДАННЫХ SQLITE
# =========================================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def generate_built_in_demo_pdf_bytes() -> bytes:
    """Генерирует валидный 3-страничный демо-PDF для предустановленного урока."""
    pages_content = [
        '\n'.join([
            'BT /F2 20 Tf 50 760 Td (VECTOR ACADEMY - UX/UI DESIGN GUIDE) Tj ET',
            'BT /F1 12 Tf 50 732 Td (Module 1, Lesson 3: Modular Grids, Typography & Visual Hierarchy) Tj ET',
            '0.85 0.87 0.92 RG 50 718 m 545 718 l S',
            'BT /F2 14 Tf 50 685 Td (1. Core Principles of Web Typography) Tj ET',
            'BT /F1 11 Tf 50 662 Td (Typography represents up to 85% of any educational interface.) Tj ET',
            'BT /F1 11 Tf 50 644 Td (A well-structured type scale turns complex lectures into clear guides:) Tj ET',
            'BT /F1 11 Tf 65 620 Td (- Optimal line length: 55 to 75 characters per line.) Tj ET',
            'BT /F1 11 Tf 65 602 Td (- Body text line-height: 1.45 to 1.65 relative to font size.) Tj ET',
            'BT /F1 11 Tf 65 584 Td (- Contrast ratio: minimum 4.5:1 according to WCAG AA standard.) Tj ET',
            'BT /F2 14 Tf 50 545 Td (2. The 8-Point Grid System) Tj ET',
            'BT /F1 11 Tf 50 522 Td (Use multiples of 8px (8, 16, 24, 32, 48, 64) for all paddings,) Tj ET',
            'BT /F1 11 Tf 50 504 Td (margins, card gaps, and button heights across desktop and mobile.) Tj ET',
            'BT /F1 10 Tf 50 60 Td (Protected Course Material - Page 1 of 3) Tj ET',
        ]),
        '\n'.join([
            'BT /F2 18 Tf 50 760 Td (VISUAL HIERARCHY & RESPONSIVE BREAKPOINTS) Tj ET',
            '0.85 0.87 0.92 RG 50 744 m 545 744 l S',
            'BT /F2 14 Tf 50 710 Td (3. Three Levels of Visual Attention) Tj ET',
            'BT /F1 11 Tf 50 686 Td (Level 1 (Primary): Course title, main CTA button, key value metric.) Tj ET',
            'BT /F1 11 Tf 50 668 Td (Level 2 (Secondary): Module subtitles, lesson duration, category tags.) Tj ET',
            'BT /F1 11 Tf 50 650 Td (Level 3 (Tertiary): Footnotes, metadata, secondary borders.) Tj ET',
            'BT /F2 14 Tf 50 610 Td (4. Standard Responsive Grid Columns) Tj ET',
            'BT /F1 11 Tf 65 586 Td (* Desktop (1280px+): 12-column grid, 24px-32px gutter.) Tj ET',
            'BT /F1 11 Tf 65 568 Td (* Tablet (768px-1024px): 8-column grid, 20px gutter.) Tj ET',
            'BT /F1 11 Tf 65 550 Td (* Mobile (360px-480px): 4-column grid, 16px side margins.) Tj ET',
            'BT /F1 10 Tf 50 60 Td (Protected Course Material - Page 2 of 3) Tj ET',
        ]),
        '\n'.join([
            'BT /F2 18 Tf 50 760 Td (PRACTICAL ASSIGNMENT & CHECKLIST) Tj ET',
            '0.85 0.87 0.92 RG 50 744 m 545 744 l S',
            'BT /F2 14 Tf 50 710 Td (Homework Task for Lesson 3) Tj ET',
            'BT /F1 11 Tf 50 686 Td (1. Create a modular typographic scale in Figma (H1, H2, H3, Body, Caption).) Tj ET',
            'BT /F1 11 Tf 50 668 Td (2. Configure a 12-column desktop frame (1440px) with 80px margins.) Tj ET',
            'BT /F1 11 Tf 50 650 Td (3. Design a course catalog card following the 8pt spacing rule.) Tj ET',
            'BT /F1 11 Tf 50 632 Td (4. Verify text contrast using a contrast checker plugin.) Tj ET',
            'BT /F2 12 Tf 50 585 Td (Security Notice: Unauthorized copying or distribution is prohibited.) Tj ET',
            'BT /F1 10 Tf 50 60 Td (Protected Course Material - Page 3 of 3) Tj ET',
        ]),
    ]

    objects = [None] * 11
    objects[1] = '<< /Type /Catalog /Pages 2 0 R >>'
    objects[2] = '<< /Type /Pages /Kids [5 0 R 7 0 R 9 0 R] /Count 3 >>'
    objects[3] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>'
    objects[4] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>'

    for i, stream_str in enumerate(pages_content):
        page_obj_num = 5 + i * 2
        content_obj_num = 6 + i * 2
        objects[page_obj_num] = (
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            f'/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_obj_num} 0 R >>'
        )
        objects[content_obj_num] = f'<< /Length {len(stream_str)} >>\nstream\n{stream_str}\nendstream'

    pdf = '%PDF-1.4\n'
    offsets = [0] * len(objects)
    for i in range(1, len(objects)):
        offsets[i] = len(pdf)
        pdf += f'{i} 0 obj\n{objects[i]}\nendobj\n'

    xref_offset = len(pdf)
    pdf += f'xref\n0 {len(objects)}\n'
    pdf += '0000000000 65535 f \n'
    for i in range(1, len(objects)):
        pdf += f'{str(offsets[i]).zfill(10)} 00000 n \n'
    pdf += f'trailer\n<< /Size {len(objects)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF'

    return pdf.encode('utf-8')


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            school_name TEXT NOT NULL,
            hero_title TEXT NOT NULL,
            hero_subtitle TEXT NOT NULL,
            hero_cta_text TEXT NOT NULL,
            accent_color TEXT NOT NULL DEFAULT 'indigo',
            contact_email TEXT NOT NULL,
            contact_telegram TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            protect_watermark INTEGER NOT NULL DEFAULT 1,
            protect_blur INTEGER NOT NULL DEFAULT 1,
            protect_shortcuts INTEGER NOT NULL DEFAULT 1,
            sbp_qr_image TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL DEFAULT 0,
            cover_gradient TEXT NOT NULL DEFAULT 'grad-indigo',
            cover_image TEXT NOT NULL DEFAULT '',
            short_description TEXT NOT NULL DEFAULT '',
            full_description TEXT NOT NULL DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id TEXT PRIMARY KEY,
            course_id TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            title TEXT NOT NULL,
            duration TEXT NOT NULL DEFAULT '20 мин',
            is_free INTEGER NOT NULL DEFAULT 0,
            video_url TEXT NOT NULL DEFAULT '',
            content_type TEXT NOT NULL DEFAULT 'text',
            pdf_filename TEXT NOT NULL DEFAULT '',
            pdf_stored_name TEXT NOT NULL DEFAULT '',
            html_filename TEXT NOT NULL DEFAULT '',
            html_stored_name TEXT NOT NULL DEFAULT '',
            enable_code_tab INTEGER NOT NULL DEFAULT 0,
            content TEXT NOT NULL DEFAULT '',
            default_html TEXT NOT NULL DEFAULT '',
            default_css TEXT NOT NULL DEFAULT '',
            default_js TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            purchased_at TEXT NOT NULL,
            PRIMARY KEY (user_id, course_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lesson_progress (
            user_id TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            PRIMARY KEY (user_id, lesson_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS homework_submissions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            lesson_id TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'submitted',
            submitted_at TEXT NOT NULL,
            UNIQUE (user_id, lesson_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
        );
    """)

    # Безопасная миграция для существующей БД без колонок html_filename / html_stored_name
    cols = [row['name'] for row in cur.execute('PRAGMA table_info(lessons)').fetchall()]
    if 'html_filename' not in cols:
        cur.execute("ALTER TABLE lessons ADD COLUMN html_filename TEXT NOT NULL DEFAULT ''")
    if 'html_stored_name' not in cols:
        cur.execute("ALTER TABLE lessons ADD COLUMN html_stored_name TEXT NOT NULL DEFAULT ''")
    s_cols = [row['name'] for row in cur.execute('PRAGMA table_info(settings)').fetchall()]
    if 'sbp_qr_image' not in s_cols:
        cur.execute("ALTER TABLE settings ADD COLUMN sbp_qr_image TEXT NOT NULL DEFAULT ''")

    existing = cur.execute('SELECT COUNT(*) AS cnt FROM settings').fetchone()['cnt']
    if existing == 0:
        cur.execute("""
            INSERT INTO settings (
                id, school_name, hero_title, hero_subtitle, hero_cta_text,
                accent_color, contact_email, contact_telegram, contact_phone,
                protect_watermark, protect_blur, protect_shortcuts, sbp_qr_image
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, '')
        """, (
            'Академия Профессий «Вектор»',
            'Освойте востребованные навыки будущего на практике',
            'Авторские онлайн-курсы с проверкой заданий, закрытыми методическими материалами и бессрочным доступом в личном кабинете.',
            'Выбрать программу обучения',
            'indigo',
            'hello@vector-academy.ru',
            '@vector_school_support',
            '+7 (495) 128-44-90'
        ))

        cur.execute(
            'INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            ('user-admin', 'Алексей Смирнов (Автор школы)', 'admin@vector.ru', generate_password_hash('admin'), 'admin', '2026-01-10')
        )
        cur.execute(
            'INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)',
            ('user-student', 'Мария Соколова', 'student@vector.ru', generate_password_hash('123'), 'student', '2026-02-14')
        )

        courses_seed = [
            (
                'course-1',
                'Основы UX/UI дизайна: от прототипа до дизайн-системы',
                'Дизайн',
                14900,
                'grad-indigo',
                '',
                'Научитесь проектировать удобные интерфейсы в Figma, проводить пользовательские исследования и собирать масштабируемые дизайн-системы.',
                'Практический курс для начинающих дизайнеров и продакт-менеджеров. Вы пройдете полный цикл создания цифрового продукта: от глубинных интервью с пользователями и проектирования пользовательских сценариев (User Flow) до интерактивного прототипирования, типографики, работы с сетками и передачи макетов в разработку.'
            ),
            (
                'course-2',
                'Современный Frontend на JavaScript и Tailwind CSS',
                'Разработка',
                19900,
                'grad-emerald',
                '',
                'Создание быстрых адаптивных веб-приложений, работа с DOM, асинхронными запросами и локальным хранилищем.',
                'Пошаговый курс по современной веб-разработке без лишней теории. Вы научитесь верстать сложные адаптивные интерфейсы, управлять состоянием приложения и интегрировать фронтенд с REST API на Python.'
            ),
            (
                'course-3',
                'Запуск и монетизация онлайн-школы: от идеи до первых продаж',
                'Маркетинг',
                12500,
                'grad-amber',
                '',
                'Упаковка образовательной программы, линейка тарифов, прогрев аудитории и защита авторского контента.',
                'Практическое руководство для экспертов и методистов по запуску собственных образовательных продуктов, настройке воронки продаж и повышению доходимости учеников до конца курса.'
            )
        ]
        cur.executemany(
            'INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            courses_seed
        )

        demo_pdf_stored = 'demo_typography.pdf'
        demo_pdf_path = os.path.join(UPLOAD_PDF_DIR, demo_pdf_stored)
        if not os.path.exists(demo_pdf_path):
            with open(demo_pdf_path, 'wb') as f:
                f.write(generate_built_in_demo_pdf_bytes())

        lessons_seed = [
            (
                'lesson-1-1', 'course-1', 1,
                'Введение в UX-исследования и анализ целевой аудитории',
                '24 мин', 1, '', 'text', '', '', '', '', 0,
                'Пользовательский опыт (UX) начинается задолго до открытия графического редактора. Главная ошибка начинающих дизайнеров — попытка сразу рисовать красивые экраны без понимания реальных задач и болей пользователя.\n\n1. Что такое JTBD (Jobs To Be Done)\nФреймворк «Работа, которая должна быть выполнена» помогает сместить фокус с социально-демографических характеристик на контекст ситуации.\n\n2. Правила проведения глубинного интервью:\n— Задавайте открытые вопросы о прошлом опыте.\n— Не подсказывайте ответы и не защищайте свой интерфейс.\n— Фиксируйте барьеры и моменты непонимания терминологии.',
                '', '', ''
            ),
            (
                'lesson-1-2', 'course-1', 2,
                'Информационная архитектура и проектирование User Flow',
                '32 мин', 0, '', 'text', '', '', '', '', 0,
                'Информационная архитектура определяет, как контент сгруппирован, назван и связан между собой. Хорошая архитектура позволяет пользователю интуитивно находить нужный раздел за 2–3 клика.',
                '', '', ''
            ),
            (
                'lesson-1-3', 'course-1', 3,
                'Модульные сетки, типографика и визуальная иерархия',
                '40 мин', 0, '', 'pdf', 'Методичка_Сетки_и_Типографика.pdf', demo_pdf_stored, '', '', 0,
                'Типографика составляет до 85% любого контентного интерфейса. Изучите прикрепленную защищенную методичку в формате PDF ниже.',
                '', '', ''
            ),
            (
                'lesson-1-4', 'course-1', 4,
                'Практикум: верстка интерактивной карточки тарифа (HTML/CSS/JS)',
                '45 мин', 1, '', 'code', '', '', '', '', 1,
                'В этом практическом уроке вы создадите интерактивную карточку тарифа онлайн-курса с переключением формата обучения и мгновенным расчетом стоимости. Переключитесь на вкладку «Песочница кода».',
                '<div class="landing">\n  <span class="badge">Интенсив 2026</span>\n  <h1>Проектирование интерфейсов с нуля</h1>\n  <p>Практический курс с проверкой домашних заданий.</p>\n  <div class="tariffs">\n    <button class="tariff active" data-price="14900">Базовый — 14 900 ₽</button>\n    <button class="tariff" data-price="24900">С наставником — 24 900 ₽</button>\n  </div>\n  <button id="enrollBtn" class="cta">Записаться за 14 900 ₽</button>\n  <div id="statusMsg" class="status"></div>\n</div>',
                'body { background: #0f172a; color: #f8fafc; font-family: system-ui, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }\n.landing { max-width: 600px; background: #1e293b; border: 1px solid #334155; border-radius: 20px; padding: 36px; text-align: center; }\n.badge { background: rgba(99,102,241,0.2); color: #a5b4fc; padding: 6px 14px; border-radius: 999px; font-size: 13px; font-weight: 600; }\n.tariffs { display: flex; gap: 10px; justify-content: center; margin: 20px 0; }\n.tariff { background: #0f172a; color: #cbd5e1; border: 1px solid #334155; padding: 10px 16px; border-radius: 10px; cursor: pointer; }\n.tariff.active { border-color: #6366f1; color: #fff; }\n.cta { background: #6366f1; color: #fff; border: none; padding: 12px 24px; border-radius: 10px; font-weight: 700; cursor: pointer; }\n.status { margin-top: 14px; color: #34d399; font-weight: 600; }',
                'const tariffs = document.querySelectorAll(".tariff");\nconst enrollBtn = document.getElementById("enrollBtn");\nconst statusMsg = document.getElementById("statusMsg");\nlet price = "14 900 ₽";\ntariffs.forEach(b => b.addEventListener("click", () => {\n  tariffs.forEach(x => x.classList.remove("active"));\n  b.classList.add("active");\n  price = Number(b.dataset.price).toLocaleString("ru-RU") + " ₽";\n  enrollBtn.textContent = "Записаться за " + price;\n}));\nenrollBtn.addEventListener("click", () => {\n  statusMsg.textContent = "Заявка оформлена! Тариф: " + price;\n});'
            ),
            (
                'lesson-2-1', 'course-2', 1,
                'Архитектура SPA и интеграция с Python REST API',
                '35 мин', 1, '', 'code', '', '', '', '', 1,
                'Современные веб-приложения разделяют интерфейс и серверную логику через JSON API на Python (Flask/FastAPI).',
                '<h2>Тест API запроса</h2>\n<button id="pingBtn">Проверить статус сервера</button>\n<pre id="out"></pre>',
                'body { font-family: sans-serif; padding: 24px; background: #f8fafc; }\nbutton { background: #059669; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; }',
                'document.getElementById("pingBtn").onclick = () => {\n  document.getElementById("out").textContent = "Статус: Python Flask Backend активен!";\n};'
            ),
            (
                'lesson-2-2', 'course-2', 2,
                'Асинхронный JavaScript: Promise, async/await и Fetch API',
                '42 мин', 0, '', 'text', '', '', '', '', 0,
                'Работа с внешними API требует корректной обработки состояний загрузки (Loading), успешного ответа (Success) и сетевых ошибок (Error) через блоки try / catch.',
                '', '', ''
            ),
            (
                'lesson-3-1', 'course-3', 1,
                'Проектирование продуктовой матрицы и бесплатного вводного урока',
                '28 мин', 1, '', 'text', '', '', '', '', 0,
                'Бесплатный первый урок — лучший инструмент демонстрации экспертности. Он должен давать ученику быстрый измеримый результат уже за первые 20 минут обучения.',
                '', '', ''
            ),
            (
                'lesson-3-2', 'course-3', 2,
                'Юридическая и техническая защита авторских курсов от сливов',
                '30 мин', 0, '', 'text', '', '', '', '', 0,
                'Комбинация серверной проверки прав доступа, персонализированных водяных знаков с email покупателя и постраничного рендеринга PDF снижает риск несанкционированного распространения материалов.',
                '', '', ''
            )
        ]
        cur.executemany(
            'INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            lessons_seed
        )

        now_str = datetime.now().strftime('%Y-%m-%d')
        cur.executemany(
            'INSERT INTO enrollments (user_id, course_id, purchased_at) VALUES (?, ?, ?)',
            [
                ('user-admin', 'course-1', now_str),
                ('user-admin', 'course-2', now_str),
                ('user-admin', 'course-3', now_str),
                ('user-student', 'course-1', now_str),
            ]
        )
        cur.execute(
            'INSERT INTO lesson_progress (user_id, lesson_id, completed_at) VALUES (?, ?, ?)',
            ('user-student', 'lesson-1-1', now_str)
        )

    conn.commit()
    conn.close()


# =========================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ АВТОРИЗАЦИИ И ПРАВ ДОСТУПА
# =========================================================================

def get_current_user(conn):
    user_id = session.get('user_id')
    if not user_id:
        return None
    row = conn.execute('SELECT id, name, email, role, created_at FROM users WHERE id = ?', (user_id,)).fetchone()
    return dict(row) if row else None


def has_lesson_access(conn, user, lesson_row) -> bool:
    """Серверная проверка: доступен ли урок пользователю."""
    if bool(lesson_row['is_free']):
        return True
    if not user:
        return False
    if user['role'] == 'admin':
        return True
    enrolled = conn.execute(
        'SELECT 1 FROM enrollments WHERE user_id = ? AND course_id = ?',
        (user['id'], lesson_row['course_id'])
    ).fetchone()
    return enrolled is not None


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Требуется авторизация'}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Требуется авторизация'}), 401
        conn = get_db()
        user = conn.execute('SELECT role FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        if not user or user['role'] != 'admin':
            return jsonify({'error': 'Доступ разрешён только администратору школы'}), 403
        return f(*args, **kwargs)
    return wrapper


# =========================================================================
# МАРШРУТЫ СТРАНИЦ И API ВИТРИНЫ
# =========================================================================

@app.route('/')
def index():
    tpl_path = os.path.join(BASE_DIR, 'templates', 'index.html')
    if os.path.exists(tpl_path):
        return render_template('index.html')
    return send_file(os.path.join(BASE_DIR, 'index.html'))


@app.route('/api/state', methods=['GET'])
def api_get_state():
    conn = get_db()
    user = get_current_user(conn)

    s_row = conn.execute('SELECT * FROM settings WHERE id = 1').fetchone()
    settings = {
        'schoolName': s_row['school_name'],
        'heroTitle': s_row['hero_title'],
        'heroSubtitle': s_row['hero_subtitle'],
        'heroCtaText': s_row['hero_cta_text'],
        'accentColor': s_row['accent_color'],
        'contactEmail': s_row['contact_email'],
        'contactTelegram': s_row['contact_telegram'],
        'contactPhone': s_row['contact_phone'],
        'sbpQrImage': s_row['sbp_qr_image'] if 'sbp_qr_image' in s_row.keys() else '',
        'protection': {
            'watermark': bool(s_row['protect_watermark']),
            'blurOnUnfocus': bool(s_row['protect_blur']),
            'blockShortcutsAndCopy': bool(s_row['protect_shortcuts']),
        }
    }

    purchased_ids = []
    completed_ids = []
    if user:
        purchased_ids = [
            r['course_id'] for r in conn.execute(
                'SELECT course_id FROM enrollments WHERE user_id = ?', (user['id'],)
            ).fetchall()
        ]
        completed_ids = [
            r['lesson_id'] for r in conn.execute(
                'SELECT lesson_id FROM lesson_progress WHERE user_id = ?', (user['id'],)
            ).fetchall()
        ]
        user['purchasedCourseIds'] = purchased_ids
        user['completedLessonIds'] = completed_ids

    is_admin = bool(user and user['role'] == 'admin')
    courses_rows = conn.execute('SELECT * FROM courses').fetchall()
    courses = []
    for c in courses_rows:
        lessons_rows = conn.execute(
            'SELECT * FROM lessons WHERE course_id = ? ORDER BY sort_order ASC, rowid ASC',
            (c['id'],)
        ).fetchall()
        lessons_list = []
        for l in lessons_rows:
            item = {
                'id': l['id'],
                'title': l['title'],
                'duration': l['duration'],
                'isFree': bool(l['is_free']),
                'contentType': l['content_type'],
                'hasPdf': bool(l['pdf_stored_name']),
                'pdfFileName': l['pdf_filename'],
                'hasHtml': bool(l['html_stored_name']),
                'htmlFileName': l['html_filename'],
                'enableCodeTab': bool(l['enable_code_tab']) or l['content_type'] in ('code', 'all'),
                'unlocked': has_lesson_access(conn, user, l)
            }
            if is_admin:
                item['content'] = l['content']
                item['defaultHtml'] = l['default_html']
                item['defaultCss'] = l['default_css']
                item['defaultJs'] = l['default_js']
            lessons_list.append(item)
        courses.append({
            'id': c['id'],
            'title': c['title'],
            'category': c['category'],
            'price': c['price'],
            'coverGradient': c['cover_gradient'],
            'coverImage': c['cover_image'],
            'shortDescription': c['short_description'],
            'fullDescription': c['full_description'],
            'lessons': lessons_list
        })

    users_list = []
    if is_admin:
        all_users = conn.execute('SELECT id, name, email, role, created_at FROM users').fetchall()
        for u in all_users:
            u_courses = [
                r['course_id'] for r in conn.execute(
                    'SELECT course_id FROM enrollments WHERE user_id = ?', (u['id'],)
                ).fetchall()
            ]
            u_completed = [
                r['lesson_id'] for r in conn.execute(
                    'SELECT lesson_id FROM lesson_progress WHERE user_id = ?', (u['id'],)
                ).fetchall()
            ]
            users_list.append({
                'id': u['id'],
                'name': u['name'],
                'email': u['email'],
                'role': u['role'],
                'createdAt': u['created_at'],
                'purchasedCourseIds': u_courses,
                'completedLessonIds': u_completed
            })

    conn.close()
    return jsonify({
        'settings': settings,
        'courses': courses,
        'currentUser': user,
        'users': users_list
    })


# =========================================================================
# АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ
# =========================================================================

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE lower(email) = ?', (email,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Неверный email или пароль'}), 401

    session['user_id'] = user['id']
    return jsonify({'ok': True, 'userId': user['id']})


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not name or not email or len(password) < 3:
        return jsonify({'error': 'Заполните имя, email и пароль (минимум 3 символа)'}), 400

    conn = get_db()
    exists = conn.execute('SELECT 1 FROM users WHERE lower(email) = ?', (email,)).fetchone()
    if exists:
        conn.close()
        return jsonify({'error': 'Пользователь с таким email уже зарегистрирован'}), 409

    user_id = f'user-{uuid.uuid4().hex[:8]}'
    now_str = datetime.now().strftime('%Y-%m-%d')
    conn.execute(
        'INSERT INTO users (id, name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, name, email, generate_password_hash(password), 'student', now_str)
    )
    conn.commit()
    conn.close()

    session['user_id'] = user_id
    return jsonify({'ok': True, 'userId': user_id})


@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify({'ok': True})


# =========================================================================
# ПОКУПКА КУРСА, ЗАЩИЩЁННЫЙ ПРОСМОТР УРОКА, PDF, HTML И ДОМАШНИЕ ЗАДАНИЯ
# =========================================================================

@app.route('/api/courses/<course_id>/buy', methods=['POST'])
@login_required
def api_buy_course(course_id):
    conn = get_db()
    course = conn.execute('SELECT id, title FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'error': 'Курс не найден'}), 404

    now_str = datetime.now().strftime('%Y-%m-%d')
    conn.execute(
        'INSERT OR IGNORE INTO enrollments (user_id, course_id, purchased_at) VALUES (?, ?, ?)',
        (session['user_id'], course_id, now_str)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/lessons/<lesson_id>', methods=['GET'])
def api_get_lesson(lesson_id):
    conn = get_db()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not lesson:
        conn.close()
        return jsonify({'error': 'Урок не найден'}), 404

    user = get_current_user(conn)
    if not has_lesson_access(conn, user, lesson):
        conn.close()
        return jsonify({'error': 'Доступ закрыт. Приобретите курс для просмотра этого урока.'}), 403

    homework = None
    if user:
        hw = conn.execute(
            'SELECT answer_text, status, submitted_at FROM homework_submissions WHERE user_id = ? AND lesson_id = ?',
            (user['id'], lesson_id)
        ).fetchone()
        if hw:
            homework = dict(hw)

    conn.close()
    return jsonify({
        'id': lesson['id'],
        'courseId': lesson['course_id'],
        'title': lesson['title'],
        'duration': lesson['duration'],
        'isFree': bool(lesson['is_free']),
        'videoUrl': lesson['video_url'],
        'contentType': lesson['content_type'],
        'hasPdf': bool(lesson['pdf_stored_name']),
        'pdfFileName': lesson['pdf_filename'],
        'hasHtml': bool(lesson['html_stored_name']),
        'htmlFileName': lesson['html_filename'],
        'enableCodeTab': bool(lesson['enable_code_tab']) or lesson['content_type'] in ('code', 'all'),
        'content': lesson['content'],
        'defaultHtml': lesson['default_html'],
        'defaultCss': lesson['default_css'],
        'defaultJs': lesson['default_js'],
        'homework': homework
    })


@app.route('/api/lessons/<lesson_id>/pdf', methods=['GET'])
def api_stream_protected_pdf(lesson_id):
    """Защищённая отдача PDF-файла только после проверки прав доступа на сервере."""
    conn = get_db()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not lesson or not lesson['pdf_stored_name']:
        conn.close()
        abort(404)

    user = get_current_user(conn)
    if not has_lesson_access(conn, user, lesson):
        conn.close()
        abort(403)

    file_path = os.path.join(UPLOAD_PDF_DIR, lesson['pdf_stored_name'])
    conn.close()

    if not os.path.isfile(file_path):
        abort(404)

    response = send_file(file_path, mimetype='application/pdf', as_attachment=False)
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


@app.route('/api/lessons/<lesson_id>/html', methods=['GET'])
def api_stream_protected_html(lesson_id):
    """Защищённая отдача HTML-файла урока только после проверки прав доступа на сервере."""
    conn = get_db()
    lesson = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not lesson or not lesson['html_stored_name']:
        conn.close()
        abort(404)

    user = get_current_user(conn)
    if not has_lesson_access(conn, user, lesson):
        conn.close()
        abort(403)

    file_path = os.path.join(UPLOAD_HTML_DIR, lesson['html_stored_name'])
    conn.close()

    if not os.path.isfile(file_path):
        abort(404)

    with open(file_path, 'rb') as f:
        raw_bytes = f.read()

    # Декодируем UTF-8 или Windows-1251, если файл сохранён в старой кодировке
    try:
        html_text = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        html_text = raw_bytes.decode('cp1251', errors='replace')

    resp = Response(html_text, mimetype='text/html; charset=utf-8')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


@app.route('/api/lessons/<lesson_id>/complete', methods=['POST'])
@login_required
def api_toggle_lesson_complete(lesson_id):
    conn = get_db()
    user_id = session['user_id']
    exists = conn.execute(
        'SELECT 1 FROM lesson_progress WHERE user_id = ? AND lesson_id = ?',
        (user_id, lesson_id)
    ).fetchone()
    if exists:
        conn.execute('DELETE FROM lesson_progress WHERE user_id = ? AND lesson_id = ?', (user_id, lesson_id))
        completed = False
    else:
        conn.execute(
            'INSERT INTO lesson_progress (user_id, lesson_id, completed_at) VALUES (?, ?, ?)',
            (user_id, lesson_id, datetime.now().strftime('%Y-%m-%d %H:%M'))
        )
        completed = True
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'completed': completed})


@app.route('/api/lessons/<lesson_id>/homework', methods=['POST'])
@login_required
def api_submit_homework(lesson_id):
    data = request.get_json(silent=True) or {}
    answer_text = (data.get('answerText') or '').strip()
    if not answer_text:
        return jsonify({'error': 'Введите текст ответа на домашнее задание'}), 400

    conn = get_db()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    hw_id = f'hw-{uuid.uuid4().hex[:8]}'
    conn.execute("""
        INSERT INTO homework_submissions (id, user_id, lesson_id, answer_text, status, submitted_at)
        VALUES (?, ?, ?, ?, 'submitted', ?)
        ON CONFLICT(user_id, lesson_id) DO UPDATE SET
            answer_text = excluded.answer_text,
            status = 'submitted',
            submitted_at = excluded.submitted_at
    """, (hw_id, session['user_id'], lesson_id, answer_text, now_str))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'submittedAt': now_str})


# =========================================================================
# API КОНСТРУКТОРА САЙТА (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА)
# =========================================================================

@app.route('/api/admin/settings', methods=['PUT'])
@admin_required
def api_admin_update_settings():
    data = request.get_json(silent=True) or {}
    protection = data.get('protection') or {}
    conn = get_db()
    conn.execute("""
        UPDATE settings SET
            school_name = ?,
            hero_title = ?,
            hero_subtitle = ?,
            hero_cta_text = ?,
            accent_color = ?,
            contact_email = ?,
            contact_telegram = ?,
            contact_phone = ?,
            protect_watermark = ?,
            protect_blur = ?,
            protect_shortcuts = ?,
            sbp_qr_image = ?
        WHERE id = 1
    """, (
        data.get('schoolName', 'Моя Онлайн-Школа'),
        data.get('heroTitle', ''),
        data.get('heroSubtitle', ''),
        data.get('heroCtaText', 'Выбрать курс'),
        data.get('accentColor', 'indigo'),
        data.get('contactEmail', ''),
        data.get('contactTelegram', ''),
        data.get('contactPhone', ''),
        1 if protection.get('watermark', True) else 0,
        1 if protection.get('blurOnUnfocus', True) else 0,
        1 if protection.get('blockShortcutsAndCopy', True) else 0,
        data.get('sbpQrImage', ''),
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/admin/courses', methods=['POST'])
@admin_required
def api_admin_create_course():
    data = request.get_json(silent=True) or {}
    course_id = f'course-{uuid.uuid4().hex[:8]}'
    conn = get_db()
    conn.execute(
        'INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (
            course_id,
            data.get('title', 'Новый онлайн-курс'),
            data.get('category', 'Общее'),
            int(data.get('price', 4900)),
            data.get('coverGradient', 'grad-indigo'),
            data.get('coverImage', ''),
            data.get('shortDescription', 'Краткое описание программы обучения'),
            data.get('fullDescription', 'Подробная программа курса и результаты после прохождения.')
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'courseId': course_id})


@app.route('/api/admin/courses/<course_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_admin_manage_course(course_id):
    conn = get_db()
    if request.method == 'DELETE':
        conn.execute('DELETE FROM courses WHERE id = ?', (course_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    data = request.get_json(silent=True) or {}
    conn.execute("""
        UPDATE courses SET
            title = ?, category = ?, price = ?, cover_gradient = ?,
            cover_image = ?, short_description = ?, full_description = ?
        WHERE id = ?
    """, (
        data.get('title', ''),
        data.get('category', ''),
        int(data.get('price', 0)),
        data.get('coverGradient', 'grad-indigo'),
        data.get('coverImage', ''),
        data.get('shortDescription', ''),
        data.get('fullDescription', ''),
        course_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/admin/courses/<course_id>/lessons', methods=['POST'])
@admin_required
def api_admin_create_lesson(course_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    max_order = conn.execute(
        'SELECT COALESCE(MAX(sort_order), 0) AS m FROM lessons WHERE course_id = ?',
        (course_id,)
    ).fetchone()['m']
    lesson_id = f'lesson-{uuid.uuid4().hex[:8]}'
    conn.execute(
        'INSERT INTO lessons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (
            lesson_id,
            course_id,
            max_order + 1,
            data.get('title', 'Новый урок'),
            data.get('duration', '25 мин'),
            1 if data.get('isFree') else 0,
            data.get('videoUrl', ''),
            data.get('contentType', 'text'),
            '', '', '', '',
            1 if data.get('enableCodeTab') else 0,
            data.get('content', 'Текст конспекта нового урока...'),
            data.get('defaultHtml', '<h1>Практическое задание</h1>'),
            data.get('defaultCss', 'body { font-family: sans-serif; padding: 20px; }'),
            data.get('defaultJs', 'console.log("Урок запущен");')
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'lessonId': lesson_id})


@app.route('/api/admin/lessons/<lesson_id>', methods=['PUT', 'DELETE'])
@admin_required
def api_admin_manage_lesson(lesson_id):
    conn = get_db()
    existing = conn.execute('SELECT * FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Урок не найден'}), 404

    if request.method == 'DELETE':
        if existing['pdf_stored_name'] and existing['pdf_stored_name'] != 'demo_typography.pdf':
            p = os.path.join(UPLOAD_PDF_DIR, existing['pdf_stored_name'])
            if os.path.exists(p):
                os.remove(p)
        if existing['html_stored_name']:
            h = os.path.join(UPLOAD_HTML_DIR, existing['html_stored_name'])
            if os.path.exists(h):
                os.remove(h)
        conn.execute('DELETE FROM lessons WHERE id = ?', (lesson_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    data = request.get_json(silent=True) or {}
    default_html = data['defaultHtml'] if 'defaultHtml' in data else existing['default_html']
    default_css = data['defaultCss'] if 'defaultCss' in data else existing['default_css']
    default_js = data['defaultJs'] if 'defaultJs' in data else existing['default_js']

    conn.execute("""
        UPDATE lessons SET
            title = ?, duration = ?, is_free = ?, video_url = ?,
            content_type = ?, enable_code_tab = ?, content = ?,
            default_html = ?, default_css = ?, default_js = ?
        WHERE id = ?
    """, (
        data.get('title', existing['title']),
        data.get('duration', existing['duration']),
        1 if data.get('isFree', existing['is_free']) else 0,
        data.get('videoUrl', existing['video_url']),
        data.get('contentType', existing['content_type']),
        1 if data.get('enableCodeTab', existing['enable_code_tab']) else 0,
        data.get('content', existing['content']),
        default_html,
        default_css,
        default_js,
        lesson_id
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/admin/lessons/<lesson_id>/pdf', methods=['POST', 'DELETE'])
@admin_required
def api_admin_upload_lesson_pdf(lesson_id):
    """Загрузка или удаление PDF-файла методички на Python-сервере."""
    conn = get_db()
    old = conn.execute('SELECT pdf_stored_name FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not old:
        conn.close()
        return jsonify({'error': 'Урок не найден'}), 404

    if request.method == 'DELETE':
        if old['pdf_stored_name'] and old['pdf_stored_name'] != 'demo_typography.pdf':
            old_path = os.path.join(UPLOAD_PDF_DIR, old['pdf_stored_name'])
            if os.path.exists(old_path):
                os.remove(old_path)
        conn.execute(
            "UPDATE lessons SET pdf_filename = '', pdf_stored_name = '' WHERE id = ?",
            (lesson_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    if 'pdf' not in request.files:
        conn.close()
        return jsonify({'error': 'Файл PDF не передан'}), 400
    file = request.files['pdf']
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        conn.close()
        return jsonify({'error': 'Разрешена загрузка только файлов в формате .pdf'}), 400

    stored_name = f'{lesson_id}_{uuid.uuid4().hex[:8]}.pdf'
    save_path = os.path.join(UPLOAD_PDF_DIR, stored_name)
    file.save(save_path)

    if old['pdf_stored_name'] and old['pdf_stored_name'] != 'demo_typography.pdf':
        old_path = os.path.join(UPLOAD_PDF_DIR, old['pdf_stored_name'])
        if os.path.exists(old_path):
            os.remove(old_path)

    conn.execute(
        'UPDATE lessons SET pdf_filename = ?, pdf_stored_name = ?, content_type = ? WHERE id = ?',
        (file.filename, stored_name, 'pdf', lesson_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'pdfFileName': file.filename})


@app.route('/api/admin/lessons/<lesson_id>/html', methods=['POST', 'DELETE'])
@admin_required
def api_admin_upload_lesson_html(lesson_id):
    """Загрузка или удаление интерактивного HTML-файла урока на Python-сервере."""
    conn = get_db()
    old = conn.execute('SELECT html_stored_name FROM lessons WHERE id = ?', (lesson_id,)).fetchone()
    if not old:
        conn.close()
        return jsonify({'error': 'Урок не найден'}), 404

    if request.method == 'DELETE':
        if old['html_stored_name']:
            old_path = os.path.join(UPLOAD_HTML_DIR, old['html_stored_name'])
            if os.path.exists(old_path):
                os.remove(old_path)
        conn.execute(
            "UPDATE lessons SET html_filename = '', html_stored_name = '' WHERE id = ?",
            (lesson_id,)
        )
        conn.commit()
        conn.close()
        return jsonify({'ok': True})

    if 'html' not in request.files:
        conn.close()
        return jsonify({'error': 'HTML-файл не передан'}), 400
    file = request.files['html']
    fname_lower = (file.filename or '').lower()
    if not fname_lower or not (fname_lower.endswith('.html') or fname_lower.endswith('.htm')):
        conn.close()
        return jsonify({'error': 'Разрешена загрузка только файлов в формате .html или .htm'}), 400

    stored_name = f'{lesson_id}_{uuid.uuid4().hex[:8]}.html'
    save_path = os.path.join(UPLOAD_HTML_DIR, stored_name)
    file.save(save_path)

    with open(save_path, 'rb') as f:
        raw_bytes = f.read()
    try:
        decoded_html = raw_bytes.decode('utf-8')
    except UnicodeDecodeError:
        decoded_html = raw_bytes.decode('cp1251', errors='replace')

    if old['html_stored_name']:
        old_path = os.path.join(UPLOAD_HTML_DIR, old['html_stored_name'])
        if os.path.exists(old_path):
            os.remove(old_path)

    conn.execute(
        """UPDATE lessons
           SET html_filename = ?, html_stored_name = ?, content_type = ?, default_html = ?
           WHERE id = ?""",
        (file.filename, stored_name, 'html', decoded_html, lesson_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'htmlFileName': file.filename})


@app.route('/api/admin/users/<user_id>/courses/<course_id>', methods=['POST', 'DELETE'])
@admin_required
def api_admin_user_access(user_id, course_id):
    conn = get_db()
    if request.method == 'POST':
        conn.execute(
            'INSERT OR IGNORE INTO enrollments (user_id, course_id, purchased_at) VALUES (?, ?, ?)',
            (user_id, course_id, datetime.now().strftime('%Y-%m-%d'))
        )
    else:
        conn.execute(
            'DELETE FROM enrollments WHERE user_id = ? AND course_id = ?',
            (user_id, course_id)
        )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
