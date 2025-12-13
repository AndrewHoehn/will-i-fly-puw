from datetime import datetime
from .history_db import HistoryDatabase
import math

class RiskScore:
    def __init__(self, score, factors, risk_level, breakdown, detailed_factors):
        self.score = score # 0-100
        self.factors = factors # List of strings
        self.risk_level = risk_level # Low, Medium, High
        self.breakdown = breakdown # Dict of component scores
        self.detailed_factors = detailed_factors # List of structured factor dicts

    def to_dict(self):
        return {
            "score": self.score,
            "factors": self.factors,
            "risk_level": self.risk_level,
            "breakdown": self.breakdown,
            "detailed_factors": self.detailed_factors
        }

class PredictionEngine:
    # Multi-Airport Runway Configurations
    RUNWAY_HEADINGS = {
        "KPUW": [50, 230],           # Runway 05/23
        "KSEA": [160, 340, 170, 350],  # Runways 16L/34R, 16C/34C, 16R/34L
        "KBOI": [100, 280, 120, 300]   # Runways 10L/28R, 10R/28L
    }

    # Legacy single-airport support
    LEGACY_RUNWAY_HEADINGS = [50, 230]  # KPUW

    def __init__(self):
        # Estimated cancellation rates (%) by month for KPUW
        # Estimated cancellation rates (%) by month for KPUW (Based on BTS Data 2020-2025)
        self.seasonal_baselines = {
            1: 4.1, 2: 4.8, 3: 0.5, 4: 1.6, 5: 0.7, 6: 0.9,
            7: 0.4, 8: 0.9, 9: 0.6, 10: 0.1, 11: 1.7, 12: 5.9
        }
        self.history_db = HistoryDatabase()

        # Dynamic calibration: Automatically computed from actual performance
        # Falls back to conservative default if insufficient data
        self.calibration_factor = self._compute_calibration_factor()

    def get_seasonal_baseline(self, date_obj):
        return self.seasonal_baselines.get(date_obj.month, 5)

    def _compute_calibration_factor(self):
        """
        Dynamically compute calibration factor from historical performance.

        This method analyzes past predictions vs actual outcomes to determine
        how much we should adjust current predictions. The system automatically
        adapts as more data becomes available.

        Returns:
            float: Calibration factor (0.0-1.0), or default conservative value
        """
        try:
            conn = self.history_db._get_conn()
            cursor = conn.cursor()

            # Get predictions with known outcomes
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(hl.predicted_risk) as avg_predicted,
                    SUM(CASE WHEN hf.is_cancelled = 1 THEN 1 ELSE 0 END) as actual_cancelled
                FROM history_log hl
                JOIN historical_flights hf
                    ON hl.number = hf.flight_number
                    AND substr(hl.scheduled_time, 1, 10) = hf.flight_date
                WHERE hl.predicted_risk IS NOT NULL
            """)

            row = cursor.fetchone()
            conn.close()

            if not row or row[0] is None:
                # No data available - use conservative default
                return 0.5

            total, avg_predicted, actual_cancelled = row

            # Need at least 30 predictions for reliable calibration
            if total < 30:
                return 0.5  # Conservative default

            # Calculate actual cancellation rate
            actual_rate = (actual_cancelled / total) * 100 if total > 0 else 0

            # If we have no actual cancellations, be very conservative
            if actual_cancelled == 0:
                # We're over-predicting, but don't know by how much
                # Scale down significantly but not too aggressively
                return 0.3

            # Calculate ideal calibration factor
            # If avg_predicted = 12% and actual_rate = 1%, factor = 1/12 ≈ 0.083
            if avg_predicted > 0:
                ideal_factor = actual_rate / avg_predicted
            else:
                return 0.5

            # Apply bounds to prevent extreme adjustments
            # Minimum: 0.1 (don't scale down more than 90%)
            # Maximum: 2.0 (don't scale up more than 2x)
            calibration_factor = max(0.1, min(2.0, ideal_factor))

            # Add safety margin: Never go below actual rate
            # If we're currently over-predicting, be conservative
            if calibration_factor < 0.5:
                # Gradually approach the ideal, don't jump there immediately
                # This prevents overcorrection from limited data
                calibration_factor = 0.5 + (calibration_factor - 0.5) * 0.5

            return calibration_factor

        except Exception as e:
            # If anything goes wrong, fall back to conservative default
            import logging
            logging.warning(f"Error computing calibration factor: {e}")
            return 0.5

    def apply_calibration(self, raw_score):
        """
        Apply learned calibration to raw prediction score.

        Based on historical performance analysis, we adjust predictions
        to better match actual cancellation rates while remaining conservative.

        Args:
            raw_score: Uncalibrated risk score (0-100)

        Returns:
            Calibrated risk score (0-100)
        """
        # Apply calibration factor
        calibrated = raw_score * self.calibration_factor

        # Ensure we stay in valid range
        return max(0, min(100, calibrated))

    def calculate_crosswind(self, wind_speed, wind_direction, airport_code="KPUW"):
        """
        Calculates the crosswind component for a given airport's runways.
        Returns the minimum crosswind component (uses the most favorable runway).

        Args:
            wind_speed: Wind speed in knots
            wind_direction: Wind direction in degrees (0-360)
            airport_code: ICAO code (KPUW, KSEA, KBOI)

        Returns:
            Crosswind component in knots
        """
        if wind_speed is None or wind_direction is None:
            return None

        # Get runway headings for this airport
        runway_headings = self.RUNWAY_HEADINGS.get(airport_code, self.LEGACY_RUNWAY_HEADINGS)

        # Calculate crosswind for all runway headings, use the minimum
        crosswinds = []
        for runway_heading in runway_headings:
            # Angle between wind and runway
            angle_diff = abs(wind_direction - runway_heading)

            # Normalize to 0-180 range
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # Crosswind component = wind_speed * sin(angle)
            crosswind = abs(wind_speed * math.sin(math.radians(angle_diff)))
            crosswinds.append(crosswind)

        # Return the minimum crosswind (best case runway choice)
        return min(crosswinds)

    def calculate_risk(self, flight, weather):
        """
        Calculates flight cancellation risk based on weather and season.
        Returns a RiskScore object.
        """
        score = 0
        factors = []
        detailed_factors = []
        breakdown = {
            "seasonal_baseline": 0,
            "weather_score": 0,
            "history_adjustment": 0,
            "final_score": 0
        }

        # 1. Seasonal Baseline
        # We use the scheduled time of the flight
        dt = flight.get('scheduled_time')
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                dt = None
        
        if dt:
            baseline = self.get_seasonal_baseline(dt)
            score += baseline
            breakdown["seasonal_baseline"] = baseline
            if baseline > 10:
                desc = f"Seasonal Baseline: {baseline}% (High for {dt.strftime('%b')})"
                factors.append(desc)
                detailed_factors.append({
                    "category": "Seasonal",
                    "description": desc,
                    "details": {"month": dt.strftime('%B'), "baseline": baseline}
                })
        
        # 2. Weather Heuristics
        weather_score = 0
        if weather:
            # Visibility
            vis = weather.get('visibility_miles')
            if vis is not None:
                if vis < 0.5:
                    weather_score += 60
                    desc = f"Critical Visibility ({vis}mi)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Visibility", "value": vis, "penalty": 60}})
                elif vis < 1.0:
                    weather_score += 40
                    desc = f"Low Visibility ({vis}mi)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Visibility", "value": vis, "penalty": 40}})
                elif vis < 3.0:
                    weather_score += 15
                    desc = f"Reduced Visibility ({vis}mi)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Visibility", "value": vis, "penalty": 15}})

            # Wind (using crosswind component)
            wind = weather.get('wind_speed_knots')
            wind_dir = weather.get('wind_direction')

            # Calculate crosswind component
            crosswind = self.calculate_crosswind(wind, wind_dir)

            if crosswind is not None:
                # Use crosswind component for more accurate risk assessment
                if crosswind > 25:
                    weather_score += 50
                    desc = f"Extreme Crosswind ({crosswind:.1f}kt, Wind {wind:.0f}kt @ {wind_dir:.0f}°)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Crosswind", "crosswind": round(crosswind, 1), "wind_speed": wind, "wind_direction": wind_dir, "penalty": 50}})
                elif crosswind > 15:
                    weather_score += 30
                    desc = f"High Crosswind ({crosswind:.1f}kt, Wind {wind:.0f}kt @ {wind_dir:.0f}°)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Crosswind", "crosswind": round(crosswind, 1), "wind_speed": wind, "wind_direction": wind_dir, "penalty": 30}})
                elif crosswind > 10:
                    weather_score += 10
                    desc = f"Moderate Crosswind ({crosswind:.1f}kt, Wind {wind:.0f}kt @ {wind_dir:.0f}°)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Crosswind", "crosswind": round(crosswind, 1), "wind_speed": wind, "wind_direction": wind_dir, "penalty": 10}})
            elif wind is not None:
                # Fallback to total wind if direction is unavailable
                if wind > 40:
                    weather_score += 50
                    desc = f"Extreme Wind ({wind}kt)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Wind", "value": wind, "penalty": 50}})
                elif wind > 30:
                    weather_score += 30
                    desc = f"High Wind ({wind}kt)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Wind", "value": wind, "penalty": 30}})
                elif wind > 20:
                    weather_score += 10
                    desc = f"Breezy ({wind}kt)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Wind", "value": wind, "penalty": 10}})

            # Temperature / Precip (Icing Risk)
            temp = weather.get('temperature_f')
            desc_text = weather.get('description', '').lower()
            if temp is not None and temp < 32:
                if 'snow' in desc_text or 'rain' in desc_text or 'drizzle' in desc_text or 'fog' in desc_text:
                    weather_score += 25
                    desc = "Icing Conditions (Freezing Precip/Fog)"
                    factors.append(desc)
                    detailed_factors.append({"category": "Weather", "description": desc, "details": {"type": "Icing", "temp": temp, "penalty": 25}})
        
        score += weather_score
        breakdown["weather_score"] = weather_score

        # 3. Historical Data Check
        # Check factors independently to maximize data availability
        
        # Visibility Check
        if vis is not None and vis < 3.0:
            total, cancelled = self.history_db.find_similar_flights(visibility=vis)
            if total >= 5:
                hist_prob = (cancelled / total) * 100
                desc = f"History: {int(hist_prob)}% cancelled when Vis < {vis+0.5:.1f}mi ({cancelled}/{total})"
                factors.append(desc)
                detailed_factors.append({
                    "category": "History",
                    "description": desc,
                    "details": {
                        "match_criteria": f"Visibility < {vis+0.5:.1f}mi",
                        "total_flights": total,
                        "cancelled_flights": cancelled,
                        "cancellation_rate": int(hist_prob)
                    }
                })
                
                # Blend: Average
                new_score = (score + hist_prob) / 2
                breakdown["history_adjustment"] = new_score - score
                score = new_score

        # Wind Check
        if wind is not None and wind > 20:
            total, cancelled = self.history_db.find_similar_flights(wind=wind)
            if total >= 5:
                hist_prob = (cancelled / total) * 100
                desc = f"History: {int(hist_prob)}% cancelled when Wind > {wind-5:.0f}kt ({cancelled}/{total})"
                factors.append(desc)
                detailed_factors.append({
                    "category": "History",
                    "description": desc,
                    "details": {
                        "match_criteria": f"Wind > {wind-5:.0f}kt",
                        "total_flights": total,
                        "cancelled_flights": cancelled,
                        "cancellation_rate": int(hist_prob)
                    }
                })
                
                # Blend: Max
                new_score = max(score, hist_prob)
                if new_score > score:
                    breakdown["history_adjustment"] += (new_score - score)
                score = new_score

        # Icing Check
        if temp is not None and temp < 32 and ('snow' in desc_text or 'rain' in desc_text or 'fog' in desc_text):
                total, cancelled = self.history_db.find_similar_flights(temp=temp)
                if total >= 5:
                    hist_prob = (cancelled / total) * 100
                    desc = f"History: {int(hist_prob)}% cancelled in freezing temps ({cancelled}/{total})"
                    factors.append(desc)
                    detailed_factors.append({
                        "category": "History",
                        "description": desc,
                        "details": {
                            "match_criteria": "Freezing Temps + Precip",
                            "total_flights": total,
                            "cancelled_flights": cancelled,
                            "cancellation_rate": int(hist_prob)
                        }
                    })
                    
                    # Blend: Max
                    new_score = max(score, hist_prob)
                    if new_score > score:
                        breakdown["history_adjustment"] += (new_score - score)
                    score = new_score

        # Cap score at 99% (nothing is certain)
        score = min(score, 99)
        score = max(score, 0)
        breakdown["final_score"] = score

        # Apply calibration (learned from historical performance)
        raw_score = score
        score = self.apply_calibration(score)
        breakdown["calibrated_score"] = score
        breakdown["calibration_adjustment"] = score - raw_score

        # Determine Level (using calibrated score)
        if score >= 70:
            level = "High"
        elif score >= 40:
            level = "Medium"
        else:
            level = "Low"

        return RiskScore(score, factors, level, breakdown, detailed_factors)

    # ===== MULTI-AIRPORT WEATHER METHODS =====

    def calculate_risk_multi_airport(self, flight, puw_weather, origin_weather, dest_weather):
        """
        Calculate flight cancellation risk using weather from all relevant airports.

        Args:
            flight: Flight dict with origin, destination, type, scheduled_time
            puw_weather: Weather dict for KPUW
            origin_weather: Weather dict for origin airport
            dest_weather: Weather dict for destination airport

        Returns:
            RiskScore object with multi-airport analysis
        """
        score = 0
        factors = []
        detailed_factors = []
        breakdown = {
            "seasonal_baseline": 0,
            "puw_weather_score": 0,
            "origin_weather_score": 0,
            "dest_weather_score": 0,
            "history_adjustment": 0,
            "final_score": 0
        }

        # 1. Seasonal Baseline
        dt = flight.get('scheduled_time')
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except ValueError:
                dt = None

        if dt:
            baseline = self.get_seasonal_baseline(dt)
            score += baseline
            breakdown["seasonal_baseline"] = baseline
            if baseline > 10:
                desc = f"Seasonal Baseline: {baseline}% (High for {dt.strftime('%b')})"
                factors.append(desc)
                detailed_factors.append({
                    "category": "Seasonal",
                    "description": desc,
                    "details": {"month": dt.strftime('%B'), "baseline": baseline}
                })

        # 2. PUW Weather Score
        puw_score = self._score_airport_weather(puw_weather, "KPUW", flight.get('type'))
        if puw_score > 0:
            score += puw_score
            breakdown["puw_weather_score"] = puw_score
            factors.append(f"PUW: {self._describe_weather(puw_weather)}")

        # 3. Origin Weather Score (critical for arrivals)
        if flight.get('type') == 'arrival' and origin_weather:
            origin_code = flight.get('origin', 'Unknown')
            origin_score = self._score_airport_weather(origin_weather, origin_code, 'departure')

            if origin_score > 20:
                # Weight origin weather heavily for arrivals (70%)
                weighted_score = origin_score * 0.7
                score += weighted_score
                breakdown["origin_weather_score"] = weighted_score
                factors.append(f"{origin_code}: {self._describe_weather(origin_weather)} +{int(weighted_score)}%")
                detailed_factors.append({
                    "category": "Origin Weather",
                    "description": f"{origin_code} weather affecting departure",
                    "details": {
                        "airport": origin_code,
                        "conditions": self._describe_weather(origin_weather),
                        "impact": f"+{int(weighted_score)}%"
                    }
                })

        # 4. Destination Weather Score (critical for departures)
        if flight.get('type') == 'departure' and dest_weather:
            dest_code = flight.get('destination', 'Unknown')
            dest_score = self._score_airport_weather(dest_weather, dest_code, 'arrival')

            if dest_score > 20:
                # Weight destination weather moderately for departures (60%)
                weighted_score = dest_score * 0.6
                score += weighted_score
                breakdown["dest_weather_score"] = weighted_score
                factors.append(f"{dest_code}: {self._describe_weather(dest_weather)} +{int(weighted_score)}%")
                detailed_factors.append({
                    "category": "Destination Weather",
                    "description": f"{dest_code} weather affecting arrival",
                    "details": {
                        "airport": dest_code,
                        "conditions": self._describe_weather(dest_weather),
                        "impact": f"+{int(weighted_score)}%"
                    }
                })

        # 5. Historical Matching (Separate PUW and Origin/Dest matching)
        # Match PUW weather independently
        puw_total, puw_cancelled = self.history_db.find_similar_flights(
            visibility=puw_weather.get('visibility_miles') if puw_weather else None,
            wind=puw_weather.get('wind_speed_knots') if puw_weather else None,
            temp=puw_weather.get('temperature_f') if puw_weather else None
        )

        # Match origin/destination weather independently
        other_total, other_cancelled = 0, 0
        if flight.get('type') == 'arrival' and origin_weather:
            other_total, other_cancelled = self.history_db.find_similar_flights_multi_airport(
                puw_weather=None,  # Don't match PUW again
                origin_weather=origin_weather,
                dest_weather=None,
                flight_type='arrival'
            )
        elif flight.get('type') == 'departure' and dest_weather:
            other_total, other_cancelled = self.history_db.find_similar_flights_multi_airport(
                puw_weather=None,  # Don't match PUW again
                origin_weather=None,
                dest_weather=dest_weather,
                flight_type='departure'
            )

        # Combine both historical signals
        historical_signals = []

        if puw_total >= 10:
            puw_hist_prob = (puw_cancelled / puw_total) * 100
            historical_signals.append(puw_hist_prob)
            desc = f"PUW History: {int(puw_hist_prob)}% cancelled in similar conditions ({puw_cancelled}/{puw_total})"
            factors.append(desc)
            detailed_factors.append({
                "category": "Historical - PUW",
                "description": desc,
                "details": {
                    "total_flights": puw_total,
                    "cancelled_flights": puw_cancelled,
                    "cancellation_rate": int(puw_hist_prob)
                }
            })

        if other_total >= 5:
            other_hist_prob = (other_cancelled / other_total) * 100
            historical_signals.append(other_hist_prob)
            airport_name = flight.get('origin') if flight.get('type') == 'arrival' else flight.get('destination')
            desc = f"{airport_name} History: {int(other_hist_prob)}% cancelled in similar conditions ({other_cancelled}/{other_total})"
            factors.append(desc)
            detailed_factors.append({
                "category": f"Historical - {airport_name}",
                "description": desc,
                "details": {
                    "total_flights": other_total,
                    "cancelled_flights": other_cancelled,
                    "cancellation_rate": int(other_hist_prob)
                }
            })

        # Blend with historical data if we have signals
        if historical_signals:
            avg_hist_prob = sum(historical_signals) / len(historical_signals)
            new_score = (score + avg_hist_prob) / 2
            breakdown["history_adjustment"] = new_score - score
            score = new_score

        # Cap score
        score = min(score, 99)
        score = max(score, 0)
        breakdown["final_score"] = score

        # Apply calibration (learned from historical performance)
        # This adjusts predictions based on actual cancellation rates
        raw_score = score
        score = self.apply_calibration(score)
        breakdown["calibrated_score"] = score
        breakdown["calibration_adjustment"] = score - raw_score

        # Determine Level (using calibrated score)
        if score >= 70:
            level = "High"
        elif score >= 40:
            level = "Medium"
        else:
            level = "Low"

        return RiskScore(score, factors, level, breakdown, detailed_factors)

    def _score_airport_weather(self, weather, airport_code, operation_type):
        """
        Score weather conditions at a specific airport using comprehensive weather data.

        Args:
            weather: Weather dict with comprehensive fields
            airport_code: ICAO code
            operation_type: 'arrival' or 'departure'

        Returns:
            Weather score (0-100)
        """
        if not weather:
            return 0

        score = 0
        vis = weather.get('visibility_miles')
        wind = weather.get('wind_speed_knots')
        wind_dir = weather.get('wind_direction')
        wind_gust = weather.get('wind_gust_knots')
        temp = weather.get('temperature_f')
        precip = weather.get('precipitation_in')
        snow_depth = weather.get('snow_depth_in')
        cloud_cover = weather.get('cloud_cover_pct')
        humidity = weather.get('humidity_pct')
        conditions = weather.get('conditions', '')

        # Visibility scoring
        if vis is not None:
            if vis < 0.5:
                score += 60
            elif vis < 1.0:
                score += 40
            elif vis < 3.0:
                score += 15

        # Wind gusts are more important than sustained winds for landing/takeoff safety
        effective_wind = wind_gust if wind_gust is not None else wind

        # Crosswind scoring (use gusts if available)
        crosswind = self.calculate_crosswind(effective_wind, wind_dir, airport_code)
        if crosswind is not None:
            if crosswind > 25:
                score += 50
            elif crosswind > 15:
                score += 30
            elif crosswind > 10:
                score += 10
        elif effective_wind is not None:
            # Fallback to total wind if no direction
            if effective_wind > 40:
                score += 50
            elif effective_wind > 30:
                score += 30
            elif effective_wind > 20:
                score += 10

        # Snow on runway - critical for operations
        if snow_depth is not None and snow_depth > 0:
            if snow_depth > 6:
                score += 40  # Major runway contamination
            elif snow_depth > 3:
                score += 25  # Moderate contamination
            elif snow_depth > 1:
                score += 15  # Light contamination

        # Active precipitation - adds to risk
        if precip is not None and precip > 0:
            if temp is not None and temp < 32:
                # Freezing precipitation (snow, ice)
                if precip > 0.3:
                    score += 30  # Heavy freezing precip
                elif precip > 0.1:
                    score += 20  # Moderate freezing precip
                else:
                    score += 10  # Light freezing precip
            else:
                # Rain (less severe but still impacts operations)
                if precip > 0.5:
                    score += 15  # Heavy rain
                elif precip > 0.1:
                    score += 8   # Moderate rain

        # Cloud cover / ceiling (VFR vs IFR)
        # Low clouds combined with poor visibility = IFR conditions
        if cloud_cover is not None and cloud_cover > 90 and vis is not None and vis < 5:
            score += 10  # IFR conditions

        # Icing risk (freezing temp + high humidity + precipitation)
        if temp is not None and temp < 32:
            if humidity is not None and humidity > 80 and precip is not None and precip > 0:
                score += 20  # High icing risk
            elif 'snow' in conditions.lower() or 'ice' in conditions.lower() or 'freezing' in conditions.lower():
                score += 15  # Icing conditions reported

        return score

    def _describe_weather(self, weather):
        """
        Generate human-readable weather description using comprehensive data.

        Args:
            weather: Weather dict with comprehensive fields

        Returns:
            String description
        """
        if not weather:
            return "No data"

        parts = []
        vis = weather.get('visibility_miles')
        wind = weather.get('wind_speed_knots')
        wind_gust = weather.get('wind_gust_knots')
        temp = weather.get('temperature_f')
        snow_depth = weather.get('snow_depth_in')
        precip = weather.get('precipitation_in')
        conditions = weather.get('conditions', '')

        # Visibility
        if vis is not None:
            if vis < 1.0:
                parts.append(f"Low visibility ({vis:.1f}mi)")
            elif vis < 3.0:
                parts.append(f"Reduced visibility ({vis:.1f}mi)")

        # Wind (prefer gusts if available)
        if wind_gust is not None and wind_gust > 20 and wind is not None:
            parts.append(f"Gusty winds ({wind:.0f}kt gusting {wind_gust:.0f}kt)")
        elif wind is not None and wind > 20:
            parts.append(f"High wind ({wind:.0f}kt)")

        # Snow depth
        if snow_depth is not None and snow_depth > 0:
            parts.append(f"{snow_depth:.1f}\" snow on ground")

        # Active precipitation
        if precip is not None and precip > 0.05:
            if temp is not None and temp < 32:
                parts.append(f"Freezing precip ({precip:.2f}\")")
            else:
                parts.append(f"Rain ({precip:.2f}\")")

        # Temperature (if freezing)
        if temp is not None and temp < 32:
            parts.append(f"Freezing ({temp:.0f}°F)")

        # Conditions text (if notable)
        if conditions and any(word in conditions.lower() for word in ['storm', 'thunder', 'heavy', 'ice', 'fog']):
            parts.append(conditions)

        if not parts:
            return "Good conditions"

        return ", ".join(parts)
