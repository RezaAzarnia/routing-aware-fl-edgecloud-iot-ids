# نسخه V5 برای اجرای CICIoT2023

این بسته، Code Base اصلی V4 را بدون حذف پشتیبانی UNSW-NB15 توسعه می‌دهد و یک مسیر جداگانه برای CICIoT2023 اضافه می‌کند.

## تصمیم دیتاست

برای اعتبارسنجی خارجی مقاله، CICIoT2023 انتخاب مناسبی است؛ چون:

- مختص IoT است.
- از 105 دستگاه و 33 حمله در هفت گروه ساخته شده است.
- مستقل از UNSW-NB15 و متعلق به مرکز پژوهشی دیگری است.
- CSVهای آماده برای Machine Learning دارد.
- Binary intrusion detection را پشتیبانی می‌کند.

این دیتاست بسیار بزرگ است: نسخه CSV رسمی حدود 169 فایل دارد. بسته حاضر عمداً یک نمونه بازتولیدپذیر می‌سازد تا Pipeline فعلی در حافظه اجرا شود. در مقاله باید تعداد دقیق ردیف‌های استفاده‌شده گزارش شود و نباید ادعا شود کل 46 میلیون ردیف آموزش داده شده‌اند.

## دانلود رسمی

صفحه رسمی:

https://www.unb.ca/cic/datasets/iotdataset-2023.html

فرم دانلود رسمی:

https://cicresearch.ca/IOTDataset/CIC_IOT_Dataset2023/

در صفحه رسمی روی **Download the dataset** کلیک کنید، فرم کوتاه را تکمیل کنید و بخش CSV را دریافت کنید.

## ساختار پوشه لازم

پس از Extract کردن دیتاست، تمام 169 فایل CSV را در این مسیر قرار دهید:

```text
CICIoT2023_FL_V5/
└── data/
    └── CICIoT2023/
        └── raw_csv/
            ├── part-00000-....csv
            ├── part-00001-....csv
            └── ...
```

وجود زیرپوشه داخل `raw_csv` اشکال ندارد، چون اسکریپت به‌صورت بازگشتی `**/*.csv` را پیدا می‌کند.

## ترتیب اجرای دقیق

### 1. نصب کتابخانه‌ها

روی فایل زیر دوبار کلیک کنید:

```text
00_INSTALL_REQUIREMENTS.bat
```

### 2. کنترل دیتاست

```text
01_CHECK_CICIOT2023_DATASET.bat
```

این مرحله تعداد CSVها، نام ستون‌ها و Labelهای چند فایل نمونه را بررسی می‌کند.

### 3. ساخت داده کوچک Pilot

```text
02_PREPARE_CICIOT2023_PILOT.bat
```

خروجی:

```text
data/CICIoT2023/prepared_pilot/
```

شامل:

- `train.csv.gz`
- `validation.csv.gz`
- `test.csv.gz`
- `preparation_metadata.json`
- `split_manifest.csv`
- `raw_label_counts.csv`
- `prepared_label_counts.csv`

### 4. Preflight

```text
03_RUN_CICIOT2023_PREFLIGHT.bat
```

این فقط نصب، خواندن داده، Preprocessing، Partitioning و یک اجرای کوچک را کنترل می‌کند.

### 5. Pilot کامل یک Seed

```text
04_RUN_CICIOT2023_PILOT.bat
```

قبل از هر اجرای مقاله‌ای، خروجی Pilot باید بررسی شود:

- ROC-AUC و PR-AUC
- FPR و Recall
- Update norms
- Clipped fraction
- Noise-to-signal ratio
- RAM و زمان اجرا

### 6. ساخت نمونه مقاله

```text
05_PREPARE_CICIOT2023_PAPER.bat
```

تنظیمات پیش‌فرض این بسته:

| Split | تعداد ردیف |
|---|---:|
| Train | 1,000,000 |
| Validation | 200,000 |
| Test | 300,000 |

Train به‌صورت 50% Benign و 50% Attack ساخته می‌شود. سهم Attackهای Train بین Attack categoryها توزیع می‌شود تا DDoSهای بسیار پرتعداد تمام آموزش را اشغال نکنند. Validation و Test نسبت‌های طبیعی Categoryها را در Shardهای نگه‌داشته‌شده حفظ می‌کنند.

تقسیم داده در سطح CSV shard و با Seed ثابت 2023 انجام می‌شود:

- 70% Shardها: Train
- 10% Shardها: Validation
- 20% Shardها: Test

محدودیت: CSV رسمی Device ID ندارد؛ بنابراین این پروتکل shard-held-out است، نه device-held-out. این موضوع باید در Limitations مقاله ذکر شود.

### 7. تعیین Clip norm

```text
06_RUN_CLIP_SCREEN_1SEED.bat
```

این مرحله Clip normهای 0.05، 0.10 و 0.20 را با یک Seed بررسی می‌کند. اگر گزارش قابل‌قبول باشد، مقدار انتخاب‌شده خودکار در Configهای CICIoT2023 قرار می‌گیرد.

### 8. دو روش اصلی با پنج Seed

```text
07_RUN_MAIN_EPS10_EPS20_5SEEDS.bat
```

Seedها:

```text
2, 3, 4, 5, 6
```

خروجی‌های ε≈10 و ε≈20 جدا نگه داشته می‌شوند.

### 9. Baselineهای پنج‌Seed

```text
08_RUN_BASELINES_5SEEDS.bat
```

شامل:

- Centralized clean
- FedAvg clean
- FedAvg under attack/failure
- FedAvg + DP
- Robust aggregation without DP
- Proposed Full

### 10. Ablation و Sweepهای ضروری

```text
09_RUN_ABLATIONS_3SEEDS.bat
10_RUN_KEY_SWEEPS_3SEEDS.bat
```

Sweepهای کلیدی:

- Malicious-client fraction
- Failure probability
- IID/Dirichlet heterogeneity

## Configهای اصلی

```text
configs/ciciot2023_preflight.yaml
configs/ciciot2023_pilot.yaml
configs/ciciot2023_clip_screen.yaml
configs/ciciot2023_eps10.yaml
configs/ciciot2023_eps20.yaml
configs/ciciot2023_core.yaml
```

## چه چیزهایی نسبت به V4 تغییر کرده است؟

- `data.dataset_name` اضافه شده است.
- Validation مستقل CICIoT2023 پشتیبانی می‌شود.
- `prepare_ciciot2023.py` برای خواندن Chunk-based دیتاست بزرگ اضافه شده است.
- Label اصلی در `attack_category` حفظ و Binary label در `label` ذخیره می‌شود.
- Preprocessor فقط روی Train fit می‌شود.
- Test در Model selection یا Threshold selection استفاده نمی‌شود.
- Calibration با بخشی از Test برای CICIoT2023 غیرفعال است.
- Metadata دقیق آماده‌سازی داده همراه هر Run ذخیره می‌شود.

## نکات علمی برای مقاله Q1

1. CICIoT2023 را **external validation dataset** بنامید.
2. تعداد واقعی Sampleهای استفاده‌شده را دقیق گزارش کنید.
3. نگویید کل دیتاست 46M-row آموزش داده شده، مگر Config را تغییر داده و واقعاً کل آن را اجرا کرده باشید.
4. Split را `deterministic shard-held-out split` معرفی کنید.
5. Train balancing را شفاف گزارش کنید.
6. Official UNSW-NB15 همچنان Benchmark اصلی باقی بماند.
7. روی CICIoT2023 نیز Mean ± SD، 95% CI و پنج Seed گزارش شود.
8. نتایج ضعیف و Trade-offها حذف نشوند.

## تست انجام‌شده روی کد

- تمام تست‌های قبلی V4 حفظ شده‌اند.
- تست Loader جدید CICIoT2023 اضافه شده است.
- نتیجه تست بسته هنگام ساخت: `22 passed`.
- Pipeline جدید با CSVهای مصنوعی دارای Schema مشابه CICIoT2023 از آماده‌سازی تا اجرای Experiment آزمایش شده است.

توجه: به دلیل حجم چندگیگابایتی دیتاست رسمی، این بسته در این محیط روی کل فایل رسمی اجرا نشده است. ابتدا Preflight و Pilot را روی سیستم خود اجرا کنید و خروجی را برای ممیزی ارسال کنید.
