# DC-03B · Независимая офлайн-валидация WSL

Используйте чистый опубликованный checkout, Python 3.12, prlimit, Poppler и закреплённые зависимости проекта через requirements-dev.txt. Подготовьте тот же закреплённый Saturn checkout и оригиналы, как в runbook DC-02. Используйте уже сохранённый файл q01-candidate.json из предоставленного Audit Package. Приватный ledger, скриншоты, JSON и оригинальные PDF остаются вне Git. [Подготовка корпуса](../DS-DC-02-LIVE.md)

```sh
set -e
unset DEEPSEEK_API_KEY
export SATURN_SOURCE=/absolute/path/to/Saturn-Main-Site
export DS_DC_CACHE=/absolute/path/to/frozen/cache
export DS_DC_Q01_CANDIDATE=/absolute/private/path/q01-candidate.json
export SATURN_BKD_PDF="$DS_DC_CACHE/030303812b4bd8dfc7e82fcd3ad4ef8493526549c7c90d033ce25b4f8b2fe83a.pdf"
export SATURN_SLD_PDF="$DS_DC_CACHE/f1436a93285cad9a201b6b387ed64a606ad2768cfc7ee70627c188411e9ce61f.pdf"
test "$(git -C "$SATURN_SOURCE" rev-parse HEAD)" = 084d759487bfab6e111549c9b5469711ac5fc13e
test "$(wc -c < "$DS_DC_Q01_CANDIDATE")" -eq 5188
printf '%s  %s\n' ae646fb4ae9d3b83c22edc9717b4d8ddb0ef228ac54b9f5a1aec222bcb24cb26 "$DS_DC_Q01_CANDIDATE" | sha256sum -c -
python -m pytest -q --tb=short
python -m ds_dc.evidence_lab matrix
python -m ds_dc.structural_shadow --fixture "$DS_DC_Q01_CANDIDATE" \
  --site "$SATURN_SOURCE" --cache "$DS_DC_CACHE"
```

Ожидаются V1 invalid_locator, пять V2 supported с восстановленными ячейками и coverage semantic_pending. Проверьте неизменность входного SHA после прогона. Shadow использует только локальные оригиналы и безсетевой перехват dispatch. Никакого нового GO, DEEPSEEK_API_KEY или запуска CAL для этой проверки не требуется.
