from abc import ABC, abstractmethod
import pandas as pd


class Rule(ABC):
    def __init__(self, name, description, direction="long"):
        self.name = name
        self.description = description
        self.direction = direction

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        pass

    @abstractmethod
    def get_required_lookback(self) -> int:
        pass


class MOM_1W(Rule):
    def __init__(self, threshold_pct=5):
        super().__init__(
            name=f"MOM_1W_{threshold_pct}",
            description=f"Son 7 gun getirisi > %{threshold_pct}",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 7 * 24

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_7d_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_7d_ago <= 0:
            return False

        ret = (current_price - price_7d_ago) / price_7d_ago * 100
        return ret > self.threshold_pct


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


class BIST_MOM_1W(Rule):
    def __init__(self, threshold_pct=5):
        super().__init__(
            name=f"BIST_MOM_1W_{threshold_pct}",
            description=f"BIST Son 5 gun getirisi > %{threshold_pct}",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 5 * 8

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_5d_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_5d_ago <= 0:
            return False

        ret = (current_price - price_5d_ago) / price_5d_ago * 100
        return ret > self.threshold_pct


class BIST_REV_1D(Rule):
    def __init__(self, threshold_pct=-8):
        super().__init__(
            name=f"BIST_REV_1D_{abs(threshold_pct)}",
            description=f"BIST Son 1 gunde %{threshold_pct} dusus",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 8

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_1d_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_1d_ago <= 0:
            return False

        ret = (current_price - price_1d_ago) / price_1d_ago * 100
        return ret < self.threshold_pct


class BIST_MOM_1M(Rule):
    def __init__(self, threshold_pct=10):
        super().__init__(
            name=f"BIST_MOM_1M_{threshold_pct}",
            description=f"BIST Son 20 gun getirisi > %{threshold_pct}",
            direction="long"
        )
        self.threshold_pct = threshold_pct

    def get_required_lookback(self):
        return 20 * 8

    def evaluate(self, df: pd.DataFrame, current_idx: int) -> bool:
        if current_idx < self.get_required_lookback():
            return False

        current_price = df.iloc[current_idx]['close']
        price_20d_ago = df.iloc[current_idx - self.get_required_lookback()]['close']

        if price_20d_ago <= 0:
            return False

        ret = (current_price - price_20d_ago) / price_20d_ago * 100
        return ret > self.threshold_pct


def get_all_rules():
    rules = []
    for threshold in [5, 10, 15]:
        rules.append(MOM_1W(threshold))
    for threshold in [-5, -8, -12]:
        rules.append(REV_1D(threshold))
    return rules


def get_bist_rules():
    rules = []
    for threshold in [3, 5, 8]:
        rules.append(BIST_MOM_1W(threshold))
    for threshold in [-3, -5, -8]:
        rules.append(BIST_REV_1D(threshold))
    for threshold in [10, 15, 20]:
        rules.append(BIST_MOM_1M(threshold))
    return rules


def get_rules_for_thresholds(mom_thresholds=None, rev_thresholds=None):
    rules = []
    if mom_thresholds is None:
        mom_thresholds = [5, 10, 15]
    if rev_thresholds is None:
        rev_thresholds = [-5, -8, -12]

    for t in mom_thresholds:
        rules.append(MOM_1W(t))
    for t in rev_thresholds:
        rules.append(REV_1D(t))
    return rules
