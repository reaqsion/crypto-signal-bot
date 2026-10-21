"""Sembol listesini borsanin gercek listesiyle dogrular.

config.SYMBOLS sabit bir liste. Borsa degisiyor: MATIC -> POL olarak yeniden
adlandirildi, MATICTRY artik bos donuyor. Sabit listeye guvenmek sessizce
bos veri toplamak demek. Bot acilisinda exchangeinfo'dan dogruluyoruz.
"""
from data.btcturk_api import api


class SembolHatasi(Exception):
    pass


_onbellek = None


def borsa_sembolleri(yenile=False):
    """Borsada islem goren tum pariteler (set). Alinamazsa exception."""
    global _onbellek
    if _onbellek is not None and not yenile:
        return _onbellek

    info = api.get_exchange_info()
    if not info or "data" not in info:
        raise SembolHatasi(
            "exchangeinfo alinamadi. Sembol listesi dogrulanamiyor; "
            "sessizce devam etmek yerine duruyoruz."
        )

    semboller = info["data"].get("symbols")
    if not semboller:
        raise SembolHatasi(f"exchangeinfo bos 'symbols' dondu: {list(info['data'].keys())}")

    _onbellek = {s["name"] for s in semboller if "name" in s}
    if not _onbellek:
        raise SembolHatasi("exchangeinfo'da 'name' alani olan sembol yok.")

    return _onbellek


def dogrula(sembol_listesi, etiket="SYMBOLS"):
    """Borsada olmayan sembolleri UYARI basarak listeden cikarir.

    Doner: (gecerli_liste, eksik_liste)
    """
    borsada = borsa_sembolleri()
    gecerli = [s for s in sembol_listesi if s in borsada]
    eksik = [s for s in sembol_listesi if s not in borsada]

    for s in eksik:
        print(f"  ! UYARI: {etiket} icindeki '{s}' borsada yok, listeden cikarildi.")

    if not gecerli:
        raise SembolHatasi(
            f"{etiket} icindeki hicbir sembol borsada bulunamadi: {sembol_listesi}"
        )

    if eksik:
        print(f"  {etiket}: {len(gecerli)}/{len(sembol_listesi)} sembol gecerli.")

    return gecerli, eksik


def gecerli_semboller():
    """config.SYMBOLS'un dogrulanmis hali."""
    from config import SYMBOLS
    gecerli, _ = dogrula(SYMBOLS)
    return gecerli


if __name__ == "__main__":
    from config import SYMBOLS, DEFLATOR_SYMBOL
    print("=== SEMBOL DOGRULAMA ===")
    gecerli, eksik = dogrula(SYMBOLS)
    print(f"Gecerli: {gecerli}")
    print(f"Eksik  : {eksik}")
    print(f"Deflator '{DEFLATOR_SYMBOL}' borsada mi: {DEFLATOR_SYMBOL in borsa_sembolleri()}")
