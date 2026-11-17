#!/usr/bin/env python3
"""DS-LV-02/P8: four-turn synthetic conversational continuity, 1 HTTP per invocation.
--self-test: offline; --turn-1|--turn-2|--turn-3|--turn-4: one POST each.
No redundant consent prompt. Local hidden key only, no tools, no real Saturn data.
Never rerun a consumed turn or modify its marker/report to retry.
"""
import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

ROOT=Path.home() / "ds-consult-validation"
LOG=ROOT/"logs"
STATE=LOG/"ds-lv-02-p8-dialogue-private.json"
MODEL="deepseek-flash"
URL="https://api.deepseek.com/chat/completions"
MAX_TOKENS=192
MAX_COST_USD=0.02
PROMPTS=(
    "Учебная карточка: ЛИРА-17 — питание 12 В, интерфейс RS-485; ОРБИТА-5 — питание 24 В, интерфейс Ethernet. Назови параметры ЛИРА-17.",
    "А у второй?",
    "Исправление учебной карточки: у ЛИРА-17 интерфейс Ethernet вместо RS-485, питание прежнее. Назови её актуальные параметры.",
    "Сравни интерфейсы обеих моделей и назови рабочую температуру ОРБИТА-5. Если температура не указана, сообщи об отсутствии данных."
)
SYSTEM="Ты проверяешь только синтетическую учебную карточку. Отвечай кратко на русском. Учитывай уточнения пользователя в текущем диалоге. Не выдумывай недостающие характеристики и не используй внешние источники."

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def marker(n):
    return LOG/f"ds-lv-02-p8-turn-{n}-attempted.marker"

def report_path(n):
    return LOG/f"ds-lv-02-p8-turn-{n}-redacted.json"

def estimate_peak(usage):
    prompt=usage.get("prompt_tokens")
    output=usage.get("completion_tokens")
    if not isinstance(prompt,int) or not isinstance(output,int) or prompt<0 or output<0:
        return None
    hit=usage.get("prompt_cache_hit_tokens")
    miss=usage.get("prompt_cache_miss_tokens")
    if not (isinstance(hit,int) and isinstance(miss,int) and hit>=0 and miss>=0 and hit+miss==prompt):
        hit,miss=0,prompt
    return round((miss*0.30+hit*0.006+output*1.20)/1_000_000,9)

def original_history(n):
    """Read only local private prior answers; require contiguous accepted turns."""
    if n==1:
        if STATE.exists():
            raise ValueError("P8_PRIVATE_STATE_ALREADY_EXISTS")
        return []
    if not STATE.is_file():
        raise ValueError("P8_PRIVATE_STATE_MISSING")
    doc=json.loads(STATE.read_text(encoding="utf-8"))
    if not isinstance(doc,dict) or doc.get("completed_turns")!=n-1:
        raise ValueError("P8_STATE_TURN_MISMATCH")
    turns=doc.get("turns")
    if not isinstance(turns,list) or len(turns)!=n-1:
        raise ValueError("P8_STATE_HISTORY_MISSING")
    history=[]
    for i,turn in enumerate(turns,1):
        evidence=report_path(i)
        if not evidence.is_file() or not marker(i).is_file():
            raise ValueError("P8_PREVIOUS_EVIDENCE_MISSING")
        recorded=json.loads(evidence.read_text(encoding="utf-8"))
        if recorded.get("status")!="TURN_COMPLETE_REVIEW_NEEDED":
            raise ValueError("P8_PREVIOUS_TURN_NOT_COMPLETE")
        if not (isinstance(turn,dict) and turn.get("turn")==i
                and turn.get("user")==PROMPTS[i-1]
                and isinstance(turn.get("assistant"),str)
                and hashlib.sha256(turn["assistant"].encode()).hexdigest()==recorded.get("answer_sha256")):
            raise ValueError("P8_PREVIOUS_HISTORY_TAMPERED")
        history.append(turn)
    return history

def build_messages(history,n):
    messages=[{"role":"system","content":SYSTEM}]
    for i,turn in enumerate(history,1):
        if turn["turn"]!=i:
            raise ValueError("NONCONTIGUOUS_HISTORY")
        messages.append({"role":"user","content":turn["user"]})
        messages.append({"role":"assistant","content":turn["assistant"]})
    messages.append({"role":"user","content":PROMPTS[n-1]})
    return messages

def total_previous_estimate(n):
    total=0.
    for i in range(1,n):
        doc=json.loads(report_path(i).read_text(encoding="utf-8"))
        cost=doc.get("peak_estimate_usd")
        if not isinstance(cost,(int,float)) or cost<0:
            raise ValueError("PREVIOUS_COST_UNKNOWN")
        total+=cost
    return total

def selftest():
    assert len(PROMPTS)==4 and "RS-485" in PROMPTS[0]
    assert PROMPTS[1]=="А у второй?" and "вместо RS-485" in PROMPTS[2]
    assert "рабочую температуру" in PROMPTS[3]
    fake=[
      {"turn":1,"user":PROMPTS[0],"assistant":"ЛИРА-17: 12 В, RS-485."},
      {"turn":2,"user":PROMPTS[1],"assistant":"ОРБИТА-5: 24 В, Ethernet."},
      {"turn":3,"user":PROMPTS[2],"assistant":"ЛИРА-17: 12 В, Ethernet."}
    ]
    for turn in range(1,5):
        m=build_messages(fake[:turn-1],turn)
        assert len(m)==2*turn
        assert m[-1]=={"role":"user","content":PROMPTS[turn-1]}
        assert sum(item["role"]=="assistant" for item in m)==turn-1
    assert estimate_peak({"prompt_tokens":100,"completion_tokens":50})==0.00009
    assert estimate_peak({"prompt_tokens":100,"completion_tokens":50,
                          "prompt_cache_hit_tokens":30,"prompt_cache_miss_tokens":70})==0.00008118
    assert estimate_peak({"prompt_tokens":100,"completion_tokens":50,
                          "prompt_cache_hit_tokens":30,"prompt_cache_miss_tokens":60})==0.00009
    assert not STATE.exists() or STATE.is_file()
    print("DS-LV-02 P8 FOUR-TURN DIALOGUE OFFLINE SELF-TEST: PASS")
    print("TURNS: 4 | MODEL: deepseek-flash | THINKING: disabled | TOOLS: none")
    print("NETWORK REQUESTS: 0 | API COST: $0")

def write_private(path,obj,replace=False):
    encoded=(json.dumps(obj,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
    tmp=path.with_suffix(path.suffix+".tmp")
    fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(encoded)
        if replace:
            os.replace(tmp,path)
        else:
            os.link(tmp,path)
            tmp.unlink()
    finally:
        if tmp.exists():
            tmp.unlink()

def run(n):
    if n not in (1,2,3,4):
        raise SystemExit("STOP: invalid turn index.")
    os.umask(0o077)
    LOG.mkdir(parents=True,exist_ok=True,mode=0o700)
    if marker(n).exists() or report_path(n).exists():
        raise SystemExit("STOP: this P8 turn has been attempted. NO RETRY.")
    for j in range(n+1,5):
        if marker(j).exists() or report_path(j).exists():
            raise SystemExit("STOP: later P8 attempt already exists.")
    try:
        history=original_history(n)
        prior_estimate=total_previous_estimate(n)
        messages=build_messages(history,n)
        if len(json.dumps(messages,ensure_ascii=False).encode("utf-8"))>12000:
            raise ValueError("PROMPT_TOO_LONG")
        conservative_next=(len(json.dumps(messages,ensure_ascii=False).encode("utf-8"))*0.30+
                           MAX_TOKENS*1.20)/1_000_000
        if prior_estimate+conservative_next>MAX_COST_USD:
            raise ValueError("P8_ORGANIZATIONAL_BUDGET_EXCEEDED")
    except Exception as error:
        raise SystemExit("STOP: P8 local preflight "+type(error).__name__)
    if not (sys.stdin.isatty() and sys.stderr.isatty()):
        raise SystemExit("STOP: interactive WSL terminal required.")
    key=getpass.getpass("DeepSeek API key (hidden, WSL only): ")
    if not key.strip():
        raise SystemExit("STOP: empty API key.")
    fd=os.open(str(marker(n)),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        f.write(f"P8 turn {n} reserved, one POST only. No retry.\n")
    result={
        "test_id":f"DS-LV-02-P8-TURN-{n}", "turn":n,
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "model_requested":MODEL, "thinking_requested":"disabled",
        "tools_declared":[], "max_tokens":MAX_TOKENS,
        "http_requests_attempted":0,"http_status":None,
        "response_model":None,"finish_reason":None,
        "reasoning_present":None,"tool_calls_present":None,
        "question":PROMPTS[n-1],"answer_preview":None,"answer_sha256":None,
        "usage":{},"peak_estimate_usd":None,
        "cumulative_peak_estimate_usd":None,
        "actual_billing_usd":None,"status":"INCONCLUSIVE","error_type":None
    }
    started=time.monotonic()
    try:
        reqbody={"model":MODEL,"thinking":{"type":"disabled"},
                 "messages":messages,"max_tokens":MAX_TOKENS,
                 "temperature":0,"stream":False,"tool_choice":"none"}
        request=urllib.request.Request(URL,data=json.dumps(reqbody,ensure_ascii=False).encode("utf-8"),method="POST",
            headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
        result["http_requests_attempted"]=1
        try:
            with urllib.request.build_opener(NoRedirect()).open(request,timeout=80) as resp:
                result["http_status"]=resp.status
                raw=resp.read(800001)
        except urllib.error.HTTPError as err:
            result["http_status"]=err.code
            result["status"]="HTTP_ERROR_STOP"
        else:
            if len(raw)>800000:
                raise ValueError("RESPONSE_TOO_LARGE")
            obj=json.loads(raw.decode("utf-8"))
            if not isinstance(obj,dict) or obj.get("error"):
                result["status"]="API_ERROR_STOP"
            else:
                result["response_model"]=obj.get("model")
                choices=obj.get("choices")
                choice=choices[0] if isinstance(choices,list) and len(choices)==1 and isinstance(choices[0],dict) else {}
                result["finish_reason"]=choice.get("finish_reason")
                msg=choice.get("message") if isinstance(choice.get("message"),dict) else {}
                answer=msg.get("content")
                result["reasoning_present"]=bool(msg.get("reasoning_content"))
                result["tool_calls_present"]=bool(msg.get("tool_calls"))
                usage=obj.get("usage")
                if isinstance(usage,dict):
                    result["usage"]={k:usage[k] for k in ("prompt_tokens","completion_tokens","total_tokens",
                         "prompt_cache_hit_tokens","prompt_cache_miss_tokens") if isinstance(usage.get(k),int)}
                result["peak_estimate_usd"]=estimate_peak(result["usage"])
                result["cumulative_peak_estimate_usd"]=round(prior_estimate+(result["peak_estimate_usd"] or 0),9) if result["peak_estimate_usd"] is not None else None
                if (result["http_status"]==200 and result["response_model"]==MODEL
                    and result["finish_reason"]=="stop" and isinstance(answer,str)
                    and answer.strip() and len(answer)<=1600
                    and result["reasoning_present"] is False and result["tool_calls_present"] is False
                    and result["peak_estimate_usd"] is not None
                    and result["cumulative_peak_estimate_usd"]<=MAX_COST_USD):
                    result["answer_preview"]=answer[:650]
                    result["answer_sha256"]=hashlib.sha256(answer.encode("utf-8")).hexdigest()
                    newstate={"completed_turns":n,"turns":history+
                              [{"turn":n,"user":PROMPTS[n-1],"assistant":answer}]}
                    write_private(STATE,newstate,replace=(n>1))
                    result["status"]="TURN_COMPLETE_REVIEW_NEEDED"
                else:
                    result["status"]="TURN_INCOMPLETE_OR_BUDGET_STOP"
    except Exception as error:
        result["error_type"]=type(error).__name__
        result["status"]="TRANSPORT_OR_PARSE_ERROR_STOP"
    finally:
        key=None
        request=None
        result["latency_ms"]=int((time.monotonic()-started)*1000)
        write_private(report_path(n),result)
        print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    if sys.argv[1:]==["--self-test"]:
        selftest()
    elif len(sys.argv)==2 and sys.argv[1] in ("--turn-1","--turn-2","--turn-3","--turn-4"):
        run(int(sys.argv[1][-1]))
    else:
        raise SystemExit("Usage: --self-test | --turn-1 | --turn-2 | --turn-3 | --turn-4")
