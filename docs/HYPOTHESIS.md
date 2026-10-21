# HYPOTHESIS.md - Kripto Bot Hipotez Dosyasi

Ilk yazim: 2026-09-01
Son guncelleme: 2026-09-01 (Gorev 10 -- gercek deneme sayisiyla hizalandi)

Bu dosyanin tek islevi **deneme sayisini sabitlemek.** Ne kadar cok
kombinasyon denenirse tesadufen iyi gorunen birini bulma olasiligi o kadar
artar. Duzeltme bu sayiya dayanir, dolayisiyla sayi dogru olmak zorunda.

---

## Test Edilecek Kurallar (v1 = SADECE KRIPTO)

### Kural 1: MOM_1W (Momentum 1 Hafta)
- **Tez:** Son 7 gun getirisi pozitif olan coinler devam eder
- **Sinyal:** 7 gunluk getiri > %X
- **Esikler:** {%5, %10, %15}

### Kural 2: REV_1D (Mean Reversion 1 Gun)
- **Tez:** Sert dususlerde tepki alimi gelir
- **Sinyal:** 24 saatte > %X dusus
- **Esikler:** {-5, -8, -12}

### Olculen tutma sureleri
{1 gun, 7 gun, 30 gun} -- kodda `forward_1d`, `forward_7d`, `forward_30d`.
(Onceki metin "3 gun" diyordu; kodda oyle bir ufuk yok, dokuman duzeltildi.)

---

## Toplam Deneme

**2 kural x 3 esik x 3 tutma suresi = 18 deneme**

`kurallar/motor.py -> get_all_rules()` 6 kural nesnesi doner,
`backtest/metrikler.py -> UFUKLAR` 3 ufuk tanimlar. 6 x 3 = 18.
Bu sayi metrik raporunun basinda her seferinde basilir.

### Onceki uyumsuzluk (duzeltildi)
BIST kurallari da akisa eklenmisti: `get_bist_rules()` 9 kural
(3 aile x 3 esik) donuyordu, yani gercek deneme sayisi **18 degil 45**'ti.
Gorev 10 ile v1 akisi yalnizca kripto kurallarini calistiriyor;
`get_bist_rules` kodda duruyor ama `backtest/olay_calismasi.py` ana akisindan
cagrilmiyor.

### Sembol carpani (ayrica akilda tutulacak)
18 deneme **her sembol icin** tekrarlaniyor. 9 gecerli sembolde
9 x 18 = 162 sembol-kural-ufuk kombinasyonu goruluyor. Kural bazli sonuca
bakarken bu carpan da coklu karsilastirma sorununa dahildir.

---

## Basari Kriterleri
- t-istatistigi > 3
- Gozlem sayisi > 100
- Maliyet sonrasi pozitif ortalama
- BTC'ye ve USDTTRY'ye gore fazla getiri (bkz. metriklerdeki `net_getiri`)

## Reddedilme Kriteri
Hicbir kombinasyon gecemezse -> Faz 0'a don, yeni hipotez yaz.

## Onemli Notlar
- BtcTurk TRY pariteleri kullanilacak
- Maliyet orani: %0.40 (gidis-donus, `config.ROUND_TRIP_COST`)
- USDTTRY deflator olarak kullanilacak (`deflator` tablosu)
- **Survivorship bias itirafi:** Sadece bugun listede olan pariteler test
  edildi. BtcTurk gecmis sembol listesi vermedigi icin bu bias bugun
  kapatilamiyor; `daily_snapshot` tablosu bugunden itibaren kayit tutuyor ki
  bir yil sonra kapatilabilsin.
- **MATICTRY dusuruldu:** MATIC -> POL olarak yeniden adlandirildi, parite
  borsada yok. Sembol listesi acilista `exchangeinfo` ile dogrulaniyor.
