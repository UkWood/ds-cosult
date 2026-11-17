# DS-01C — Linux/WSL PDF Byte Pin & Physical Page Validation

**Тип:** одноразовое задание на чтение оригиналов и фиксацию доказательств. **НЕ кодинг/DS-02**, без изменений исходных репозиториев.  
**Статус:** READY FOR OWNER-OPERATED VALIDATION — NOT EXECUTED.  
**Дата:** 2026-11-17.

## Цель
Получить подлинные байты трёх публичных PDF, вычислить SHA-256, сверить число физических страниц и изображения эталонных страниц. Не использовать закрытый Core/GT или API ключи.

## Исполнение в отдельной папке Linux/WSL

```bash
set -euo pipefail
mkdir -p "$HOME/ds-consult-pdf-pin"
cd "$HOME/ds-consult-pdf-pin"

curl --fail --location --retry 3 --connect-timeout 15 --max-time 180 \
  --output sos95_re.pdf 'https://www.mnppsaturn.ru/ftp/public/doc/sos-95/re%20SOS-95.pdf'
curl --fail --location --retry 3 --connect-timeout 15 --max-time 180 \
  --output sldks1_re2011_p1.pdf 'https://www.mnppsaturn.ru/ftp/public/doc/sldks/re%20SLDKS-1%20p1(3).pdf'
curl --fail --location --retry 3 --connect-timeout 15 --max-time 180 \
  --output easdkiu_re.pdf 'https://www.mnppsaturn.ru/ftp/public/doc/iis/re_iis.pdf'

file --mime-type sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf
sha256sum sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf | tee SHA256SUMS.txt
wc -c sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf
pdfinfo -v
for f in sos95_re.pdf sldks1_re2011_p1.pdf easdkiu_re.pdf; do
  echo "========== $f =========="
  pdfinfo "$f" | grep -E '^(Pages|Page size|PDF version|Encrypted|Title|CreationDate):'
done

mkdir -p evidence_png
pdftoppm -f 9 -l 9 -singlefile -scale-to 1200 -png sos95_re.pdf evidence_png/sos95_p009
pdftoppm -f 7 -l 7 -singlefile -scale-to 1200 -png sldks1_re2011_p1.pdf evidence_png/sldks_p007
pdftoppm -f 18 -l 18 -singlefile -scale-to 1200 -png sldks1_re2011_p1.pdf evidence_png/sldks_p018
pdftoppm -f 3 -l 3 -singlefile -scale-to 1200 -png easdkiu_re.pdf evidence_png/easdkiu_p003
pdftoppm -f 4 -l 4 -singlefile -scale-to 1200 -png easdkiu_re.pdf evidence_png/easdkiu_p004
pdftoppm -f 12 -l 12 -singlefile -scale-to 1200 -png easdkiu_re.pdf evidence_png/easdkiu_p012
```

**Ожидаемые ориентиры, НЕ основание PASS сами по себе:** SOS 195, SLDKS 83, EAS 79 физических страниц. Если число не совпало, зафиксировать `BLOCKED: DOCUMENT DRIFT`, не подбирать другой PDF молча. Точно сверить строки таблиц и вид схем на PNG.

## Возвращаемый отчёт
- Реальные SHA-256 и byte sizes;
- `pdfinfo`: page counts, PDF version, encrypted/metadata и версия утилиты;
- список сверенных PNG и страницу, печатный номер;
- ошибки скачивания и повторы, если были.

**Не публиковать исходные бинарные PDF/PNG автоматически в PUBLIC репозитории.** Разрешено сохранить лишь manifest (URL, SHA-256, размер, страницы, время проверки, версия инструмента) и краткое обоснование. Для долговременного хранения подлинных bytes требуется отдельное решение о доступах и авторских правах.

## Acceptance
`PDF_BYTES_PINNED` — только если скачаны byte-identical оригиналы (SHA записан), `pdfinfo` совпало, физические страницы визуально сверены, source URL/редакция идентифицированы. Экспертная техническая приёмка GT — отдельный gate.
