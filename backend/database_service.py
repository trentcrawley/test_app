from sqlalchemy.orm import Session
from database import ScanResult, HistoricalData, ScanSession, SessionLocal
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    
    @staticmethod
    def clear_old_results(country: str, scan_type: str = None):
        """Clear old scan results for a country before adding new ones"""
        db = SessionLocal()
        try:
            query = db.query(ScanResult).filter(ScanResult.country == country)
            if scan_type:
                query = query.filter(ScanResult.scan_type == scan_type)
            query.delete()
            db.commit()
            logger.info(f"Cleared old {scan_type or 'all'} results for {country}")
        except Exception as e:
            logger.error(f"Error clearing old results: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def save_scan_results(country: str, results: Dict[str, List[Dict]], scan_type: str = "scheduled"):
        """Save scan results to database"""
        db = SessionLocal()
        try:
            # Create scan session
            session = ScanSession(
                country=country,
                scan_type=scan_type,
                start_time=datetime.utcnow(),
                status="running"
            )
            db.add(session)
            db.commit()
            
            # Clear old results for this country
            DatabaseService.clear_old_results(country)
            
            total_results = 0
            
            # Save TTM Squeeze results
            if "ttm_squeeze" in results:
                for stock in results["ttm_squeeze"]:
                    scan_result = ScanResult(
                        symbol=stock["symbol"],
                        company_name=stock["company_name"],
                        exchange=stock["exchange"],
                        country=country,
                        scan_type="ttm_squeeze",
                        price=stock["price"],
                        change=stock["change"],
                        change_percent=stock["change_percent"],
                        volume=stock["volume"],
                        market_cap=stock["market_cap"],
                        pe_ratio=stock["pe_ratio"],
                        squeeze_days=stock["squeeze_days"],
                        bollinger_upper=stock["bollinger_bands"]["upper"],
                        bollinger_lower=stock["bollinger_bands"]["lower"],
                        bollinger_middle=stock["bollinger_bands"]["middle"],
                        keltner_upper=stock["keltner_channels"]["upper"],
                        keltner_lower=stock["keltner_channels"]["lower"],
                        keltner_middle=stock["keltner_channels"]["middle"],
                        momentum=stock["momentum"],
                        squeeze_intensity=stock["squeeze_intensity"]
                    )
                    db.add(scan_result)
                    total_results += 1
            
            # Save Volume Spike results
            if "volume_spikes" in results:
                for stock in results["volume_spikes"]:
                    scan_result = ScanResult(
                        symbol=stock["symbol"],
                        company_name=stock["company_name"],
                        exchange=stock["exchange"],
                        country=country,
                        scan_type="volume_spike",
                        price=stock["price"],
                        change=stock["change"],
                        change_percent=stock["change_percent"],
                        volume=stock["volume"],
                        market_cap=stock["market_cap"],
                        pe_ratio=stock["pe_ratio"],
                        spike_days=stock["spike_days"],
                        volume_ratio=stock["volume_ratio"],
                        avg_volume_30d=stock["avg_volume_30d"],
                        consecutive_days=stock["consecutive_days"],
                        spike_intensity=stock["spike_intensity"]
                    )
                    db.add(scan_result)
                    total_results += 1
            
            # Update session
            session.end_time = datetime.utcnow()
            session.status = "completed"
            session.results_count = total_results
            
            db.commit()
            logger.info(f"Saved {total_results} scan results for {country}")
            
        except Exception as e:
            logger.error(f"Error saving scan results: {e}")
            db.rollback()
            # Update session with error
            if 'session' in locals():
                session.end_time = datetime.utcnow()
                session.status = "failed"
                session.error_message = str(e)
                db.commit()
        finally:
            db.close()
    
    @staticmethod
    def get_latest_results(country: str) -> Dict[str, Any]:
        """Get latest scan results for a country"""
        db = SessionLocal()
        try:
            # Get latest scan session
            latest_session = db.query(ScanSession).filter(
                ScanSession.country == country,
                ScanSession.status == "completed"
            ).order_by(ScanSession.end_time.desc()).first()
            
            if not latest_session:
                return {
                    "ttm_squeeze": [],
                    "volume_spikes": [],
                    "last_updated": None,
                    "scan_info": None
                }
            
            # Get TTM Squeeze results
            ttm_results = db.query(ScanResult).filter(
                ScanResult.country == country,
                ScanResult.scan_type == "ttm_squeeze"
            ).all()
            
            # Get Volume Spike results
            volume_results = db.query(ScanResult).filter(
                ScanResult.country == country,
                ScanResult.scan_type == "volume_spike"
            ).all()
            
            # Convert to dict format
            ttm_data = []
            for result in ttm_results:
                ttm_data.append({
                    "symbol": result.symbol,
                    "company_name": result.company_name,
                    "exchange": result.exchange,
                    "price": result.price,
                    "change": result.change,
                    "change_percent": result.change_percent,
                    "volume": result.volume,
                    "market_cap": result.market_cap,
                    "pe_ratio": result.pe_ratio,
                    "squeeze_days": result.squeeze_days,
                    "bollinger_bands": {
                        "upper": result.bollinger_upper,
                        "lower": result.bollinger_lower,
                        "middle": result.bollinger_middle
                    },
                    "keltner_channels": {
                        "upper": result.keltner_upper,
                        "lower": result.keltner_lower,
                        "middle": result.keltner_middle
                    },
                    "momentum": result.momentum,
                    "squeeze_intensity": result.squeeze_intensity
                })
            
            volume_data = []
            for result in volume_results:
                volume_data.append({
                    "symbol": result.symbol,
                    "company_name": result.company_name,
                    "exchange": result.exchange,
                    "price": result.price,
                    "change": result.change,
                    "change_percent": result.change_percent,
                    "volume": result.volume,
                    "market_cap": result.market_cap,
                    "pe_ratio": result.pe_ratio,
                    "spike_days": result.spike_days,
                    "volume_ratio": result.volume_ratio,
                    "avg_volume_30d": result.avg_volume_30d,
                    "consecutive_days": result.consecutive_days,
                    "spike_intensity": result.spike_intensity
                })
            
            return {
                "ttm_squeeze": ttm_data,
                "volume_spikes": volume_data,
                "last_updated": latest_session.end_time.isoformat(),
                "scan_info": {
                    "scan_type": latest_session.scan_type,
                    "results_count": latest_session.results_count,
                    "start_time": latest_session.start_time.isoformat(),
                    "end_time": latest_session.end_time.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting latest results: {e}")
            return {
                "ttm_squeeze": [],
                "volume_spikes": [],
                "last_updated": None,
                "scan_info": None
            }
        finally:
            db.close()
    
    @staticmethod
    def save_historical_data(symbol: str, country: str, data: List[Dict]):
        """Save historical candlestick data"""
        db = SessionLocal()
        try:
            # Clear old historical data for this symbol
            db.query(HistoricalData).filter(
                HistoricalData.symbol == symbol,
                HistoricalData.country == country
            ).delete()
            
            # Save new historical data
            for candle in data:
                historical_data = HistoricalData(
                    symbol=symbol,
                    date=datetime.fromtimestamp(candle["date"]),
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"],
                    country=country
                )
                db.add(historical_data)
            
            db.commit()
            logger.info(f"Saved {len(data)} historical records for {symbol}")
            
        except Exception as e:
            logger.error(f"Error saving historical data: {e}")
            db.rollback()
        finally:
            db.close()
    
    @staticmethod
    def get_historical_data(symbol: str, country: str, days: int = 30) -> List[Dict]:
        """Get historical data for a symbol"""
        db = SessionLocal()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            historical_data = db.query(HistoricalData).filter(
                HistoricalData.symbol == symbol,
                HistoricalData.country == country,
                HistoricalData.date >= cutoff_date
            ).order_by(HistoricalData.date.asc()).all()
            
            return [
                {
                    "date": int(data.date.timestamp()),
                    "open": data.open,
                    "high": data.high,
                    "low": data.low,
                    "close": data.close,
                    "volume": data.volume
                }
                for data in historical_data
            ]
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
        finally:
            db.close() 