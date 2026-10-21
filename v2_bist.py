import borsapy as bp
from datetime import datetime


class BISTApi:
    def __init__(self):
        pass

    def get_hisse(self, symbol):
        try:
            hisse = bp.Ticker(symbol)
            return hisse.info
        except Exception as e:
            print(f"Hisse hatasi ({symbol}): {e}")
            return None

    def get_bist100(self):
        try:
            endeks = bp.Ticker("XU100")
            return endeks.info
        except Exception as e:
            print(f"BIST100 hatasi: {e}")
            return None

    def get_coklu_hisse(self, symbols):
        try:
            hisseler = bp.Tickers(symbols)
            results = {}
            for symbol in symbols:
                try:
                    results[symbol] = hisseler.tickers[symbol].info
                except:
                    results[symbol] = None
            return results
        except Exception as e:
            print(f"Coklu hisse hatasi: {e}")
            return None

    def get_gecmis(self, symbol, period="1ay"):
        try:
            df = bp.download(symbol, period=period)
            return df
        except Exception as e:
            print(f"Gecmis veri hatasi ({symbol}): {e}")
            return None

    def get_viop(self, symbol):
        try:
            contracts = bp.viop_contracts(symbol)
            return contracts
        except Exception as e:
            print(f"VIOP hatasi ({symbol}): {e}")
            return None


bist = BISTApi()


def test_bist():
    print("=== BIST TEST ===\n")

    print("1. BIST100 Endeksi:")
    bist100 = bist.get_bist100()
    if bist100:
        print(f"  Son: {bist100.get('last', 'N/A')}")
        print(f"  Degisim: {bist100.get('dailyPercent', 'N/A')}%")
    print()

    print("2. THYAO Hisse Bilgisi:")
    thyao = bist.get_hisse("THYAO")
    if thyao:
        print(f"  Son: {thyao.get('last', 'N/A')} TL")
        print(f"  Hacim: {thyao.get('volume', 'N/A')}")
    print()

    print("3. Coklu Hisse (AKBNK, GARAN, THYAO):")
    coklu = bist.get_coklu_hisse(["AKBNK", "GARAN", "THYAO"])
    if coklu:
        for symbol, data in coklu.items():
            if data:
                print(f"  {symbol}: {data.get('last', 'N/A')} TL")
    print()

    print("4. THYAO Gecmis Verisi (1 Ay):")
    gecmis = bist.get_gecmis("THYAO", "1ay")
    if gecmis is not None and not gecmis.empty:
        print(f"  Satir sayisi: {len(gecmis)}")
        print(f"  Son kapanis: {gecmis['Close'].iloc[-1]:.2f}")


if __name__ == "__main__":
    test_bist()
