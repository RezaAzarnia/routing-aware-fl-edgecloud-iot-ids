# سند مجوز ارزیابی نهایی (Final Test) — برای تصمیم مالک پروژه

**وضعیت: پیش‌نویس آماده برای تصمیم. هیچ بخشی از ارزیابی اجرا نشده است و هیچ فایل test قفل‌شده‌ای باز نشده است. این سند امضا نیست؛ فقط توضیح می‌دهد دقیقاً چه چیزی را تأیید می‌کنید.**

## ۱. دقیقاً چه چیزی اجرا می‌شود
یک دستور واحد، یک‌بار، روی مدل‌های منجمد:
- **۲۸۰ run** (۲۴۰ run از Phase 6C و ۴۰ run اجباری Phase 7b روی UNSW) با **۵۶۰ checkpoint** (best و last برای هر run).
- هر checkpoint فقط **پیش‌بینی** می‌کند. هیچ آموزش، تنظیم، fit یا انتخاب جدیدی انجام نمی‌شود.
- آستانه‌ها همان مقادیر ثبت‌شده از partition کالیبراسیون هستند (آستانه‌ی اصلی، به‌علاوه‌ی سه نقطه‌ی عملیاتی با FPR هدف ۱٪، ۵٪ و ۱۵٪ برای checkpoint بهترین).
- preprocessorها همان‌هایی هستند که در آموزش fit شده‌اند و بارگذاری می‌شوند، نه دوباره fit.

## ۲. به کدام داده‌ها دسترسی داده می‌شود
| فایل | نقش | چند بار باز می‌شود |
|---|---|---|
| `data\UNSW_NB15_testing-set.csv` (۸۲٬۳۳۲ ردیف) — **قفل‌شده** | ارزیابی نهایی | یک بار |
| `data\CICIoT2023\prepared_verified_v2_filegroup\test.csv.gz` (۳۰۰٬۰۰۰ ردیف) — **قفل‌شده** | ارزیابی نهایی | یک بار |
| فایل‌های آموزشی/اعتبارسنجی UNSW و CIC (غیرقفل) | فقط برای ساخت زیرمجموعه‌های کنترل هم‌پوشانی (overlap) | یک بار |
`test_provenance.csv.gz` توسط ارزیابی باز نمی‌شود. قبل از هر پیش‌بینی، hash محتوای هر فایل test با مقدار قفل‌شده در manifest مقایسه می‌شود و در صورت اختلاف، کار متوقف می‌شود.

## ۳. تعداد ارزیابی‌ها و تقسیم آن‌ها
- **اولیه (۵۰ run):** `reference`، `clean_fedavg`، `scenario_fedavg_topk`، `corrected`، `reference_gaussian` × دو dataset × پنج seed. چهار contrast پیش‌ثبت‌شده: reference−clean_fedavg، reference−scenario_fedavg_topk، corrected−reference، reference_gaussian−reference (معیار اصلی: ROC-AUC در checkpoint بهترین).
- **ثانویه (۱۹۰ run):** سایر ۱۹ arm از Phase 6C.
- **اکتشافی (۴۰ run):** Phase 7b (فقط گزارش، بدون وزن استنباطی).
- برای هر run: ۵ اعمال آستانه (۴ برای best، ۱ برای last) و معیارهای زیرمجموعه‌های overlap (UNSW: ردیف‌هایی که بردار predictor آن‌ها در فایل آموزشی رسمی نیست؛ CIC: ردیف‌های یکتا و خارج از train/validation).
- **زمان:** اندازه‌گیری نشده؛ برآورد تقریبی ده‌ها دقیقه روی CPU (۵۶۰ پیش‌بینی روی ۸۲ هزار و ۳۰۰ هزار ردیف).

## ۴. خروجی‌های مورد انتظار (همه در پوشه‌ی جدید `results_final_test\`، خارج از همه‌ی نتایج تاریخی)
`{dataset}\{arm}\seed_{s}\final_test_result.json` و `test_probabilities.npz` برای هر run (۲۸۰ مورد)، فایل append-only `ledger.jsonl` با hash نتایج؛ سپس با `analyze_final_test.py`: جدول‌های per-run، خلاصه‌ی هر arm، contrastهای زوجی (میانگین، SD، بازه‌ی اطمینان ۹۵٪، تعداد seedهای برنده، p دقیق sign-flip)، جابه‌جایی FPR (test منهای calibration) و جدول زیرمجموعه‌های overlap.

## ۵. چگونه از نشت و انتخاب پس از آزمون جلوگیری می‌شود
- فرضیه‌ها، tierها، checkpointها، آستانه‌ها، معیارها و روش آماری **قبل از اجرا** در `PRETEST_SIGNOFF.md` و manifest منجمد (hash: `737b901f…`) ثبت و commit شده‌اند.
- همه‌ی ۲۸۰ run بدون استثنا ارزیابی و گزارش می‌شوند؛ کد، انتخاب run یا حذف مورد نامطلوب ندارد.
- هر دو checkpoint (best و last) برای همه‌ی armها کنار هم گزارش می‌شوند؛ انتخاب مورد مطلوب بعد از آزمون وجود ندارد.
- کد ارزیابی هیچ `fit`، جست‌وجوی آستانه، انتخاب checkpoint یا بهینه‌سازی ندارد (با تست ساختاری تأیید شده است).
- نتایج فقط با حالت exclusive-create نوشته می‌شوند؛ اجرای دوم رد می‌شود و چیزی را بازنویسی نمی‌کند.
- فایل‌های test فقط داخل یک بلوک مجوزدار باز می‌شوند و در اجراهای عادی تست، باز کردن آن‌ها مسدود است.
- تمرین کامل روی داده‌ی مصنوعی انجام شد: رد بدون مجوز، preflight، dry-run، رد فایل دست‌کاری‌شده، اجرا، محافظت در برابر بازنویسی و تحلیل؛ همه پاس. تحلیل منجمد با داده‌ی validation هم ۲۴ از ۲۴ مقایسه را دقیقاً بازتولید کرد.
- محدودیت صادقانه: فایل‌های test قبلاً توسط بررسی‌های integrity و تست‌های واحد باز شده بودند (hash، شمارش ردیف، تکرار و overlap)، هرگز برای مدل‌سازی. این در مقاله افشا شده است.

## ۶. اگر نتیجه منفی باشد چه می‌شود
هر نتیجه‌ای، چه موافق چه منفی، **همان‌طور که هست** گزارش می‌شود. هیچ مدل، آستانه، checkpoint، preprocessor یا تحلیلی بعد از دیدن نتیجه تغییر نمی‌کند و اجرای مجدد برای «بهتر شدن» مجاز نیست. اگر FPR آزمون بیش از ۰.۲۵ باشد، به‌عنوان شکست سیاست آستانه گزارش می‌شود، نه اصلاح. ادعاهای مقاله بر اساس نتیجه محدود یا حذف می‌شوند و تنها تغییر مجاز در مقاله افزودن بخش «نتایج final-test» است. فایل‌های test پس از اجرا «مصرف‌شده» حساب می‌شوند.

## ۷. دستور دقیق (اجرا **نمی‌شود** مگر پس از تأیید صریح شما)
پیش از آن (بدون خواندن داده‌ی test):
```powershell
$PY = "C:\Users\R_Azarnia\Desktop\IoT-FL-Recovery\venv\Scripts\python.exe"
& $PY scripts\final_test\final_test_v2.py evaluate --preflight
& $PY scripts\final_test\final_test_v2.py evaluate --dry-run --authorization C:\secure\final_test_authorization.json
```
اجرای یک‌باره:
```powershell
& $PY scripts\final_test\final_test_v2.py evaluate --authorization C:\secure\final_test_authorization.json
& $PY scripts\final_test\analyze_final_test.py --results results_final_test --out results_final_test\ledgers
```

## ۸. متن دقیق مجوزی که باید تأیید کنید
فایل `C:\secure\final_test_authorization.json` را خودتان بسازید (با `authorization-template`) و این مقادیر را وارد کنید. **متن statement باید کاراکتر به کاراکتر برابر باشد:**
```json
{
  "manifest_sha256": "737b901f26ae66cccb8971da41a8537c9e803f1933e1c442a63e38ad0a28d556",
  "plan": "final-test-eval-v2",
  "authorized": true,
  "statement": "I authorize one-time final-test evaluation of the frozen configurations under plan final-test-eval-v2",
  "authorized_by": "<نام کامل شما>",
  "acknowledge_no_retuning_after_test": true,
  "acknowledge_prior_integrity_reads_disclosed": true
}
```
معنای دو تأییدیه: (۱) «بعد از دیدن نتایج test هیچ مدل، آستانه یا تحلیلی را تغییر نمی‌دهم»؛ (۲) «می‌پذیرم که فایل‌های test پیش‌تر برای بررسی‌های integrity باز شده‌اند و این در مقاله افشا می‌شود».
**تأییدیه‌ی اضافی (بخش R6، خارج از JSON، در پاسخ تأیید خود بنویسید):** «موانع ویراستاری M1 تا M4 (خواندن منابع، بیانیه‌ها، ژورنال/قالب، ویرایش زبانی) را آگاهانه به بعد از ارزیابی موکول می‌کنم؛ این موارد پروتکل و تحلیل را تغییر نمی‌دهند.»

## ۹. چه کسی امضا می‌کند
من نمی‌توانم و نباید امضای شما را بسازم. دو راه: خودتان فایل JSON را بنویسید؛ یا در پیام تأیید، نام کامل خود را صریحاً بنویسید تا مقدار `authorized_by` را همان‌طور وارد کنم (همچنان تصمیم شما محسوب می‌شود). بدون فایل معتبر، دستور اجرا رد می‌شود. پیش از اجرا، tag پیشنهادی `final-test-eval-v1` روی commit نهایی ساخته می‌شود (`PROPOSED_TAG.md`).
