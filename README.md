# هم‌درس — سامانه کلاس و بانک سؤال

نسخه آغازین یک سامانه فارسی و راست‌به‌چپ برای مدیریت دوره‌ها، کلاس‌ها، جزوه‌ها و سؤال‌ها. معلم می‌تواند برای هر کلاس پیوند دعوت بسازد، درخواست دانش‌آموزان را تأیید کند و محتوای قابل مشاهده و دسترسی به پاسخ‌ها را برای هر کلاس جداگانه تعیین کند. هر سؤال می‌تواند حداکثر یک تصویر داشته باشد.

جزئیات کامل محصول در [persian_teacher_platform_spec.md](./persian_teacher_platform_spec.md) آمده است.

## اجرای محلی

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

مستندات تعاملی API در `http://localhost:8000/docs` در دسترس است.

### رابط کاربری

```bash
cd frontend
npm install
npm run dev
```

رابط کاربری در `http://localhost:5173` اجرا می‌شود و درخواست‌های `/api` را در محیط توسعه به FastAPI می‌فرستد.

## آزمون

```bash
cd backend
pytest

cd ../frontend
npm run build
```

> ذخیره‌سازی تصویر در اجرای محلی روی دیسک انجام می‌شود. برای استقرار، همین لایه باید به فضای ذخیره‌سازی خصوصی سازگار با S3 یا Supabase Storage متصل شود.
