import os, io, json, time
from datetime import datetime, timedelta
import requests
import pandas as pd
from flask import Flask, request, jsonify, send_file, Response

app = Flask(__name__)
DUFFEL_API_URL = "https://api.duffel.com/air/offer_requests"
SLEEP_BETWEEN_REQUESTS = 10.0
MAX_RETRIES = 3
LAST_RESULTS = {"rows": [], "params": {}}

HTML = r"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Vols</title>
<style>
body{font-family:-apple-system,sans-serif;max-width:1100px;margin:0 auto;padding:24px;background:#f5f5f7}
.card{background:white;padding:24px;border-radius:12px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.row{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.field{flex:1;min-width:180px}
label{display:block;font-size:13px;font-weight:600;margin-bottom:6px}
input,select{width:100%;padding:8px 12px;font-size:14px;border:1px solid #d2d2d7;border-radius:8px}
button{background:#0071e3;color:white;border:none;padding:10px 20px;font-size:15px;border-radius:8px;cursor:pointer}
button:disabled{background:#86868b}
.log{font-family:Menlo,monospace;font-size:12px;background:#1d1d1f;color:#e5e5ea;padding:12px;border-radius:8px;max-height:200px;overflow-y:auto}
.log-ok{color:#34c759}.log-empty{color:#86868b}.log-error{color:#ff3b30}.log-retry{color:#ff9f0a}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px;text-align:left;border-bottom:1px solid #e5e5ea}
th{background:#f5f5f7;font-weight:600;cursor:pointer}
tr.cheapest{background:#d4f4dd}
.progress{height:8px;background:#e5e5ea;border-radius:4px;overflow:hidden;margin:16px 0}
.bar{height:100%;background:#0071e3;width:0%}
</style></head><body>
<h1>Recherche de vols</h1>
<div class="card">
<div class="row">
<div class="field"><label>Origine</label><input id="origin" value="CCS"></div>
<div class="field"><label>Destination</label><input id="destination" value="PAR"></div>
<div class="field"><label>Classe</label><select id="cabin_class"><option value="economy">Economie</option><option value="premium_economy">Premium</option><option value="business">Business</option></select></div>
</div>
<div class="row">
<div class="field"><label>Aller du</label><input id="depart_start" type="date" value="2026-12-08"></div>
<div class="field"><label>Aller au</label><input id="depart_end" type="date" value="2026-12-20"></div>
<div class="field"><label>Retour du</label><input id="return_start" type="date" value="2027-03-08"></div>
<div class="field"><label>Retour au</label><input id="return_end" type="date" value="2027-03-11"></div>
</div>
<div class="row">
<div class="field"><label>Escales max</label><select id="max_connections"><option value="0">Direct</option><option value="1" selected>1 escale</option><option value="2">2 escales</option></select></div>
<div class="field"><label>Sejour max (j)</label><input id="max_stay_days" type="number" value="90"></div>
<div class="field"><label>Adultes</label><input id="adults" type="number" value="1" min="1" max="9"></div>
<div class="field" style="display:flex;align-items:flex-end"><button id="btn" onclick="go()">Lancer</button></div>
</div>
</div>
<div class="card" id="prog" style="display:none">
<div id="stat">...</div>
<div class="progress"><div class="bar" id="bar"></div></div>
<div class="log" id="log"></div>
<button onclick="exportXlsx()" id="exp" style="display:none;margin-top:10px">Export Excel</button>
</div>
<div class="card" id="res" style="display:none">
<table><thead><tr><th onclick="srt('prix')">Prix</th><th onclick="srt('aller')">Aller</th><th onclick="srt('retour')">Retour</th><th onclick="srt('sejour')">Sejour</th><th>Compagnies</th><th>Aller via</th><th>Retour via</th></tr></thead><tbody id="tb"></tbody></table>
</div>
<script>
var rows=[],sk='prix',sa=true;
function val(id){return document.getElementById(id).value}
function go(){
  document.getElementById('btn').disabled=true;
  document.getElementById('prog').style.display='block';
  document.getElementById('log').innerHTML='';
  document.getElementById('bar').style.width='0%';
  rows=[];
  var p={origin:val('origin'),destination:val('destination'),depart_start:val('depart_start'),depart_end:val('depart_end'),return_start:val('return_start'),return_end:val('return_end'),max_connections:val('max_connections'),max_stay_days:val('max_stay_days'),cabin_class:val('cabin_class'),adults:val('adults')};
  fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)}).then(function(r){
    var rd=r.body.getReader(),dc=new TextDecoder(),bf='';
    function pr(x){
      if(x.done){document.getElementById('btn').disabled=false;return}
      bf+=dc.decode(x.value,{stream:true});
      var ls=bf.split('\n\n');bf=ls.pop();
      ls.forEach(function(l){if(l.indexOf('data: ')===0){try{ev(JSON.parse(l.slice(6)))}catch(e){console.error(e)}}});
      return rd.read().then(pr);
    }
    return rd.read().then(pr);
  });
}
function ev(e){
  if(e.type==='start'){document.getElementById('stat').textContent='0 / '+e.total+' (environ '+Math.round(e.total*12/60)+' min)'}
  else if(e.type==='retry'){lg('['+e.i+'] rate limit, nouvel essai dans '+e.wait+'s','retry')}
  else if(e.type==='progress'){
    document.getElementById('bar').style.width=(e.i/e.total*100)+'%';
    document.getElementById('stat').textContent=e.i+' / '+e.total;
    if(e.status==='ok'){var r=e.row;lg('['+e.i+'] '+r.aller+' > '+r.retour+' : '+r.prix.toFixed(2)+' '+r.devise+' ('+r.compagnies+')','ok');rows.push(r);show()}
    else if(e.status==='empty'){lg('['+e.i+'] '+e.aller+' > '+e.retour+' : aucune','empty')}
    else if(e.status==='error'){lg('['+e.i+'] erreur '+e.error,'error')}
  }
  else if(e.type==='done'){document.getElementById('stat').textContent='Termine - '+e.count+' offres';if(e.count>0)document.getElementById('exp').style.display='inline-block'}
}
function lg(m,c){var l=document.getElementById('log'),d=document.createElement('div');d.className='log-'+c;d.textContent=m;l.appendChild(d);l.scrollTop=l.scrollHeight}
function srt(k){if(sk===k)sa=!sa;else{sk=k;sa=true}show()}
function show(){
  if(rows.length===0)return;
  document.getElementById('res').style.display='block';
  var s=rows.slice().sort(function(a,b){var x=a[sk],y=b[sk];if(typeof x==='number')return sa?x-y:y-x;return sa?String(x).localeCompare(y):String(y).localeCompare(x)});
  var mp=Math.min.apply(null,rows.map(function(r){return r.prix}));
  var tb=document.getElementById('tb');tb.innerHTML='';
  s.forEach(function(r){var tr=document.createElement('tr');if(r.prix===mp)tr.className='cheapest';tr.innerHTML='<td>'+r.prix.toFixed(2)+' '+r.devise+'</td><td>'+r.aller+'</td><td>'+r.retour+'</td><td>'+r.sejour+'j</td><td>'+r.compagnies+'</td><td>'+r.aller_via+' ('+r.aller_escales+')</td><td>'+r.retour_via+' ('+r.retour_escales+')</td>';tb.appendChild(tr)});
}
function exportXlsx(){window.location.href='/api/export'}
</script>
</body></html>"""


def daterange(s, e):
    for n in range((e - s).days + 1):
        yield s + timedelta(days=n)


def search_flights(token, origin, dest, d_out, d_in, mc, cc, adults, on_retry=None):
    h = {"Accept": "application/json", "Accept-Encoding": "gzip",
         "Content-Type": "application/json", "Duffel-Version": "v2",
         "Authorization": "Bearer " + token}
    pl = {"data": {"slices": [
        {"origin": origin, "destination": dest, "departure_date": d_out.isoformat()},
        {"origin": dest, "destination": origin, "departure_date": d_in.isoformat()}],
        "passengers": [{"type": "adult"}] * adults,
        "cabin_class": cc, "max_connections": mc}}
    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.post(DUFFEL_API_URL, json=pl, headers=h,
                              params={"return_offers": "true"}, timeout=60)
        except requests.RequestException as e:
            return None, "Reseau: " + str(e)
        if r.status_code == 429 and attempt < MAX_RETRIES:
            wait = 15 * (attempt + 1)
            try:
                wait = max(wait, int(r.headers.get("ratelimit-reset", 0)))
            except ValueError:
                pass
            if on_retry:
                on_retry(wait)
            time.sleep(wait)
            continue
        if r.status_code != 201:
            return None, "API " + str(r.status_code) + ": " + r.text[:200]
        return r.json().get("data", {}).get("offers", []), None
    return None, "Rate limit persistant"


def summary(offer, d_out, d_in):
    sl = offer.get("slices", [])
    os_ = sl[0].get("segments", []) if len(sl) > 0 else []
    is_ = sl[1].get("segments", []) if len(sl) > 1 else []
    ov = " -> ".join([s["origin"]["iata_code"] for s in os_] +
                     ([os_[-1]["destination"]["iata_code"]] if os_ else []))
    iv = " -> ".join([s["origin"]["iata_code"] for s in is_] +
                     ([is_[-1]["destination"]["iata_code"]] if is_ else []))
    al = sorted({s["marketing_carrier"]["name"] for s in os_ + is_})
    return {"aller": d_out.isoformat(), "retour": d_in.isoformat(),
            "sejour": (d_in - d_out).days,
            "prix": float(offer.get("total_amount", 0)),
            "devise": offer.get("total_currency", ""),
            "compagnies": ", ".join(al),
            "aller_escales": max(0, len(os_) - 1), "aller_via": ov,
            "retour_escales": max(0, len(is_) - 1), "retour_via": iv,
            "offer_id": offer.get("id", "")}


@app.route("/")
def index():
    return HTML


@app.route("/api/search", methods=["POST"])
def api_search():
    token = os.environ.get("DUFFEL_TOKEN")
    if not token:
        return jsonify({"error": "DUFFEL_TOKEN absent"}), 500
    d = request.json
    origin = d["origin"].upper().strip()
    dest = d["destination"].upper().strip()
    ds = datetime.strptime(d["depart_start"], "%Y-%m-%d").date()
    de = datetime.strptime(d["depart_end"], "%Y-%m-%d").date()
    rs = datetime.strptime(d["return_start"], "%Y-%m-%d").date()
    re_ = datetime.strptime(d["return_end"], "%Y-%m-%d").date()
    mc = int(d.get("max_connections", 1))
    msd = int(d.get("max_stay_days", 90))
    cc = d.get("cabin_class", "economy")
    adults = max(1, min(9, int(d.get("adults", 1) or 1)))

    combos = []
    for do in daterange(ds, de):
        for di in daterange(rs, re_):
            stay = (di - do).days
            if 0 < stay <= msd:
                combos.append((do, di))

    def stream():
        rows = []
        yield "data: " + json.dumps({"type": "start", "total": len(combos)}) + "\n\n"
        for i, (do, di) in enumerate(combos, 1):
            retries = []
            offers, err = search_flights(token, origin, dest, do, di, mc, cc, adults,
                                         on_retry=lambda w: retries.append(w))
            for w in retries:
                yield "data: " + json.dumps({"type": "retry", "i": i, "wait": w}) + "\n\n"
            base = {"type": "progress", "i": i, "total": len(combos),
                    "aller": do.isoformat(), "retour": di.isoformat()}
            if err:
                base.update({"status": "error", "error": err})
            elif not offers:
                base.update({"status": "empty"})
            else:
                row = summary(min(offers, key=lambda o: float(o["total_amount"])), do, di)
                rows.append(row)
                base.update({"status": "ok", "row": row})
            yield "data: " + json.dumps(base) + "\n\n"
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        LAST_RESULTS["rows"] = rows
        LAST_RESULTS["params"] = {"origin": origin, "destination": dest}
        yield "data: " + json.dumps({"type": "done", "count": len(rows)}) + "\n\n"

    return Response(stream(), mimetype="text/event-stream")


@app.route("/api/export")
def api_export():
    rows = LAST_RESULTS.get("rows", [])
    params = LAST_RESULTS.get("params", {})
    if not rows:
        return jsonify({"error": "Aucun resultat"}), 400
    df = pd.DataFrame(rows).sort_values("prix").reset_index(drop=True)
    df.columns = ["Aller", "Retour", "Sejour", "Prix", "Devise", "Compagnies",
                  "Aller esc", "Aller via", "Retour esc", "Retour via", "Offer ID"]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Vols", index=False)
    buf.seek(0)
    fn = "vols_" + params.get("origin", "X") + "_" + params.get("destination", "X") + ".xlsx"
    return send_file(buf, as_attachment=True, download_name=fn,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == "__main__":
    if not os.environ.get("DUFFEL_TOKEN"):
        print("ATTENTION : DUFFEL_TOKEN non defini.")
    port = int(os.environ.get("PORT", 5001))
    print("Ouvre http://localhost:%d" % port)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
