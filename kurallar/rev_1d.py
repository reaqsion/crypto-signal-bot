from kurallar.motor import Rule
import pandas as pd


class REV_1D(Rule):
    def __init__(self, threshold_pct=-8):
        super().__init__(
            name=f"REV_1D_{abs(threshold_pct)}",
            description=f"Son 24 saatte %{threshold_pct} dusus",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 24

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_24h_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_24h_ago <= 0:
            return False

        ret = (current_price - price_24h_ago) / price_24h_ago * 100
        return ret < self.threshold_pct
