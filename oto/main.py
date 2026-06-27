import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import requests
import urllib.parse
import os

# ── CAR API (RapidAPI) ───────────────────────────────────────────────────────
# Car API endpoint'leri — marka/model/motor teknik verilerini çeker
CARAPI_BASE    = "https://car-api2.p.rapidapi.com/api"
CARAPI_HEADERS = lambda key: {
    "x-rapidapi-host": "car-api2.p.rapidapi.com",
    "x-rapidapi-key":  key,
}

# Türkiye piyasasında satılan markalar ile Car API'deki karşılıkları
# (API İngilizce marka adı bekler, bazıları birebir eşleşmeyebilir)
MARKA_API_MAP = {
    "Toyota":"Toyota","Honda":"Honda","Volkswagen":"Volkswagen",
    "Renault":"Renault","Fiat":"Fiat","Ford":"Ford",
    "Hyundai":"Hyundai","Kia":"Kia","Peugeot":"Peugeot",
    "Opel":"Opel","Skoda":"Skoda","Seat":"Seat",
    "BMW":"BMW","Mercedes":"Mercedes-Benz","Audi":"Audi",
    "Volvo":"Volvo","Mazda":"Mazda","Nissan":"Nissan",
    "Dacia":"Dacia","Tesla":"Tesla","Togg":None,  # API'de Togg yok
}

@st.cache_data(ttl=86400, show_spinner=False)
def carapi_modeller_getir(api_key: str, marka: str, yil: int = 2024) -> list[dict]:
    """
    Car API'den belirli marka ve yıla ait modelleri + teknik verileri çeker.
    Dönen liste: [{"model": str, "yakit_turu": str, "motor_cc": int, ...}, ...]
    """
    api_marka = MARKA_API_MAP.get(marka)
    if not api_marka:
        return []
    try:
        # 1) O markaya ait modelleri çek
        r = requests.get(
            f"{CARAPI_BASE}/models",
            headers=CARAPI_HEADERS(api_key),
            params={"make": api_marka, "year": yil, "limit": 50},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        modeller = data.get("data", []) if isinstance(data, dict) else data
        return modeller
    except Exception:
        return []

@st.cache_data(ttl=86400, show_spinner=False)
def carapi_motor_getir(api_key: str, marka: str, model: str, yil: int = 2024) -> dict:
    """
    Belirli araç için motor/yakıt detaylarını çeker.
    """
    api_marka = MARKA_API_MAP.get(marka)
    if not api_marka:
        return {}
    try:
        r = requests.get(
            f"{CARAPI_BASE}/engines",
            headers=CARAPI_HEADERS(api_key),
            params={"make": api_marka, "model": model, "year": yil, "limit": 1},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("data", []) if isinstance(data, dict) else data
        return items[0] if items else {}
    except Exception:
        return {}

def yakit_turu_cevir(fuel_type: str) -> str:
    """Car API'den gelen İngilizce fuel_type → Türkçe"""
    ft = (fuel_type or "").lower()
    if "electric"  in ft: return "Elektrik"
    if "hybrid"    in ft: return "Hibrit"
    if "diesel"    in ft: return "Dizel"
    return "Benzin"

@st.cache_data(ttl=86400, show_spinner=False)
def carapi_veri_yukle(api_key: str) -> pd.DataFrame | None:
    """
    Tüm Türkiye markaları için Car API'den veri çeker ve
    mevcut sabit veriyle birleştirip zenginleştirilmiş DataFrame döner.
    Başarısız olursa None döner (fallback: sabit dict).
    """
    rows = []
    markalar = list(MARKA_API_MAP.keys())
    for marka in markalar:
        modeller = carapi_modeller_getir(api_key, marka, yil=2024)
        for m in modeller[:6]:  # Her markadan max 6 model (limit koruma)
            model_adi = m.get("name", m.get("model", ""))
            if not model_adi:
                continue
            motor = carapi_motor_getir(api_key, marka, model_adi, yil=2024)
            fuel  = yakit_turu_cevir(motor.get("fuel_type", ""))
            cc_raw = motor.get("displacement", 0) or 0
            try:
                cc = int(float(str(cc_raw).replace("L","").strip()) * 1000) if "." in str(cc_raw) else int(cc_raw)
            except Exception:
                cc = 1500
            rows.append({
                "marka": marka,
                "model": model_adi,
                "fuel_type_raw": motor.get("fuel_type",""),
                "motor_cc_api": cc,
                "yakit_turu_api": fuel,
            })
    if not rows:
        return None
    return pd.DataFrame(rows)

st.set_page_config(
    page_title="OtoKarar",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;600&display=swap');
*{font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Syne',sans-serif}
[data-testid="stAppViewContainer"]{background:#0F172A}
[data-testid="stSidebar"]{background:#0F172A!important;border-right:1px solid rgba(255,255,255,0.06)}
[data-testid="stSidebar"] *{color:#CBD5E1!important}
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3{color:#F1F5F9!important}
.hero{background:linear-gradient(135deg,#1E3A8A,#1D4ED8 55%,#2563EB);border-radius:20px;padding:40px 48px;margin-bottom:28px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-60px;right:-60px;width:280px;height:280px;background:radial-gradient(circle,rgba(96,165,250,.25),transparent 70%);border-radius:50%}
.hero-title{font-family:'Syne',sans-serif;font-size:2.1rem;font-weight:800;color:#fff;margin:0 0 8px}
.hero-sub{color:#BFDBFE;font-size:1rem;margin:0 0 24px}
.hero-stats{display:flex;gap:20px;flex-wrap:wrap}
.hstat{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:12px;padding:12px 20px;backdrop-filter:blur(8px)}
.hstat-v{font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;color:#fff}
.hstat-l{font-size:.7rem;color:#93C5FD;text-transform:uppercase;letter-spacing:.5px}
.sec-hd{display:flex;align-items:center;gap:12px;margin:32px 0 18px}
.sec-hd-ln{flex:1;height:1px;background:linear-gradient(90deg,#334155,transparent)}
.sec-hd-tx{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:1px;white-space:nowrap}
.card{background:#1E293B;border-radius:18px;overflow:hidden;margin-bottom:22px;border:1px solid rgba(255,255,255,.07)}
.card:hover{transform:translateY(-2px);box-shadow:0 16px 50px rgba(0,0,0,.4)}
.rs1{border-top:4px solid #F59E0B}.rs2{border-top:4px solid #94A3B8}.rs3{border-top:4px solid #CD7F32}.rs4{border-top:4px solid #334155}.rs5{border-top:4px solid #334155}
.imgw{position:relative;height:220px;overflow:hidden}
.imgw img{width:100%;height:100%;object-fit:cover;display:block}
.imgov{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(15,23,42,0) 30%,rgba(15,23,42,.85) 100%)}
.rbadge{position:absolute;top:14px;left:14px;font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;padding:5px 12px;border-radius:999px;backdrop-filter:blur(6px)}
.rb1{background:rgba(245,158,11,.85);color:#1C1004}
.rb2{background:rgba(148,163,184,.85);color:#0F172A}
.rb3{background:rgba(205,127,50,.85);color:#1C0A00}
.rb4{background:rgba(30,41,59,.85);color:#94A3B8;border:1px solid #334155}
.iscore{position:absolute;bottom:14px;right:14px;background:rgba(15,23,42,.82);border:1px solid rgba(59,130,246,.45);border-radius:10px;padding:6px 14px;backdrop-filter:blur(6px);text-align:center}
.iscore-v{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:800;color:#60A5FA;line-height:1}
.iscore-l{font-size:.62rem;color:#64748B;text-transform:uppercase}
.cbody{padding:22px 26px 26px}
.cname{font-family:'Syne',sans-serif;font-size:1.45rem;font-weight:800;color:#F1F5F9;margin:0 0 4px}
.cyear{font-size:.82rem;color:#64748B;margin-bottom:14px}
.cyear b{color:#94A3B8}
.prow{display:flex;align-items:flex-end;gap:14px;flex-wrap:wrap;margin-bottom:16px}
.p2e-l{font-size:.72rem;color:#475569;margin-bottom:2px}
.p2e-v{font-family:'Syne',sans-serif;font-size:1.75rem;font-weight:800;color:#60A5FA;line-height:1}
.ppill{border-radius:10px;padding:7px 14px}
.ppill-g{background:rgba(16,185,129,.1);border:1px solid rgba(16,185,129,.22)}
.ppill-g .pl{font-size:.68rem;color:#6EE7B7;margin-bottom:2px}
.ppill-g .pv{font-size:.9rem;font-weight:700;color:#10B981}
.ppill-a{background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.2)}
.ppill-a .pl{font-size:.68rem;color:#FDE68A;margin-bottom:2px}
.ppill-a .pv{font-size:.9rem;font-weight:700;color:#F59E0B}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px}
.badge{display:inline-block;padding:4px 12px;border-radius:999px;font-size:11px;font-weight:600}
.bf{background:rgba(16,185,129,.15);color:#34D399;border:1px solid rgba(16,185,129,.2)}
.bg{background:rgba(59,130,246,.15);color:#60A5FA;border:1px solid rgba(59,130,246,.2)}
.bs{background:rgba(148,163,184,.1);color:#94A3B8;border:1px solid rgba(148,163,184,.15)}
.bk{background:rgba(245,158,11,.12);color:#FBBF24;border:1px solid rgba(245,158,11,.2)}
.specrow{display:flex;background:rgba(15,23,42,.5);border:1px solid rgba(255,255,255,.05);border-radius:12px;overflow:hidden;margin-bottom:16px;flex-wrap:wrap}
.specitem{flex:1;min-width:90px;padding:12px 14px;border-right:1px solid rgba(255,255,255,.05);text-align:center}
.specitem:last-child{border-right:none}
.sv{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:700;color:#E2E8F0}
.sl{font-size:.68rem;color:#475569;margin-top:2px}
.rbox{background:rgba(37,99,235,.08);border:1px solid rgba(37,99,235,.2);border-radius:12px;padding:14px 16px;margin-bottom:14px}
.rtitle{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;color:#60A5FA;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.ritem{display:flex;align-items:flex-start;gap:8px;color:#93C5FD;font-size:.83rem;margin-bottom:5px;line-height:1.4}
.rdot{width:6px;height:6px;border-radius:50%;background:#3B82F6;flex-shrink:0;margin-top:6px}
.tbox{background:rgba(15,23,42,.6);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:16px 18px;margin-bottom:14px}
.ttitle{font-family:'Syne',sans-serif;font-size:.72rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.trow{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:.8rem;color:#475569}
.trow b{color:#94A3B8}
.thl{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.thlc{flex:1;min-width:90px;background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);border-radius:10px;padding:10px 12px;text-align:center}
.thlv{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:800;color:#60A5FA}
.thll{font-size:.65rem;color:#475569;margin-top:2px}
.town{display:flex;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.05);font-size:.73rem;color:#334155}
.town b{color:#475569}
.dnote{font-size:.68rem;color:#1E293B;margin-top:6px;font-style:italic}
.btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
.btn{flex:1;min-width:110px;padding:11px 12px;border-radius:10px;font-family:'Syne',sans-serif;font-weight:700;font-size:.78rem;text-decoration:none;text-align:center;display:inline-block;transition:opacity .2s}
.btn:hover{opacity:.82;text-decoration:none}
.btns{background:linear-gradient(135deg,#2563EB,#1D4ED8);color:#fff!important}
.btna{background:linear-gradient(135deg,#059669,#047857);color:#fff!important}
.btnb{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);color:#CBD5E1!important}
.sensbox{background:linear-gradient(135deg,rgba(245,158,11,.12),rgba(251,191,36,.07));border:1px solid rgba(245,158,11,.25);border-radius:14px;padding:18px 22px;margin:18px 0}
.sensbox h4{font-family:'Syne',sans-serif;color:#FBBF24;margin:0 0 8px;font-size:.95rem}
.sensbox p{color:#B45309;font-size:.84rem;margin:3px 0}
.sensbox b{color:#F59E0B}
.warnbox{background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:12px;padding:14px 18px;color:#FCA5A5;font-size:.84rem}
.footer{text-align:center;color:#1E293B;font-size:.72rem;padding:18px 0 6px;border-top:1px solid rgba(255,255,255,.04);margin-top:28px}
.footer span{color:#334155}
.stButton>button{background:linear-gradient(135deg,#2563EB,#1D4ED8)!important;color:#fff!important;border:none!important;border-radius:10px!important;font-weight:700!important;width:100%!important}
.price-info{background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.18);border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:.8rem;color:#6EE7B7}
.price-info b{color:#34D399}
/* ── Slider renk düzeltmesi: Streamlit default kırmızı → uygulamanın mavisi ── */
[data-testid="stSlider"] [data-baseweb="slider"] [role="slider"]{background:#2563EB!important;border-color:#2563EB!important}
[data-testid="stSlider"] [data-baseweb="slider"] div[class*="thumb"]{background:#2563EB!important;border-color:#1D4ED8!important}
[data-testid="stSlider"] [data-baseweb="slider"] div[class*="track"] div:first-child{background:#2563EB!important}
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stThumbValue"]{color:#60A5FA!important}
</style>""", unsafe_allow_html=True)

# ── MARKA VERİTABANI ────────────────────────────────────────────────────────
MARKA = {
    "Toyota":     "https://www.toyota.com.tr",
    "Honda":      "https://www.honda.com.tr",
    "Volkswagen": "https://www.volkswagen.com.tr",
    "Renault":    "https://www.renault.com.tr",
    "Fiat":       "https://www.fiat.com.tr",
    "Ford":       "https://www.ford.com.tr",
    "Hyundai":    "https://www.hyundai.com.tr",
    "Kia":        "https://www.kia.com/tr",
    "Peugeot":    "https://www.peugeot.com.tr",
    "Opel":       "https://www.opel.com.tr",
    "Skoda":      "https://www.skoda.com.tr",
    "Seat":       "https://www.seat.com.tr",
    "BMW":        "https://www.bmw.com.tr",
    "Mercedes":   "https://www.mercedes-benz.com.tr",
    "Audi":       "https://www.audi.com.tr",
    "Volvo":      "https://www.volvocars.com/tr",
    "Mazda":      "https://www.mazda.com.tr",
    "Nissan":     "https://www.nissan.com.tr",
    "Dacia":      "https://www.dacia.com.tr",
    "Togg":       "https://www.togg.com.tr",
    "Tesla":      "https://www.tesla.com/tr_TR",
}

DEFAULT_IMG = "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&h=400&fit=crop"

# ── WİKİPEDİA'DAN OTOMATİK GÖRSEL ÇEK ───────────────────────────────────────
# Wikipedia'nın açık API'sini kullanır — API anahtarı gerektirmez, ücretsiz ve legal.
# Her araç için İngilizce Wikipedia'da "(marka model)" başlıklı makaleyi arar,
# bulamazsa sadece model adını dener, o da olmazsa marka adıyla fallback yapar.

@st.cache_data(ttl=86400)  # 24 saat önbellek — her çalıştırmada istek atmaz
def wikipedia_gorsel_getir(marka: str, model: str) -> str:
    """
    Wikipedia API üzerinden araç görseli çeker.
    Sırasıyla şu arama terimlerini dener:
      1) "{marka} {model}" (örn: "Toyota Corolla")
      2) "{marka} {model} car"
      3) "{marka}" (marka fallback)
    İstek başarısız olursa DEFAULT_IMG döner.
    """
    arama_terimleri = [
        f"{marka} {model}",
        f"{marka} {model} car",
        f"{marka} {model} automobile",
        marka,
    ]

    headers = {"User-Agent": "OtoKarar/1.0 (streamlit-app; educational project)"}

    for terim in arama_terimleri:
        try:
            # Adım 1: Makale başlığını bul
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": terim,
                "srlimit": 3,
                "format": "json",
            }
            r = requests.get(search_url, params=search_params, headers=headers, timeout=4)
            r.raise_for_status()
            sonuclar = r.json().get("query", {}).get("search", [])
            if not sonuclar:
                continue

            # En alakalı başlığı seç (araç/otomobil içerenleri tercih et)
            baslik = None
            for s in sonuclar:
                t = s["title"].lower()
                if any(k in t for k in [marka.lower(), model.lower()]):
                    baslik = s["title"]
                    break
            if not baslik:
                baslik = sonuclar[0]["title"]

            # Adım 2: O makaledeki ilk görseli getir
            img_params = {
                "action": "query",
                "titles": baslik,
                "prop": "pageimages",
                "pithumbsize": 800,
                "format": "json",
            }
            r2 = requests.get(search_url, params=img_params, headers=headers, timeout=4)
            r2.raise_for_status()
            pages = r2.json().get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {}).get("source", "")
                if thumb:
                    return thumb

        except Exception:
            continue  # Hata olursa sıradaki terimi dene

    return DEFAULT_IMG


# ── SAHİBİNDEN / ARABAM GÜNCEL FİYAT BİLGİSİ ───────────────────────────────
# Sahibinden ve arabam.com, scraping'e karşı Cloudflare koruması kullanır.
# Bu yüzden direkt fiyat çekmek mümkün değil (403/captcha alınır).
# Yapılabilecek en iyi şey:
#   - Yıl aralığı filtreli arama linkleri oluşturmak (kullanıcı tıklayıp görür)
#   - Kendi iç veritabanındaki fiyatı göstermek
# Dilerseniz ileride bir proxy/scraper servisi (ScraperAPI, Zyte vb.) entegre edebilirsiniz.

def sahibinden_url(marka: str, model: str, yil_min: int, yil_max: int) -> str:
    q = urllib.parse.quote(f"{marka} {model}")
    return (
        f"https://www.sahibinden.com/otomobil?query={q}"
        f"&year_min={yil_min}&year_max={yil_max}"
    )

def arabam_url(marka: str, model: str, yil_min: int, yil_max: int) -> str:
    slug_marka = marka.lower().replace(" ", "-")
    slug_model = model.lower().replace(" ", "-")
    return (
        f"https://www.arabam.com/ikinci-el/otomobil/{slug_marka}-{slug_model}"
        f"?minYear={yil_min}&maxYear={yil_max}"
    )

# ── SIFIR FİYAT VERİTABANI ──────────────────────────────────────────────────
SIFIR = {
    "Toyota Corolla":1_450_000,"Toyota Corolla Cross":1_750_000,"Toyota Yaris":1_100_000,"Toyota RAV4":2_400_000,
    "Honda Civic":1_620_000,"Honda HR-V":1_890_000,
    "Volkswagen Polo":1_250_000,"Volkswagen Golf":1_620_000,"Volkswagen Tiguan":2_650_000,"Volkswagen Passat":2_100_000,
    "Renault Clio":980_000,"Renault Megane":1_380_000,"Renault Austral":2_050_000,"Renault Espace":2_850_000,
    "Fiat Egea":1_050_000,"Fiat Egea Cross":1_280_000,
    "Ford Focus":1_580_000,"Ford Kuga":2_350_000,"Ford Puma":1_620_000,
    "Hyundai i20":1_100_000,"Hyundai Elantra":1_480_000,"Hyundai Tucson":2_200_000,"Hyundai Santa Fe":3_100_000,
    "Kia Picanto":920_000,"Kia Ceed":1_450_000,"Kia Sportage":2_280_000,"Kia Sorento":3_350_000,
    "Peugeot 208":1_150_000,"Peugeot 308":1_680_000,"Peugeot 3008":2_480_000,
    "Opel Corsa":1_080_000,"Opel Astra":1_580_000,"Opel Grandland":2_280_000,
    "Skoda Fabia":1_180_000,"Skoda Octavia":1_620_000,"Skoda Karoq":2_050_000,"Skoda Kodiaq":2_950_000,
    "Seat Ibiza":1_120_000,"Seat Leon":1_580_000,"Seat Ateca":2_000_000,
    "BMW 118i":2_750_000,"BMW 320i":3_450_000,"BMW X1":3_850_000,"BMW X3":4_950_000,
    "Mercedes A180":2_950_000,"Mercedes C200":4_350_000,"Mercedes GLA":4_100_000,
    "Audi A3":3_050_000,"Audi A4":4_200_000,"Audi Q3":3_900_000,
    "Volvo XC40":3_750_000,"Volvo XC60":4_850_000,
    "Mazda CX-5":2_500_000,"Nissan Juke":1_720_000,"Nissan Qashqai":2_280_000,
    "Dacia Sandero":800_000,"Dacia Duster":1_300_000,"Dacia Jogger":1_480_000,
    "Togg T10X":1_890_000,"Tesla Model 3":2_100_000,"Tesla Model Y":2_500_000,
}

ORT_YIL = {
    "Dacia Sandero":2019,"Dacia Duster":2018,"Dacia Jogger":2022,"Renault Clio":2019,
    "Renault Megane":2018,"Kia Picanto":2019,"Fiat Egea":2018,"Fiat Egea Cross":2020,
    "Hyundai i20":2020,"Opel Corsa":2020,"Seat Ibiza":2019,"Skoda Fabia":2020,
    "Peugeot 208":2020,"Toyota Yaris":2020,"Volkswagen Polo":2020,"Renault Austral":2022,
    "Toyota Corolla":2020,"Honda Civic":2019,"Hyundai Elantra":2020,"Volkswagen Golf":2020,
    "Ford Focus":2019,"Kia Ceed":2020,"Seat Leon":2020,"Skoda Octavia":2020,
    "Opel Astra":2021,"Mercedes A180":2020,"BMW 118i":2020,"Toyota Corolla Cross":2021,
    "Honda HR-V":2021,"Nissan Juke":2020,"Ford Puma":2021,"Peugeot 308":2021,
    "Hyundai Tucson":2021,"Kia Sportage":2021,"Skoda Karoq":2020,"Seat Ateca":2020,
    "Volkswagen Tiguan":2020,"Ford Kuga":2021,"Opel Grandland":2021,"Renault Espace":2023,
    "Peugeot 3008":2021,"Nissan Qashqai":2021,"Toyota RAV4":2020,"Mazda CX-5":2019,
    "Volvo XC40":2020,"Audi Q3":2020,"BMW X1":2020,"Mercedes GLA":2021,
    "Audi A3":2020,"BMW 320i":2020,"Volkswagen Passat":2019,"Audi A4":2019,
    "Mercedes C200":2019,"Hyundai Santa Fe":2021,"Kia Sorento":2021,"Skoda Kodiaq":2020,
    "BMW X3":2020,"Volvo XC60":2020,"Togg T10X":2023,"Tesla Model 3":2021,"Tesla Model Y":2022,
}

# ── VERİ ─────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    try:
        return pd.read_csv("cars.csv")
    except Exception:
        d = {
            'marka': ['Toyota','Toyota','Toyota','Toyota','Honda','Honda','Volkswagen','Volkswagen','Volkswagen','Volkswagen','Renault','Renault','Renault','Renault','Fiat','Fiat','Ford','Ford','Ford','Hyundai','Hyundai','Hyundai','Hyundai','Kia','Kia','Kia','Kia','Peugeot','Peugeot','Peugeot','Opel','Opel','Opel','Skoda','Skoda','Skoda','Skoda','Seat','Seat','Seat','BMW','BMW','BMW','BMW','Mercedes','Mercedes','Mercedes','Audi','Audi','Audi','Volvo','Volvo','Mazda','Nissan','Nissan','Dacia','Dacia','Dacia','Togg','Tesla','Tesla'],
            'model': ['Corolla','Corolla Cross','Yaris','RAV4','Civic','HR-V','Polo','Golf','Tiguan','Passat','Clio','Megane','Austral','Espace','Egea','Egea Cross','Focus','Kuga','Puma','i20','Elantra','Tucson','Santa Fe','Picanto','Ceed','Sportage','Sorento','208','308','3008','Corsa','Astra','Grandland','Fabia','Octavia','Karoq','Kodiaq','Ibiza','Leon','Ateca','118i','320i','X1','X3','A180','C200','GLA','A3','A4','Q3','XC40','XC60','CX-5','Juke','Qashqai','Sandero','Duster','Jogger','T10X','Model 3','Model Y'],
            'yil':   [2023]*61,
            'fiyat': [950000,1150000,750000,1650000,1050000,1250000,850000,1100000,1800000,1400000,620000,920000,1350000,1950000,680000,820000,1050000,1550000,1050000,720000,980000,1450000,2100000,590000,950000,1500000,2200000,750000,1100000,1600000,700000,1000000,1500000,780000,1050000,1350000,1950000,730000,1000000,1300000,1800000,2200000,2500000,3200000,1900000,2800000,2600000,1950000,2700000,2500000,2400000,3100000,1600000,1100000,1450000,520000,850000,950000,1890000,2100000,2500000],
            'yakit_turu': ['Benzin','Hibrit','Benzin','Hibrit','Benzin','Hibrit','Benzin','Benzin','Dizel','Dizel','Benzin','Benzin','Hibrit','Hibrit','Benzin','Benzin','Benzin','Hibrit','Hibrit','Benzin','Benzin','Hibrit','Hibrit','Benzin','Benzin','Hibrit','Hibrit','Benzin','Benzin','Hibrit','Benzin','Hibrit','Hibrit','Benzin','Benzin','Benzin','Dizel','Benzin','Benzin','Benzin','Benzin','Benzin','Benzin','Dizel','Benzin','Benzin','Benzin','Benzin','Benzin','Benzin','Hibrit','Hibrit','Benzin','Benzin','Hibrit','Benzin','Benzin','Benzin','Elektrik','Elektrik','Elektrik'],
            'motor_cc': [1600,1800,1500,2500,1500,1500,1000,1500,2000,2000,1000,1300,1200,1200,1400,1400,1500,2500,1000,1000,1600,1600,1600,1000,1500,1600,1600,1200,1200,1600,1200,1200,1200,1000,1500,1500,2000,1000,1500,1500,1500,2000,1500,2000,1300,1500,1300,1500,2000,1500,1500,2000,2500,1000,1500,1000,1000,1000,0,0,0],
            'yakit_tuketimi': [6.2,4.8,5.8,5.1,6.8,5.2,5.5,6.5,6.8,5.9,5.2,6.1,5.0,5.3,6.8,7.1,6.9,6.2,5.1,5.8,7.2,6.1,6.8,5.5,6.8,6.0,6.5,5.8,6.2,5.8,5.9,5.2,5.6,5.4,6.2,7.0,6.8,5.5,6.3,7.1,6.5,7.1,7.0,6.8,6.2,7.0,6.8,6.8,7.2,7.5,6.2,5.8,7.8,6.5,5.8,5.9,7.1,6.8,0,0,0],
            'bagaj_lt': [361,487,286,580,519,437,351,380,615,586,391,521,500,697,500,430,375,540,456,352,458,620,571,255,395,587,813,311,412,520,309,422,514,380,600,521,765,355,380,510,360,480,540,550,370,455,421,380,480,530,460,505,522,354,504,328,467,712,0,542,854],
            'koltuk': [5,5,5,5,5,5,5,5,5,5,5,5,5,7,5,5,5,5,5,5,5,5,7,5,5,5,7,5,5,5,5,5,5,5,5,5,7,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,7,5,5,5],
            'guvenlik_puani': [5,5,4,5,5,5,4,5,5,5,4,4,5,5,3,3,5,5,4,4,5,5,5,3,4,5,5,4,5,5,4,5,5,4,5,5,5,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,4,5,3,3,3,5,5,5],
            'bakim_maliyet': [2,2,1,2,2,2,1,2,3,3,1,1,2,2,1,1,2,2,2,1,2,2,3,1,2,2,3,1,2,2,1,2,2,1,2,2,3,1,2,2,3,3,3,3,3,3,3,3,3,3,3,3,2,2,2,1,1,1,2,3,3],
            'vites': ['otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','manuel','otomatik','otomatik','otomatik','manuel','manuel','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','otomatik','manuel','manuel','manuel','otomatik','otomatik','otomatik'],
            'segment': ['sedan','suv','hatchback','suv','sedan','suv','hatchback','hatchback','suv','sedan','hatchback','sedan','suv','suv','sedan','suv','hatchback','suv','suv','hatchback','sedan','suv','suv','hatchback','hatchback','suv','suv','hatchback','hatchback','suv','hatchback','hatchback','suv','hatchback','sedan','suv','suv','hatchback','hatchback','suv','hatchback','sedan','suv','suv','hatchback','sedan','suv','sedan','sedan','suv','suv','suv','suv','suv','suv','hatchback','suv','suv','suv','sedan','suv'],
        }
        return pd.DataFrame(d)

df_all = load_data()

# ── API VERİSİYLE ZENGİNLEŞTİR ───────────────────────────────────────────────
# Eğer kullanıcı API key girip güncelleme yaptıysa, yakit_turu ve motor_cc
# alanlarını Car API'den gelen güncel verilerle ezmek için kullanılır.
if "api_df" in st.session_state:
    api_df = st.session_state["api_df"]
    # model adını normalize et (küçük harf, boşluksuz karşılaştırma)
    api_df["_key"] = (api_df["marka"].str.lower() + api_df["model"].str.lower().str.replace(" ",""))
    df_all["_key"] = (df_all["marka"].str.lower() + df_all["model"].str.lower().str.replace(" ",""))
    merged = df_all.merge(
        api_df[["_key","yakit_turu_api","motor_cc_api"]],
        on="_key", how="left"
    )
    # Sadece eşleşen satırlarda API verisini kullan
    mask = merged["yakit_turu_api"].notna()
    merged.loc[mask, "yakit_turu"] = merged.loc[mask, "yakit_turu_api"]
    merged.loc[mask & (merged["motor_cc_api"] > 0), "motor_cc"] = \
        merged.loc[mask & (merged["motor_cc_api"] > 0), "motor_cc_api"]
    df_all = merged.drop(columns=["_key","yakit_turu_api","motor_cc_api"], errors="ignore")

# ── TOPSIS ───────────────────────────────────────────────────────────────────
def topsis(df, weights):
    cols = list(weights.keys())
    wv   = np.array([weights[c][0] for c in cols], dtype=float)
    dirs = [weights[c][1] for c in cols]
    mat  = df[cols].values.astype(float)
    nrm  = np.sqrt((mat**2).sum(axis=0)); nrm[nrm==0] = 1
    wm   = (mat/nrm) * (wv/wv.sum())
    ib   = np.array([wm[:,i].max() if dirs[i]=='max' else wm[:,i].min() for i in range(len(cols))])
    iw   = np.array([wm[:,i].min() if dirs[i]=='max' else wm[:,i].max() for i in range(len(cols))])
    db   = np.sqrt(((wm-ib)**2).sum(axis=1))
    dw   = np.sqrt(((wm-iw)**2).sum(axis=1))
    return dw / (db + dw + 1e-10)

# ── MTV & TCO ────────────────────────────────────────────────────────────────
MTV = {
    (1300,"0-3"):3200,(1300,"4-6"):2400,(1300,"7+"):1600,
    (1600,"0-3"):6800,(1600,"4-6"):5100,(1600,"7+"):3400,
    (2000,"0-3"):12500,(2000,"4-6"):9400,(2000,"7+"):6200,
    (2500,"0-3"):18000,(2500,"4-6"):13500,(2500,"7+"):9000,
    (0,"0-3"):1200,(0,"4-6"):900,(0,"7+"):600,
}

def get_mtv(cc, yas):
    k = 0 if cc==0 else 1300 if cc<=1300 else 1600 if cc<=1600 else 2000 if cc<=2000 else 2500
    y = "0-3" if yas<=3 else "4-6" if yas<=6 else "7+"
    return MTV.get((k, y), 5000)

def hesapla_tco(row, km, yil):
    yas = 2025 - int(row['yil'])
    mtv = get_mtv(int(row['motor_cc']), yas)
    zo  = 4500
    ka  = int(row['fiyat']) * 0.03
    mu  = 900
    yak = (km*0.18*5.0) if row['yakit_turu']=='Elektrik' else \
          (km/100)*float(row['yakit_tuketimi'])*(40.0 if row['yakit_turu']=='Dizel' else 42.0)
    bak = {1:8000, 2:14000, 3:22000}.get(int(row['bakim_maliyet']), 12000)
    las = 4500
    top = mtv + zo + ka + mu + yak + bak + las
    return {
        'MTV': int(mtv), 'Zorunlu Sigorta': int(zo),
        'Kasko': int(ka), 'Muayene': int(mu),
        f'Yakit ({km:,} km)': int(yak),
        'Bakim/Servis': int(bak), 'Lastik': int(las),
        'yillik': int(top), 'aylik': int(top/12),
        'toplam': int(row['fiyat']) + int(top*yil),
    }

# ── GEREKÇE ──────────────────────────────────────────────────────────────────
def gerekceler(row, profil, tco):
    g = []
    if float(row['fiyat']) <= profil['butce']:
        g.append("Butceye uygun fiyat")
    if profil['aile'] in ['Cocuklu Aile','Genis Aile'] and int(row['bagaj_lt'])>=500:
        g.append(f"Genis bagaj hacmi ({int(row['bagaj_lt'])} lt) - aile icin ideal")
    if profil['aile']=='Genis Aile' and int(row['koltuk'])>=7:
        g.append("7 koltuklu yapilandirma - buyuk aile")
    if profil['kullanim']=='Uzun Yol' and float(row['yakit_tuketimi'])<=6.0:
        g.append(f"Uzun yolda dusuk tuketim ({row['yakit_tuketimi']} L/100km)")
    if profil['kullanim']=='Sehir Ici' and row['yakit_turu'] in ['Hibrit','Elektrik']:
        g.append(f"{row['yakit_turu']} motor - sehirde yakit tasarrufu")
    if int(row['guvenlik_puani'])==5:
        g.append("Euro NCAP 5 yildiz guvenlik puani")
    if tco['aylik'] < 15000:
        g.append(f"Makul aylik sahiplik maliyeti ({tco['aylik']:,} TL/ay)")
    if int(row['bakim_maliyet'])==1:
        g.append("Dusuk bakim maliyeti avantaji")
    return (g if g else ["Tercihlerinizle genel uyumluluk"])[:4]

# ── RADAR CHART ───────────────────────────────────────────────────────────────
def radar_chart(df_r):
    cats = ['Fiyat Uyumu','Yakit Verimi','Guvenlik','Bagaj','Dusuk Bakim']
    # Birbirinden net ayrışan renkler: mavi, turuncu, yeşil
    RADAR_COLORS = [
        ('#3B82F6', 'rgba(59,130,246,0.25)'),   # Mavi
        ('#F97316', 'rgba(249,115,22,0.25)'),    # Turuncu
        ('#22C55E', 'rgba(34,197,94,0.25)'),     # Yeşil
    ]
    fig  = go.Figure()
    for i, (_, row) in enumerate(df_r.iterrows()):
        v = [
            max(0, 10 - float(row['fiyat'])/300000),
            max(0, 10 - float(row.get('yakit_tuketimi', 7))),
            float(row['guvenlik_puani'])*2,
            min(10, float(row['bagaj_lt'])/90),
            (4 - int(row['bakim_maliyet']))*3.33,
        ]
        line_c, fill_c = RADAR_COLORS[i % 3]
        fig.add_trace(go.Scatterpolar(
            r=v+[v[0]], theta=cats+[cats[0]],
            fill='toself', name=f"{row['marka']} {row['model']}",
            line_color=line_c, fillcolor=fill_c,
            line=dict(width=2.5)
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,10], tickfont_size=9,
                            gridcolor='rgba(255,255,255,.06)', linecolor='rgba(255,255,255,.08)'),
            angularaxis=dict(tickfont=dict(color='#94A3B8', size=11)),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True,
        legend=dict(font=dict(color='#94A3B8', size=11), bgcolor='rgba(0,0,0,0)'),
        margin=dict(t=40,b=40,l=40,r=40), height=400,
        font=dict(family='DM Sans')
    )
    return fig

# ── CAR API KEY — .env dosyasından okunur (güvenlik için kod içine yazılmaz) ─
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

# Uygulama ilk açıldığında otomatik veri çek (session_state'te yoksa)
if RAPIDAPI_KEY and "api_df" not in st.session_state:
    with st.spinner("🔄 Car API'den araç verisi yükleniyor..."):
        _api_df = carapi_veri_yukle(RAPIDAPI_KEY)
    if _api_df is not None and not _api_df.empty:
        st.session_state["api_df"] = _api_df

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
import os as _os
_LOGO_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "otokarar_logo.png")

with st.sidebar:
    if _os.path.exists(_LOGO_PATH):
        st.image(_LOGO_PATH, use_container_width=True)
    else:
        st.markdown("### 🚘 OtoKarar")
    st.markdown("---")
    if "api_df" in st.session_state:
        st.caption(f"📡 Car API aktif — {len(st.session_state['api_df'])} araç verisi")
    st.markdown("---")

    st.markdown("### Profiliniz")
    aile      = st.selectbox("Aile Yapisi",    ["Bekar","Cift","Cocuklu Aile","Genis Aile"])
    kullanim  = st.selectbox("Kullanim Amaci", ["Sehir Ici","Uzun Yol","Karma"])
    yillik_km = st.select_slider("Yillik Km",
                    options=[5000,10000,15000,20000,30000,50000], value=15000,
                    format_func=lambda x: f"{x:,} km")
    kac_yil   = st.slider("Kac Yil Kullanacaksiniz?", 1, 10, 5)
    st.markdown("---")
    st.markdown("### Butce")
    butce = st.select_slider(
        "Maksimum Butce (TL)",
        options=list(range(400000, 3550000, 50000)),
        value=1200000,
        format_func=lambda x: f"{x:,} TL".replace(",", ".")
    )
    st.markdown("---")

    st.markdown("### Tercihler")
    yakit_t   = st.multiselect("Yakit Turu",  ["Benzin","Dizel","Hibrit","Elektrik"], default=["Benzin","Hibrit"])
    vites_t   = st.multiselect("Vites Tipi",  ["otomatik","manuel"], default=["otomatik"])
    segment_t = st.multiselect("Arac Tipi",   ["sedan","hatchback","suv"], default=["sedan","hatchback","suv"])
    st.markdown("---")
    with st.expander("⚙️ Gelismis: Oncelik Agirliklar", expanded=False):
        st.caption("1 = az onemli  /  5 = cok onemli")
        d = (4,3,5,5,3) if aile in ["Cocuklu Aile","Genis Aile"] \
            else (3,5,4,3,3) if kullanim=="Uzun Yol" else (4,4,3,2,3)
        w_f = st.slider("Fiyat onceligi",     1,5,d[0])
        w_y = st.slider("Yakit tasarrufu",    1,5,d[1])
        w_g = st.slider("Guvenlik",           1,5,d[2])
        w_b = st.slider("Bagaj / Alan",       1,5,d[3])
        w_k = st.slider("Dusuk bakim",        1,5,d[4])

# yil_min/yil_max — sahibinden/arabam linkleri için sabit (son 5 yıl)
yil_min, yil_max = 2020, 2025

df_f = df_all[
    (df_all['fiyat'] <= butce) &
    (df_all['yakit_turu'].isin(yakit_t or list(df_all['yakit_turu'].unique()))) &
    (df_all['vites'].isin(vites_t or list(df_all['vites'].unique()))) &
    (df_all['segment'].isin(segment_t or list(df_all['segment'].unique())))
].copy().reset_index(drop=True)

if aile == "Genis Aile":
    alt = df_f[df_f['koltuk'] >= 7]
    if not alt.empty: df_f = alt.reset_index(drop=True)

if df_f.empty:
    st.markdown('<div class="warnbox">Secilen kriterlere uygun arac bulunamadi. Butcenizi, yil araligini veya filtrelerinizi genisletin.</div>', unsafe_allow_html=True)
    st.stop()

df_f['fiyat_skor'] = 1 / (df_f['fiyat'] / df_f['fiyat'].max())
df_f['yakit_skor'] = 1 / (df_f['yakit_tuketimi'].replace(0, 0.01))
scores = topsis(df_f, {
    'fiyat_skor':    (w_f,'max'), 'yakit_skor': (w_y,'max'),
    'guvenlik_puani':(w_g,'max'), 'bagaj_lt':   (w_b,'max'), 'bakim_maliyet':(w_k,'min'),
})
df_f['skor'] = (scores*100).round(1)
df_s = df_f.assign(_s=scores).sort_values('_s',ascending=False).head(5).reset_index(drop=True)
profil = {'butce': butce, 'aile': aile, 'kullanim': kullanim}

# ── LOGO + STATS HEADER ──────────────────────────────────────────────────────
st.markdown(
    f'<div class="hero">'
    f'<div class="hero-title">🚘 OtoKarar &mdash; Akilli Arac Oneri Sistemi</div>'
    f'<div class="hero-sub">Butcenize, aile yapiniza ve yasam tarziniza gore kisisellestirilmis sifir arac onerileri</div>'
    f'<div class="hero-stats">'
    f'<div class="hstat"><div class="hstat-v">{len(df_all)}</div><div class="hstat-l">Arac Veritabani</div></div>'
    f'<div class="hstat"><div class="hstat-v">{len(df_f)}</div><div class="hstat-l">Kritere Uyan</div></div>'
    f'<div class="hstat"><div class="hstat-v">TOPSIS</div><div class="hstat-l">Algoritma</div></div>'
    f'<div class="hstat"><div class="hstat-v">2025–2026</div><div class="hstat-l">Model Yili</div></div>'
    f'</div></div>',
    unsafe_allow_html=True
)

# ── ÖNERİLER ─────────────────────────────────────────────────────────────────
RS   = ['rs1','rs2','rs3','rs4','rs5']
RLBL = ['1. Oneri','2. Oneri','3. Oneri','4. Oneri','5. Oneri']
RBC  = ['rb1','rb2','rb3','rb4','rb4']

st.markdown(
    '<div class="sec-hd"><div class="sec-hd-tx">Size Ozel Oneriler</div><div class="sec-hd-ln"></div></div>',
    unsafe_allow_html=True
)
st.caption(f"{len(df_f)} arac arasından TOPSIS ile siralandi — 100 uzerinden puan")

# Görselleri önceden toplu çek (paralel değil ama önbellekli)
with st.spinner("Arac gorselleri yukleniyor (Wikipedia API)..."):
    gorsel_cache = {}
    for _, row in df_s.iterrows():
        isim = f"{row['marka']} {row['model']}"
        if isim not in gorsel_cache:
            gorsel_cache[isim] = wikipedia_gorsel_getir(row['marka'], row['model'])

for i, (_, row) in enumerate(df_s.iterrows()):
    tco   = hesapla_tco(row, yillik_km, kac_yil)
    g     = gerekceler(row, profil, tco)
    isim  = f"{row['marka']} {row['model']}"
    site  = MARKA.get(row['marka'], "#")
    img   = gorsel_cache.get(isim, DEFAULT_IMG)
    sf    = SIFIR.get(isim, int(row['fiyat']))

    sah_link  = sahibinden_url(row['marka'], row['model'], yil_min, yil_max)
    arab_link = arabam_url(row['marka'], row['model'], yil_min, yil_max)

    stars   = "★" * int(row['guvenlik_puani']) + "☆" * (5 - int(row['guvenlik_puani']))
    g_html  = "".join(
        f'<div class="ritem"><div class="rdot"></div><span>{x}</span></div>'
        for x in g
    )
    tco_rows = "".join(
        f'<div class="trow"><span>{k}</span><span><b>{v:,} TL</b></span></div>'
        for k, v in tco.items()
        if k not in ['yillik','aylik','toplam']
    )
    tuketim = "18 kWh/100km" if row['yakit_turu']=='Elektrik' else f"{row['yakit_tuketimi']} L/100km"

    html = (
        f'<div class="card {RS[i]}">'
          f'<div class="imgw">'
            f'<img src="{img}" alt="{isim}" loading="lazy" '
            f'onerror="this.onerror=null;this.src=\'https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=800&h=400&fit=crop\'">'
            f'<div class="imgov"></div>'
            f'<span class="rbadge {RBC[i]}">{RLBL[i]}</span>'
            f'<div class="iscore">'
              f'<div class="iscore-v">{row["skor"]:.0f}</div>'
              f'<div class="iscore-l">/ 100</div>'
            f'</div>'
          f'</div>'
          f'<div class="cbody">'
            f'<div class="cname">{isim}</div>'
            f'<div class="cyear">2025 Model &nbsp;|&nbsp; <b>Sifir Arac</b></div>'
            f'<div class="prow">'
              f'<div>'
                f'<div class="p2e-l">Tahmini sifir liste fiyati</div>'
                f'<div class="p2e-v">{sf:,} TL</div>'
              f'</div>'
            f'</div>'
            f'<div class="badges">'
              f'<span class="badge bf">{row["yakit_turu"]}</span>'
              f'<span class="badge bg">{row["vites"].title()}</span>'
              f'<span class="badge bs">{row["segment"].upper()}</span>'
              f'<span class="badge bk">{int(row["koltuk"])} Koltuk</span>'
            f'</div>'
            f'<div class="specrow">'
              f'<div class="specitem"><div class="sv">{tuketim}</div><div class="sl">Tuketim</div></div>'
              f'<div class="specitem"><div class="sv">{int(row["bagaj_lt"])} lt</div><div class="sl">Bagaj</div></div>'
              f'<div class="specitem"><div class="sv">{stars}</div><div class="sl">Euro NCAP</div></div>'
              f'<div class="specitem"><div class="sv">{tco["aylik"]:,} TL</div><div class="sl">Aylik Maliyet</div></div>'
            f'</div>'
            f'<div class="rbox">'
              f'<div class="rtitle">Bu arac neden onerildi?</div>'
              f'{g_html}'
            f'</div>'
            f'<div class="tbox">'
              f'<div class="ttitle">Yillik Maliyet Tahmini</div>'
              f'{tco_rows}'
              f'<div class="thl">'
                f'<div class="thlc"><div class="thlv">{tco["yillik"]:,} TL</div><div class="thll">Yillik Toplam</div></div>'
                f'<div class="thlc"><div class="thlv">{tco["aylik"]:,} TL</div><div class="thll">Aylik Ort.</div></div>'
              f'</div>'
              f'<div class="town"><span>{kac_yil} yillik toplam sahiplik maliyeti</span><b>{tco["toplam"]:,} TL</b></div>'
              f'<div class="dnote">* Tahmin deger - piyasa ortalamalarına dayanir.</div>'
            f'</div>'
            f'<div class="btnrow">'
              f'<a href="{site}" target="_blank" class="btn btns">🌐 {row["marka"]} Resmi Sitesi</a>'
              f'<a href="{sah_link}" target="_blank" class="btn btnb">📋 Sahibinden (2. El)</a>'
              f'<a href="{arab_link}" target="_blank" class="btn btnb">📋 Arabam.com (2. El)</a>'
            f'</div>'
          f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

# ── BÜTÇE DUYARLILIK ─────────────────────────────────────────────────────────
st.markdown(
    '<div class="sec-hd"><div class="sec-hd-tx">Butce Duyarlilik Analizi</div><div class="sec-hd-ln"></div></div>',
    unsafe_allow_html=True
)
yb   = butce + 100_000
df_y = df_all[
    (df_all['fiyat'] <= yb) &
    (df_all['yakit_turu'].isin(yakit_t or list(df_all['yakit_turu'].unique()))) &
    (df_all['vites'].isin(vites_t or list(df_all['vites'].unique())))
].copy()
mev  = set(df_f.apply(lambda r: f"{r['marka']}{r['model']}", axis=1))
yeni = df_y[~df_y.apply(lambda r: f"{r['marka']}{r['model']}", axis=1).isin(mev)]

if not yeni.empty:
    ornek = ", ".join(f"{r['marka']} {r['model']}" for _, r in yeni.head(3).iterrows())
    st.markdown(
        f'<div class="sensbox">'
        f'<h4>Butcenizi 100.000 TL artirirsiniz...</h4>'
        f'<p>Yeni butce: <b>{yb:,} TL</b> &mdash; <b>{len(yeni)}</b> yeni arac secenegi eklenir.</p>'
        f'<p>One cikan yeni secenekler: <b>{ornek}</b></p>'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.markdown(
        '<div class="sensbox">'
        '<h4>Butce Analizi</h4>'
        '<p>Mevcut kriterlerde 100.000 TL artis onemli bir fark yaratmiyor.</p>'
        '<p>Segment veya yakit tipi secimini genisletmek daha fazla secenek sunabilir.</p>'
        '</div>',
        unsafe_allow_html=True
    )

# ── RADAR CHART ───────────────────────────────────────────────────────────────
st.markdown(
    '<div class="sec-hd"><div class="sec-hd-tx">Arac Karsilastirma (Radar)</div><div class="sec-hd-ln"></div></div>',
    unsafe_allow_html=True
)
al  = [f"{r['marka']} {r['model']}" for _, r in df_s.iterrows()]
sec = st.multiselect("Kiyaslamak istediginiz araclari secin (maks 3):", al, default=al[:3], max_selections=3)
if len(sec) >= 2:
    df_r = df_s[df_s.apply(lambda r: f"{r['marka']} {r['model']}", axis=1).isin(sec)]
    st.plotly_chart(radar_chart(df_r), width='stretch')
else:
    st.info("Radar chart icin en az 2 arac secin.")

# ── BAR CHART ─────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="sec-hd"><div class="sec-hd-tx">TOPSIS Skor Karsilastirmasi</div><div class="sec-hd-ln"></div></div>',
    unsafe_allow_html=True
)
db = df_s.copy()
db['isim'] = db['marka'] + ' ' + db['model']
x_min = max(0, db['skor'].min() - 3)   # minimum skor eksi 3 puan — farkları görünür kılar
fb = px.bar(
    db, x='skor', y='isim', orientation='h',
    color='skor', color_continuous_scale=['#1E3A8A','#3B82F6','#60A5FA'],
    labels={'skor':'TOPSIS Skoru (100 uzerinden)','isim':''}, text='skor'
)
fb.update_traces(texttemplate='%{text:.1f}', textposition='outside', marker_line_width=0)
fb.update_layout(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    coloraxis_showscale=False, margin=dict(t=10,b=10,l=10,r=60), height=250,
    font=dict(family='DM Sans', color='#94A3B8'),
    xaxis=dict(range=[x_min, db['skor'].max() + 5],
               gridcolor='rgba(255,255,255,.04)', zerolinecolor='rgba(255,255,255,.06)'),
    yaxis=dict(gridcolor='rgba(0,0,0,0)'),
)
st.plotly_chart(fb, width='stretch')

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="footer">'
    '<span>OtoKarar &mdash; TOPSIS Tabanli Arac Karar Destek Sistemi</span>'
    ' &nbsp;|&nbsp; '
    '<span>Karar Destek Sistemleri Dersi Projesi</span>'
    ' &nbsp;|&nbsp; '
    '<span>Gorseller: Wikipedia API &mdash; Veriler tahmindir, yatirim tavsiyesi degildir.</span>'
    '</div>',
    unsafe_allow_html=True
)
