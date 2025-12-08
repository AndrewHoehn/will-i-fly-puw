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
    # KPUW Runway Configuration
    # Runway 05/23: Heading 050° / 230°
    RUNWAY_HEADINGS = [50, 230]  # Degrees

    def __init__(self):
        # Estimated cancellation rates (%) by month for KPUW
        # Estimated cancellation rates (%) by month for KPUW (Based on BTS Data 2020-2025)
        self.seasonal_baselines = {
            1: 4.1, 2: 4.8, 3: 0.5, 4: 1.6, 5: 0.7, 6: 0.9,
            7: 0.4, 8: 0.9, 9: 0.6, 10: 0.1, 11: 1.7, 12: 5.9
        }
        self.history_db = HistoryDatabase()

    def get_seasonal_baseline(self, date_obj):
        return self.seasonal_baselines.get(date_obj.month, 5)

    def calculate_crosswind(self, wind_speed, wind_direction):
        """
        Calculates the crosswind component for KPUW's runway 05/23.
        Returns the minimum crosswind component (uses the most favorable runway).

        Args:
            wind_speed: Wind speed in knots
            wind_direction: Wind direction in degrees (0-360)

        Returns:
            Crosswind component in knots
        """
        if wind_speed is None or wind_direction is None:
            return None

        # Calculate crosswind for both runway headings, use the minimum
        crosswinds = []
        for runway_heading in self.RUNWAY_HEADINGS:
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

        # Determine Level
        if score >= 70:
            level = "High"
        elif score >= 40:
            level = "Medium"
        else:
            level = "Low"

        return RiskScore(score, factors, level, breakdown, detailed_factors)
