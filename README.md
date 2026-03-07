<div align="center">

# Multi Broken Extractor (MBE)
**Extractor yang broken di banyak situs sekaligus!** 🌐💔

</div>

---

## **📺 Supported Sites**

| Situs | Status | Keterangan |
|-------|--------|------------|
| **[animepahe.si](https://animepahe.si/)**         | ✅✅✅⬜⬜ | 60% tested, 40% unknown |
| **[nekopoi.care](https://nekopoi.care/)**         | ✅⬜⬜⬜⬜ | kadang-kiding (perlu cookies) |
| **[hentaicop.com](https://hentaicop.com/)**       | ✅✅⬜⬜⬜ | 20% tested, 80% unknown |
| **[tokusatsuindno.com](https://www.tokusatsuindo.com/)**       | ✅✅✅⬜⬜ | work,tapi mentok 360p kurasa  |
| **[minioppai.org](https://minioppai.org/)**       | ✅⬜⬜⬜⬜ | kadang-kiding, masih asal jadi |
| **[samehadaku.how](https://v1.samehadaku.how/)**  | ✅⬜⬜⬜⬜ | kadang-kadang |
---

## **NOTE**:

### **Extractor [nekopoi](/yt_dlp_plugins/extractor/nekopoi.py)**:

**Gunakan `--cookies-from-browser`**

**Contoh**:
    
    # Linux
    yt-dlp --cookies-from-browser 'brave+GNOMEKEYRING' <URL> 
    
    # Termux 
    gak bisa wkwkwk
    
    # windawg??, idk lol
    # maybe 
    yt-dlp --cookies-from-browser brave <URL>


**sesuaikan dengan browser dan keyring kalian**     
<!-- **Supported keyrings are: BASICTEXT, GNOMEKEYRING, KWALLET, KWALLET5, KWALLET6** -->
<!-- ****: -->
|**Supported keyrings are**:|
|---------------------------|
| `BASICTEXT`               |
| `GNOMEKEYRING`            | 
| `KWALLET`                 |
| `KWALLET5`                |
| `KWALLET6`                |

|**Supported browsers are**: |
|----------------------------|
| `brave`                    |
| `chrome`                   |
| `chromium`                 |
| `edge`                     |
| `firefox`                  |
| `opera`                    |
| `safari`                   |
| `vivaldi`                  |
| `whale`                    |
---
**ERROR**: `[nekopoi] Unable to download webpage: HTTP Error 468: <none> (caused by <HTTPError 468: <none>>)`

**Tinggal reload aja page nekopoi nya**  
**kalo masih error, yaudah sih (peduli apa gw)**

---

### **Extractor [animepahe](./nekopoi/yt_dlp_plugins/extractor/animepahe.py)**:
**Cukup export cookies sekali saja dari browser [firefox androwed](https://www.firefox.com/en-US/download/android/) meneggunakan Add-on [cookies.txt](https://github.com/hrdl-github/cookies-txt)**
    
- terus tinggal pake
    `yt-dlp <URL animepahe> --cookies /path/to/file/cokies.txt`

---

## **🎮 Juga Mampir ke Project Lain**:
- **[wibu-downloader](https://github.com/Asep5K/wibu-downloader)**

---

## **Why "Multi Broken"?**
- Kode asal jalan
- Filosofi: "Better broken than nothing"
---

## **Known Issues**
- Semua fitur adalah known issues
- Tapi semua known issues adalah fitur
- Gak semua video bisa di download/tonton, tapi pasti ada yang bisa
- Kalau error, coba lagi (mungkin broken-nya lagi istirahat)
- Kode nya berantakan njir
- Skill issue njir

---
## **IT WORKS ON MY MACHINE**

## **INSTALASI**

    python -m pip install -U https://github.com/Asep5K/yt-dlp-broken-extractor/archive/master.zip
---
