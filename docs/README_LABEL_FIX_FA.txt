# رفع خطای نبودن ستون Label در CICIoT2023 CSV.zip

نسخه رسمی CICIoT2023 که از CIC/UNB دانلود شده معمولاً داخل CSVها ستون `label` ندارد.
در این نسخه، Label از نام پوشه بالادستی مشخص می‌شود، مثل:

- `Benign_Final/Benign_Final.pcap.csv`  → Benign
- `Backdoor_Malware/Backdoor_Malware.pcap.csv` → Attack
- `DDoS-ACK_Fragmentation/...csv` → Attack

بنابراین خطای زیر طبیعی بود و به معنی خراب بودن دیتاست نیست:

`Could not detect the label column`

این Patch کد را طوری اصلاح می‌کند که اگر ستون label پیدا نشد، Label را از نام پوشه استخراج کند.

## روش استفاده

اگر بسته کامل جدید را دانلود کردید، همان را جایگزین قبلی کنید.

اگر فقط Patch را استفاده می‌کنید، دو فایل زیر را در پوشه اصلی پروژه جایگزین کنید:

- `prepare_ciciot2023.py`
- `inspect_ciciot2023.py`

سپس دوباره اجرا کنید:

```bat
01_CHECK_CICIOT2023_DATASET.bat
```

بعد از موفقیت، به ترتیب این‌ها را اجرا کنید:

```bat
02_PREPARE_CICIOT2023_PILOT.bat
03_RUN_CICIOT2023_PREFLIGHT.bat
04_RUN_CICIOT2023_PILOT.bat
```

## نکته مقاله‌ای

این نسخه دیتاست از label path استفاده می‌کند. در مقاله باید نوشته شود:

`For the official CICIoT2023 CSV release, class labels were inferred from the top-level class folders because the feature CSV files do not include a row-level label column.`
