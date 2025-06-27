"""
Technical Analysis Calculations Module
Contains functions for TTM Squeeze, Volume Spike, and other technical indicators
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def calculate_atr(data: List[dict], period: int = 14) -> Optional[float]:
    """
    Calculate Average True Range (ATR) for a stock
    
    Args:
        data: List of OHLCV data dictionaries
        period: Period for ATR calculation (default 14)
        
    Returns:
        Latest ATR value or None if insufficient data
    """
    try:
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        
        # Calculate True Range
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        
        # Calculate ATR (exponential moving average of TR)
        df['atr'] = df['tr'].ewm(span=period).mean()
        
        # Return latest ATR value
        latest_atr = df.iloc[-1]['atr']
        return float(latest_atr) if not pd.isna(latest_atr) else None
        
    except Exception as e:
        logger.error(f"Error calculating ATR: {str(e)}")
        return None

def calculate_ttm_squeeze(symbol: str, data: List[dict]) -> Optional[Dict]:
    """
    Calculate TTM Squeeze for a single stock
    
    Args:
        symbol: Stock symbol
        data: List of OHLCV data dictionaries
        
    Returns:
        Dictionary with TTM Squeeze results or None if not in squeeze
    """
    try:
        # Convert data to pandas DataFrame for easier analysis
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['volume'] = df['volume'].astype(int)
        
        # Calculate Bollinger Bands (20-period, 2 standard deviations)
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Calculate Keltner Channels (20-period ATR, 1.5 multiplier)
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift())
        df['tr3'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].ewm(span=20).mean()
        
        df['kc_middle'] = df['close'].ewm(span=20).mean()
        df['kc_upper'] = df['kc_middle'] + (df['atr'] * 1.5)
        df['kc_lower'] = df['kc_middle'] - (df['atr'] * 1.5)
        
        # Calculate momentum (12-period to match Pine Script default)
        df['momentum'] = df['close'] - df['close'].shift(12)
        
        # Check for squeeze (BB inside KC)
        df['squeeze'] = (df['bb_upper'] <= df['kc_upper']) & (df['bb_lower'] >= df['kc_lower'])
        
        # Count consecutive squeeze days
        squeeze_days = 0
        for i in range(len(df) - 1, -1, -1):
            if df.iloc[i]['squeeze']:
                squeeze_days += 1
            else:
                break
        
        # Only return if in squeeze (at least 5 days)
        if squeeze_days >= 5:
            latest = df.iloc[-1]
            
            # Calculate ATR for volatility context
            atr = calculate_atr(data, period=14)
            atr_ratio = (atr / float(latest['close'])) * 100 if atr and float(latest['close']) > 0 else None
            
            # Determine squeeze intensity
            if squeeze_days >= 15:
                intensity = "high"
            elif squeeze_days >= 10:
                intensity = "medium"
            else:
                intensity = "low"
            
            return {
                "symbol": symbol,
                "squeeze_days": squeeze_days,
                "squeeze_intensity": intensity,
                "bollinger_bands": {
                    "upper": float(latest['bb_upper']),
                    "lower": float(latest['bb_lower']),
                    "middle": float(latest['bb_middle'])
                },
                "keltner_channels": {
                    "upper": float(latest['kc_upper']),
                    "lower": float(latest['kc_lower']),
                    "middle": float(latest['kc_middle'])
                },
                "momentum": float(latest['momentum']),
                "latest_close": float(latest['close']),
                "latest_volume": int(latest['volume']),
                "latest_date": latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date']),
                "data_points": len(df),
                "atr": atr,
                "atr_ratio": atr_ratio  # ATR as percentage of close price
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error calculating TTM Squeeze for {symbol}: {str(e)}")
        return None

def calculate_volume_spike(symbol: str, data: List[dict]) -> Optional[Dict]:
    """
    Calculate Volume Spike analysis for a single stock
    
    Args:
        symbol: Stock symbol
        data: List of OHLCV data dictionaries
        
    Returns:
        Dictionary with Volume Spike results or None if no significant spike
    """
    try:
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(int)
        
        # Calculate 30-day average volume
        df['avg_volume_30d'] = df['volume'].rolling(window=30).mean()
        
        # Calculate volume ratio (current volume / 30-day average)
        df['volume_ratio'] = df['volume'] / df['avg_volume_30d']
        
        # Check for volume spike (volume > 3x average)
        latest = df.iloc[-1]
        volume_ratio = latest['volume_ratio']
        
        if volume_ratio >= 3.0:
            # Count consecutive days with high volume
            consecutive_days = 0
            for i in range(len(df) - 1, -1, -1):
                if df.iloc[i]['volume_ratio'] >= 2.0:  # Lower threshold for consecutive days
                    consecutive_days += 1
                else:
                    break
            
            # Determine spike intensity
            if volume_ratio >= 10.0:
                intensity = "extreme"
            elif volume_ratio >= 5.0:
                intensity = "high"
            else:
                intensity = "moderate"
            
            return {
                "symbol": symbol,
                "volume_ratio": float(volume_ratio),
                "spike_intensity": intensity,
                "consecutive_days": consecutive_days,
                "avg_volume_30d": int(latest['avg_volume_30d']),
                "latest_volume": int(latest['volume']),
                "latest_close": float(latest['close']),
                "latest_date": latest['date'].strftime('%Y-%m-%d') if hasattr(latest['date'], 'strftime') else str(latest['date']),
                "data_points": len(df)
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error calculating Volume Spike for {symbol}: {str(e)}")
        return None

def analyze_stock_technicals(symbol: str, data: List[dict]) -> Dict:
    """
    Perform comprehensive technical analysis on a stock
    
    Args:
        symbol: Stock symbol
        data: List of OHLCV data dictionaries
        
    Returns:
        Dictionary with all technical analysis results
    """
    results = {
        "symbol": symbol,
        "ttm_squeeze": None,
        "volume_spike": None,
        "latest_date": None,
        "latest_close": None,
        "latest_volume": None,
        "data_points": len(data)
    }
    
    try:
        # Get latest data
        df = pd.DataFrame(data)
        latest = df.iloc[-1]
        results["latest_date"] = latest['date']
        results["latest_close"] = float(latest['close'])
        results["latest_volume"] = int(latest['volume'])
        
        # Calculate TTM Squeeze
        results["ttm_squeeze"] = calculate_ttm_squeeze(symbol, data)
        
        # Calculate Volume Spike
        results["volume_spike"] = calculate_volume_spike(symbol, data)
        
        return results
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis for {symbol}: {str(e)}")
        return results

def calculate_emas_and_check_stacking(data: List[dict]) -> Optional[Dict]:
    """
    Calculate EMAs and check if they are properly stacked (9EMA > 50EMA > 200EMA)
    and trending upward (positive slopes)
    
    Args:
        data: List of OHLCV data dictionaries
        
    Returns:
        Dictionary with EMA values and stacking status, or None if not properly stacked
    """
    try:
        # Convert data to pandas DataFrame
        df = pd.DataFrame(data)
        df['close'] = df['close'].astype(float)
        
        # Calculate EMAs
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # Calculate slopes (change over last 5 periods)
        df['ema_9_slope'] = df['ema_9'].diff(5)
        df['ema_50_slope'] = df['ema_50'].diff(5)
        
        # Get latest values
        latest = df.iloc[-1]
        ema_9 = latest['ema_9']
        ema_50 = latest['ema_50']
        ema_200 = latest['ema_200']
        ema_9_slope = latest['ema_9_slope']
        ema_50_slope = latest['ema_50_slope']
        
        # Check if EMAs are properly stacked (9EMA > 50EMA > 200EMA)
        # AND both 9EMA and 50EMA have positive slopes
        if (ema_9 > ema_50 > ema_200 and 
            ema_9_slope > 0 and 
            ema_50_slope > 0):
            
            # Determine stacking strength
            stacking_strength = "strong" if (ema_9 - ema_200) / ema_200 > 0.05 else "moderate"
            
            # Determine slope strength
            slope_strength = "strong" if (ema_9_slope > ema_50_slope * 2) else "moderate"
            
            return {
                "ema_9": float(ema_9),
                "ema_50": float(ema_50),
                "ema_200": float(ema_200),
                "ema_9_slope": float(ema_9_slope),
                "ema_50_slope": float(ema_50_slope),
                "stacked": True,
                "stacking_strength": stacking_strength,
                "slope_strength": slope_strength,
                "trending_up": True
            }
        else:
            # Log why it failed
            reasons = []
            if not (ema_9 > ema_50 > ema_200):
                reasons.append("EMAs not stacked")
            if ema_9_slope <= 0:
                reasons.append("9EMA slope <= 0")
            if ema_50_slope <= 0:
                reasons.append("50EMA slope <= 0")
            
            return {
                "ema_9": float(ema_9),
                "ema_50": float(ema_50),
                "ema_200": float(ema_200),
                "ema_9_slope": float(ema_9_slope),
                "ema_50_slope": float(ema_50_slope),
                "stacked": False,
                "stacking_strength": "none",
                "slope_strength": "none",
                "trending_up": False,
                "failure_reasons": reasons
            }
        
    except Exception as e:
        logger.error(f"Error calculating EMAs: {str(e)}")
        return None

def calculate_ttm_squeeze_with_ema_filter(symbol: str, data: List[dict]) -> Optional[Dict]:
    """
    Calculate TTM Squeeze with EMA stacking filter
    
    Args:
        symbol: Stock symbol
        data: List of OHLCV data dictionaries
        
    Returns:
        Dictionary with TTM Squeeze results or None if not in squeeze or EMAs not stacked
    """
    try:
        # First check EMA stacking
        ema_result = calculate_emas_and_check_stacking(data)
        if not ema_result or not ema_result['stacked']:
            return None
        
        # If EMAs are stacked, proceed with TTM Squeeze calculation
        squeeze_result = calculate_ttm_squeeze(symbol, data)
        
        if squeeze_result:
            # Add EMA information to the result
            squeeze_result["ema_9"] = ema_result["ema_9"]
            squeeze_result["ema_50"] = ema_result["ema_50"]
            squeeze_result["ema_200"] = ema_result["ema_200"]
            squeeze_result["ema_9_slope"] = ema_result["ema_9_slope"]
            squeeze_result["ema_50_slope"] = ema_result["ema_50_slope"]
            squeeze_result["ema_stacking_strength"] = ema_result["stacking_strength"]
            squeeze_result["ema_slope_strength"] = ema_result["slope_strength"]
            squeeze_result["ema_trending_up"] = ema_result["trending_up"]
        
        return squeeze_result
        
    except Exception as e:
        logger.error(f"Error in TTM Squeeze with EMA filter for {symbol}: {str(e)}")
        return None 