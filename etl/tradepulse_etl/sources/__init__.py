"""
sources — the trade-data source seam (base) + its impls (fixture, comtrade, census).
@context  Import point so callers do `from tradepulse_etl.sources import FixtureSource`.
@affects  Used by pipeline.get_source().
"""
from .base import TradeSource
from .census import USCensusSource
from .comtrade import ComtradeSource
from .eurostat import EurostatSource
from .fixture import FixtureSource
from .ukhmrc import UKHmrcSource

__all__ = ["TradeSource", "FixtureSource", "ComtradeSource", "USCensusSource",
           "EurostatSource", "UKHmrcSource"]
