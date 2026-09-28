# Discord sorgu botu - Ruthless | Kanal kilitli
# Kütüphaneler: discord.py, aiohttp
# Kurulum: pip install discord.py aiohttp

import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput
import aiohttp
import json
import base64
import io
import os  # ← Token'ı ortam değişkeninden okumak için eklendi

# --- TOKEN: ORTAM DEĞİŞKENİNDEN OKU ---
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise SystemExit(
        "HATA: DISCORD_TOKEN ortam değişkeni tanımlı değil!\n"
        "Render'da Environment sekmesinden DISCORD_TOKEN ekleyin."
    )

# SADECE BU KANALDA ÇALIŞIR
IZINLI_KANAL_ID = 1553330402503036969

API_ADSOYAD = "https://solidarksystems.alwaysdata.net/adsoyad.php"
API_TC      = "https://solidarksystems.alwaysdata.net/tc.php"
API_AILE    = "https://solidarksystems.alwaysdata.net/ailepro.php"
API_VESIKA  = "https://solidarksystems.alwaysdata.net/vesika.php"
API_ISYERI  = "https://solidarksystems.alwaysdata.net/isyeri.php"
API_SGK     = "https://solidarksystems.alwaysdata.net/sgk.php"
API_ADRES   = "https://solidarksystems.alwaysdata.net/adres.php"
API_SULALE  = "https://solidarksystems.alwaysdata.net/sulale.php"
API_GSMTC   = "https://solidarksystems.alwaysdata.net/gsmtc.php"
API_TCGSM   = "https://solidarksystems.alwaysdata.net/tcgsm.php"
API_ADILILCE = "https://solidarksystems.alwaysdata.net/adililce.php"

FILTRE_ALANLAR = {"auth", "auth_alt", "vesika"}
REKLAM_DEGISTIR = {"@jessy_php": "Ruthless"}

REKLAM_AD = "Ruthless"
IMZA = f"\n\n— **{REKLAM_AD}**"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ---------------------- KANAL KİLİDİ ----------------------
@bot.check
async def sadece_izinli_kanal(ctx):
    return ctx.channel.id == IZINLI_KANAL_ID


@bot.event
async def on_message(message):
    # Bot kendi mesajını yoksay
    if message.author.bot:
        return
    # Sadece izinli kanaldaki mesajları işle
    if message.channel.id != IZINLI_KANAL_ID:
        return
    await bot.process_commands(message)


# ---------------------- YARDIMCILAR ----------------------
def temizle(metin) -> str:
    if not isinstance(metin, str):
        metin = str(metin)
    for eski, yeni in REKLAM_DEGISTIR.items():
        metin = metin.replace(eski, yeni)
    return metin


def kayitlari_formatla(kayitlar, baslik: str, ek_bilgi: str = "") -> str:
    if not kayitlar:
        return f"**{baslik}**\n{ek_bilgi}\n\n**Sonuç bulunamadı.**"

    satirlar = []
    for i, k in enumerate(kayitlar, 1):
        if not isinstance(k, dict):
            satirlar.append(f"**Kayıt {i}:** {temizle(k)}")
            continue
        if "hata" in k:
            satirlar.append(f"**Kayıt {i}**\nHata: {temizle(k['hata'])}")
            continue
        alanlar = []
        for kk, vv in k.items():
            if kk in FILTRE_ALANLAR:
                continue
            alanlar.append(f"{kk}: {temizle(vv)}")
        satirlar.append(f"**Kayıt {i}**\n" + "\n".join(alanlar))

    return (
        f"**{baslik}**\n{ek_bilgi}\n"
        f"Toplam Kayıt: {len(kayitlar)}\n\n" + "\n\n".join(satirlar)
    )


def esnek_veri(data):
    if data is None:
        return [], None

    durum = ""
    if isinstance(data, dict):
        for k in ("status", "durum"):
            if k in data:
                durum = str(data[k])
                break

    veri = None
    if isinstance(data, dict):
        for key in ("veri", "data", "kayitlar", "sonuclar", "sulale",
                    "adres", "adresler", "gsm", "gsmler", "tc",
                    "sonuc", "tcler", "numaralar", "kisiler"):
            if key in data:
                veri = data[key]
                break
        if veri is None:
            veri = data
    else:
        veri = data

    if veri is None or veri == "":
        return [], durum

    if isinstance(veri, list):
        kayitlar = [x for x in veri if x not in ("", None)]
    elif isinstance(veri, dict):
        kayitlar = [veri]
    else:
        kayitlar = []
    return kayitlar, durum


async def api_get(url: str, params: dict):
    connector = aiohttp.TCPConnector(ssl=False)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        async with session.get(url, params=params) as resp:
            text = await resp.text()
            status = resp.status
            try:
                data = json.loads(text)
            except Exception:
                data = None
            return data, text, status


# ---------------------- AD SOYAD İL İLÇE MODAL ----------------------
class AdSoyadModal(Modal, title="Ad Soyad İl İlçe Sorgu"):
    ad = TextInput(label="Ad", placeholder="Ad girin", required=True)
    soyad = TextInput(label="Soyad", placeholder="Soyad girin", required=True)
    il = TextInput(label="İl", placeholder="İl girin", required=True)
    ilce = TextInput(label="İlçe", placeholder="İlçe girin", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        params = {
            "ad": self.ad.value.strip(),
            "soyad": self.soyad.value.strip(),
            "il": self.il.value.strip(),
            "ilce": self.ilce.value.strip()
        }
        ek = (f"Ad: {self.ad.value}\nSoyad: {self.soyad.value}\n"
              f"İl: {self.il.value}\nİlçe: {self.ilce.value}")
        try:
            data, raw, status = await api_get(API_ADSOYAD, params)
            if status != 200:
                sonuc = (f"**Ad Soyad İl İlçe Sorgu**\n{ek}\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**Ad Soyad İl İlçe Sorgu**\n{ek}\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                veri = data.get("veri", []) if isinstance(data, dict) else []
                if veri == "" or veri is None:
                    veri = []
                sonuc = kayitlari_formatla(veri, "Ad Soyad İl İlçe Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**Ad Soyad İl İlçe Sorgu**\n{ek}\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- AD İL İLÇE MODAL ----------------------
class AdIlIlceModal(Modal, title="Ad İl İlçe Sorgu"):
    ad = TextInput(label="Ad", placeholder="Ad girin", required=True)
    il = TextInput(label="İl", placeholder="İl girin", required=True)
    ilce = TextInput(label="İlçe", placeholder="İlçe girin", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        params = {
            "ad": self.ad.value.strip(),
            "il": self.il.value.strip(),
            "ilce": self.ilce.value.strip()
        }
        ek = (f"Ad: {self.ad.value}\n"
              f"İl: {self.il.value}\nİlçe: {self.ilce.value}")
        try:
            data, raw, status = await api_get(API_ADILILCE, params)
            if status != 200:
                sonuc = (f"**Ad İl İlçe Sorgu**\n{ek}\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**Ad İl İlçe Sorgu**\n{ek}\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                veri = data.get("veri", []) if isinstance(data, dict) else []
                if veri == "" or veri is None:
                    veri = []
                elif isinstance(veri, dict):
                    veri = [veri]
                sonuc = kayitlari_formatla(veri, "Ad İl İlçe Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**Ad İl İlçe Sorgu**\n{ek}\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- TC SORGULAMA MODAL ----------------------
class TcModal(Modal, title="TC Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_TC, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**TC Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**TC Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, _ = esnek_veri(data)
                sonuc = kayitlari_formatla(kayitlar, "TC Sorgu Sonucu", f"TC: `{tc_val}`")
        except Exception as e:
            sonuc = (f"**TC Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- AİLE SORGULAMA MODAL ----------------------
class AileModal(Modal, title="Aile Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_AILE, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**Aile Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**Aile Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, _ = esnek_veri(data)
                sonuc = kayitlari_formatla(kayitlar, "Aile Sorgu Sonucu", f"TC: `{tc_val}`")
        except Exception as e:
            sonuc = (f"**Aile Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- VESİKA SORGULAMA MODAL ----------------------
class VesikaModal(Modal, title="Vesika Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()

        try:
            data, raw, status = await api_get(API_VESIKA, {"tc": tc_val})

            if status != 200:
                await gonder_dm(interaction, f"**Vesika Sorgu**\nTC: `{tc_val}`\n\n**API hatası: HTTP {status}**")
                return
            if data is None:
                await gonder_dm(interaction, f"**Vesika Sorgu**\nTC: `{tc_val}`\n\n**API JSON döndürmedi.**")
                return

            durum = data.get("durum", "")
            veri = data.get("veri", {}) or {}
            vesika_b64 = veri.get("vesika", "") if isinstance(veri, dict) else ""

            if durum != "basarili" or not vesika_b64:
                await gonder_dm(interaction, f"**Vesika Sorgu**\nTC: `{tc_val}`\n\n**Vesika bulunamadı.**\nDurum: {durum}")
                return

            try:
                raw_bytes = base64.b64decode(vesika_b64 + "=" * (-len(vesika_b64) % 4))
            except Exception:
                temiz_b64 = "".join(c for c in vesika_b64 if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")
                raw_bytes = base64.b64decode(temiz_b64 + "=" * (-len(temiz_b64) % 4))

            start = raw_bytes.find(b"\xff\xd8\xff")
            end = raw_bytes.rfind(b"\xff\xd9")
            jpeg_bytes = raw_bytes[start:end + 2] if (start != -1 and end != -1) else raw_bytes

            dosya = discord.File(io.BytesIO(jpeg_bytes), filename=f"vesika_{tc_val}.jpg")
            try:
                await interaction.user.send(
                    content=f"**Vesika Sorgu**\nTC: `{tc_val}`\nKayıt No: {veri.get('no','')}{IMZA}",
                    file=dosya
                )
                try:
                    await interaction.followup.send("Vesika DM olarak gönderildi.", ephemeral=True)
                except discord.errors.NotFound:
                    pass
            except discord.Forbidden:
                try:
                    await interaction.followup.send("DM gönderilemedi. DM'lerinizi açın.", ephemeral=True)
                except discord.errors.NotFound:
                    pass

        except Exception as e:
            await gonder_dm(interaction, f"**Vesika Sorgu**\nTC: `{tc_val}`\n\n**Bağlantı hatası:** `{type(e).__name__}: {e}`")


# ---------------------- İŞYERİ SORGULAMA MODAL ----------------------
class IsyeriModal(Modal, title="İşyeri Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_ISYERI, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**İşyeri Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**İşyeri Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, _ = esnek_veri(data)
                sonuc = kayitlari_formatla(kayitlar, "İşyeri Sorgu Sonucu", f"TC: `{tc_val}`")
        except Exception as e:
            sonuc = (f"**İşyeri Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- SGK SORGULAMA MODAL ----------------------
class SgkModal(Modal, title="SGK Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_SGK, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**SGK Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**SGK Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, durum = esnek_veri(data)
                ek = f"TC: `{tc_val}`"
                if durum and durum.lower() not in ("success", "basarili", "başarılı"):
                    ek += f"\nDurum: {durum}"
                sonuc = kayitlari_formatla(kayitlar, "SGK Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**SGK Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- ADRES SORGULAMA MODAL ----------------------
class AdresModal(Modal, title="Adres Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_ADRES, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**Adres Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**Adres Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, durum = esnek_veri(data)
                ek = f"TC: `{tc_val}`"
                if durum and durum.lower() not in ("success", "basarili", "başarılı"):
                    ek += f"\nDurum: {durum}"
                sonuc = kayitlari_formatla(kayitlar, "Adres Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**Adres Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- SÜLALE SORGULAMA MODAL ----------------------
class SulaleModal(Modal, title="Sülale Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_SULALE, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**Sülale Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**Sülale Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, durum = esnek_veri(data)
                ek = f"TC: `{tc_val}`"
                if durum and durum.lower() not in ("success", "basarili", "başarılı"):
                    ek += f"\nDurum: {durum}"
                sonuc = kayitlari_formatla(kayitlar, "Sülale Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**Sülale Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- GSM>TC SORGULAMA MODAL ----------------------
class GsmTcModal(Modal, title="GSM>TC Sorgu"):
    gsm = TextInput(label="GSM Numarası", placeholder="Örn: 5346997402 (başında 0 olmadan)",
                    required=True, min_length=10, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        gsm_val = self.gsm.value.strip().replace(" ", "").replace("-", "")
        if gsm_val.startswith("0"):
            gsm_val = gsm_val[1:]

        try:
            data, raw, status = await api_get(API_GSMTC, {"gsm": gsm_val})
            if status != 200:
                sonuc = (f"**GSM>TC Sorgu**\nGSM: `{gsm_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**GSM>TC Sorgu**\nGSM: `{gsm_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, durum = esnek_veri(data)
                ek = f"GSM: `{gsm_val}`"
                if durum and durum.lower() not in ("success", "basarili", "başarılı"):
                    ek += f"\nDurum: {durum}"
                sonuc = kayitlari_formatla(kayitlar, "GSM>TC Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**GSM>TC Sorgu**\nGSM: `{gsm_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- TC>GSM SORGULAMA MODAL ----------------------
class TcGsmModal(Modal, title="TC>GSM Sorgu"):
    tc = TextInput(label="TC Kimlik No", placeholder="11 haneli TC girin",
                   required=True, min_length=11, max_length=11)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        tc_val = self.tc.value.strip()
        try:
            data, raw, status = await api_get(API_TCGSM, {"tc": tc_val})
            if status != 200:
                sonuc = (f"**TC>GSM Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API hatası: HTTP {status}**\n```\n{temizle(raw[:1500])}\n```")
            elif data is None:
                sonuc = (f"**TC>GSM Sorgu**\nTC: `{tc_val}`\n\n"
                         f"**API JSON döndürmedi. Ham yanıt:**\n```\n{temizle(raw[:1500])}\n```")
            else:
                kayitlar, durum = esnek_veri(data)
                ek = f"TC: `{tc_val}`"
                if durum and durum.lower() not in ("success", "basarili", "başarılı"):
                    ek += f"\nDurum: {durum}"
                sonuc = kayitlari_formatla(kayitlar, "TC>GSM Sorgu Sonucu", ek)
        except Exception as e:
            sonuc = (f"**TC>GSM Sorgu**\nTC: `{tc_val}`\n\n"
                     f"**Bağlantı hatası:** `{type(e).__name__}: {e}`")
        await gonder_dm(interaction, sonuc)


# ---------------------- DM GÖNDERME ----------------------
async def gonder_dm(interaction: discord.Interaction, sonuc: str):
    if not sonuc.endswith(IMZA):
        sonuc = sonuc + IMZA

    try:
        if len(sonuc) <= 2000:
            await interaction.user.send(sonuc)
        else:
            for i in range(0, len(sonuc), 1990):
                await interaction.user.send(sonuc[i:i + 1990])
        try:
            await interaction.followup.send("Sonuç DM olarak gönderildi.", ephemeral=True)
        except discord.errors.NotFound:
            pass
    except discord.Forbidden:
        try:
            await interaction.followup.send("DM gönderilemedi. Lütfen DM'lerinizi açın.", ephemeral=True)
        except discord.errors.NotFound:
            pass
    except Exception as e:
        try:
            await interaction.followup.send(f"DM gönderilemedi: `{type(e).__name__}: {e}`", ephemeral=True)
        except discord.errors.NotFound:
            pass


# ---------------------- MENÜ ----------------------
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ad Soyad İl İlçe", style=discord.ButtonStyle.primary, custom_id="adsoyad_btn", row=0)
    async def adsoyad(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdSoyadModal())

    @discord.ui.button(label="Ad İl İlçe", style=discord.ButtonStyle.primary, custom_id="adililce_btn", row=0)
    async def adililce(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdIlIlceModal())

    @discord.ui.button(label="TC Sorgu", style=discord.ButtonStyle.success, custom_id="tc_btn", row=0)
    async def tcsorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TcModal())

    @discord.ui.button(label="Aile Sorgu", style=discord.ButtonStyle.secondary, custom_id="aile_btn", row=1)
    async def ailesorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AileModal())

    @discord.ui.button(label="Vesika Sorgu", style=discord.ButtonStyle.danger, custom_id="vesika_btn", row=1)
    async def vesikasorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VesikaModal())

    @discord.ui.button(label="İşyeri Sorgu", style=discord.ButtonStyle.primary, custom_id="isyeri_btn", row=1)
    async def isyerisorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(IsyeriModal())

    @discord.ui.button(label="SGK Sorgu", style=discord.ButtonStyle.success, custom_id="sgk_btn", row=2)
    async def sgksorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SgkModal())

    @discord.ui.button(label="Adres Sorgu", style=discord.ButtonStyle.secondary, custom_id="adres_btn", row=2)
    async def adressorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdresModal())

    @discord.ui.button(label="Sülale Sorgu", style=discord.ButtonStyle.primary, custom_id="sulale_btn", row=2)
    async def sulalesorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SulaleModal())

    @discord.ui.button(label="GSM>TC", style=discord.ButtonStyle.success, custom_id="gsmtc_btn", row=3)
    async def gsmtcsorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(GsmTcModal())

    @discord.ui.button(label="TC>GSM", style=discord.ButtonStyle.primary, custom_id="tcgsm_btn", row=3)
    async def tcgsmsorgu(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TcGsmModal())

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger, custom_id="kapat_btn", row=3)
    async def kapat(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Menü kapatıldı.", ephemeral=True)
        await interaction.message.delete()


# ---------------------- EVENTS ----------------------
@bot.event
async def on_ready():
    print(f"Bot hazır: {bot.user} | Reklam: {REKLAM_AD} | Kanal: {IZINLI_KANAL_ID}")


@bot.command(name="menu")
async def menu(ctx):
    # Çift güvenlik: kanal kontrolü
    if ctx.channel.id != IZINLI_KANAL_ID:
        return

    embed = discord.Embed(
        title="Sorgu Botu Menüsü",
        description="Aşağıdaki butonlardan birini seçin:\n\n"
                    "• **Ad Soyad İl İlçe** – ad, soyad, il, ilçe ile sorgu\n"
                    "• **Ad İl İlçe** – ad, il, ilçe ile sorgu (soyadsız)\n"
                    "• **TC Sorgu** – TC kimlik no ile sorgu\n"
                    "• **Aile Sorgu** – TC ile aile/akrabalık sorgusu\n"
                    "• **Vesika Sorgu** – TC ile vesika fotoğrafı\n"
                    "• **İşyeri Sorgu** – TC ile işyeri kaydı\n"
                    "• **SGK Sorgu** – TC ile SGK kaydı\n"
                    "• **Adres Sorgu** – TC ile adres kaydı\n"
                    "• **Sülale Sorgu** – TC ile geniş sülale kaydı\n"
                    "• **GSM>TC** – GSM numarası ile TC sorgusu\n"
                    "• **TC>GSM** – TC ile GSM numarası sorgusu",
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Ruthless")
    await ctx.send(embed=embed, view=MenuView())


bot.run(TOKEN)