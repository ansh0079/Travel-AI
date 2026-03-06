"""
Analysis Engine for Autonomous Travel Research
Price prediction and sentiment analysis capabilities
"""
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import re
import logging

from app.utils.logging_config import get_logger

logger = get_logger(__name__)


class PricePredictor:
    """
    Predicts optimal booking times and price trends for flights and hotels.
    Uses historical price patterns and seasonal trends.
    """
    
    def __init__(self):
        # Seasonal price multipliers (baseline = 1.0)
        self.seasonal_multipliers = {
            'high_season': 1.4,    # Jun-Aug, Dec-Jan
            'shoulder_season': 1.15,  # Apr-May, Sep-Oct
            'low_season': 0.85,    # Nov (excluding holidays), Jan-Mar
        }
        
        # Booking window recommendations (days before departure)
        self.optimal_booking_windows = {
            'domestic': {'min': 21, 'max': 60, 'sweet_spot': 45},
            'international': {'min': 60, 'max': 180, 'sweet_spot': 90},
            'luxury': {'min': 90, 'max': 365, 'sweet_spot': 180},
        }
    
    async def predict_best_booking_time(
        self,
        destination: str,
        travel_dates: Dict[str, str],
        current_price: Optional[float] = None,
        price_history: Optional[List[Dict[str, Any]]] = None,
        trip_type: str = 'international'
    ) -> Dict[str, Any]:
        """
        Predict the best time to book flights/hotels.
        
        Args:
            destination: Destination name
            travel_dates: Dict with 'start' and 'end' dates
            current_price: Current observed price (optional)
            price_history: List of historical prices (optional)
            trip_type: 'domestic', 'international', or 'luxury'
        
        Returns:
            Dict with prediction, confidence, and recommendations
        """
        # Parse travel dates
        try:
            travel_start = datetime.strptime(travel_dates['start'], '%Y-%m-%d')
        except (KeyError, ValueError):
            travel_start = datetime.now() + timedelta(days=60)
        
        days_until_departure = (travel_start - datetime.now()).days
        
        # Determine season
        season = self._get_season_for_dates(travel_start)
        
        # Analyze price history if available
        if price_history and len(price_history) >= 3:
            trend_analysis = self._analyze_price_trend(price_history)
        else:
            trend_analysis = self._get_seasonal_trend(season, days_until_departure)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            days_until_departure=days_until_departure,
            season=season,
            trend=trend_analysis['trend'],
            trip_type=trip_type
        )
        
        # Calculate estimated savings
        estimated_savings = self._estimate_savings(
            current_price=current_price,
            trend=trend_analysis['trend'],
            days_until=days_until_departure
        )
        
        return {
            'destination': destination,
            'prediction': recommendation,
            'confidence': trend_analysis['confidence'],
            'current_trend': trend_analysis['trend'],
            'season': season,
            'days_until_departure': days_until_departure,
            'optimal_booking_window': self.optimal_booking_windows.get(trip_type, self.optimal_booking_windows['international']),
            'estimated_savings': estimated_savings,
            'historical_lowest': trend_analysis.get('historical_lowest'),
            'price_forecast': self._generate_price_forecast(days_until_departure, season),
            'generated_at': datetime.now().isoformat(),
        }
    
    def _get_season_for_dates(self, travel_date: datetime) -> str:
        """Determine travel season based on date."""
        month = travel_date.month
        
        # High season: Summer (Jun-Aug) and Winter holidays (Dec-Jan)
        if month in [6, 7, 8, 12, 1]:
            return 'high_season'
        # Shoulder season: Spring (Apr-May) and Fall (Sep-Oct)
        elif month in [4, 5, 9, 10]:
            return 'shoulder_season'
        # Low season: Late fall and early spring
        else:
            return 'low_season'
    
    def _analyze_price_trend(self, price_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze historical price data to identify trends."""
        prices = [entry['price'] for entry in price_history if 'price' in entry]
        dates = [entry['date'] for entry in price_history if 'date' in entry]
        
        if len(prices) < 3:
            return {
                'trend': 'stable',
                'confidence': 0.3,
                'historical_lowest': None,
            }
        
        # Calculate trend using linear regression
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Normalize slope to percentage change
        avg_price = np.mean(prices)
        slope_percentage = (slope / avg_price) * 100 if avg_price > 0 else 0
        
        # Determine trend direction
        if slope_percentage > 2:
            trend = 'increasing'
        elif slope_percentage < -2:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Find historical lowest
        min_price_idx = np.argmin(prices)
        historical_lowest = {
            'price': prices[min_price_idx],
            'date': dates[min_price_idx] if min_price_idx < len(dates) else None,
        }
        
        # Confidence based on data points
        confidence = min(0.9, 0.5 + (len(prices) * 0.05))
        
        return {
            'trend': trend,
            'confidence': confidence,
            'historical_lowest': historical_lowest,
            'average_price': avg_price,
            'price_volatility': np.std(prices) / avg_price if avg_price > 0 else 0,
        }
    
    def _get_seasonal_trend(self, season: str, days_until: int) -> Dict[str, Any]:
        """Get typical trend based on season and booking window."""
        # General patterns:
        # - High season: prices increase as date approaches
        # - Low season: prices may decrease for last-minute deals
        # - Shoulder season: moderate behavior
        
        if season == 'high_season':
            if days_until < 30:
                trend = 'increasing_fast'
            elif days_until < 60:
                trend = 'increasing'
            else:
                trend = 'stable'
            confidence = 0.7
        elif season == 'low_season':
            if days_until < 14:
                trend = 'decreasing'  # Last-minute deals
            else:
                trend = 'stable'
            confidence = 0.6
        else:  # shoulder_season
            trend = 'stable'
            confidence = 0.65
        
        return {
            'trend': trend,
            'confidence': confidence,
            'historical_lowest': None,
        }
    
    def _generate_recommendation(
        self,
        days_until_departure: int,
        season: str,
        trend: str,
        trip_type: str
    ) -> Dict[str, str]:
        """Generate booking recommendation based on analysis."""
        window = self.optimal_booking_windows.get(trip_type, self.optimal_booking_windows['international'])
        
        # Urgency levels
        if days_until_departure < 14:
            urgency = 'urgent'
            action = 'Book immediately - last-minute prices typically spike'
        elif days_until_departure < window['min']:
            urgency = 'high'
            action = 'Book within the next 7 days'
        elif days_until_departure > window['max']:
            urgency = 'low'
            action = 'Monitor prices - too early for best deals'
        elif days_until_departure >= window['min'] and days_until_departure <= window['sweet_spot']:
            urgency = 'optimal'
            action = 'Good time to book - within optimal window'
        else:
            urgency = 'moderate'
            action = 'Consider booking soon - approaching optimal window'
        
        # Adjust based on trend
        if 'increasing' in trend:
            action = 'Book soon - prices are trending upward'
            urgency = 'high' if urgency not in ['urgent'] else urgency
        elif trend == 'decreasing' and days_until_departure > 30:
            action = 'Wait 1-2 weeks - prices may drop further'
            urgency = 'low'
        
        # Seasonal adjustments
        if season == 'high_season' and days_until_departure > 90:
            action = 'Book early - high season demand drives prices up'
        
        return {
            'action': action,
            'urgency': urgency,
            'timing': self._format_timing(days_until_departure, window),
        }
    
    def _format_timing(self, days_until: int, window: Dict) -> str:
        """Format timing recommendation as human-readable string."""
        if days_until < 14:
            return 'Last minute - book now'
        elif days_until < window['min']:
            return f'Book within {window["min"] - days_until} days'
        elif days_until > window['max']:
            return f'Wait until {days_until - window["max"]} days before departure'
        elif days_until <= window['sweet_spot']:
            return 'Optimal booking window'
        else:
            return 'Good time to book'
    
    def _estimate_savings(
        self,
        current_price: Optional[float],
        trend: str,
        days_until: int
    ) -> Dict[str, Any]:
        """Estimate potential savings based on timing."""
        if not current_price:
            return {
                'amount': None,
                'percentage': None,
                'message': 'Provide current price for savings estimate',
            }
        
        # Estimate based on trend
        if trend == 'increasing':
            # Prices might increase 5-15% if waiting
            potential_increase = current_price * 0.10
            return {
                'amount': round(potential_increase, 2),
                'percentage': 10,
                'message': f'Prices may increase by ~${potential_increase:.0f} if you wait',
                'recommendation': 'Book now to avoid price increase',
            }
        elif trend == 'decreasing' and days_until > 30:
            # Prices might decrease 5-10% if waiting
            potential_savings = current_price * 0.07
            return {
                'amount': round(potential_savings, 2),
                'percentage': 7,
                'message': f'You might save ~${potential_savings:.0f} by waiting',
                'recommendation': 'Monitor prices for 1-2 weeks',
            }
        else:
            return {
                'amount': 0,
                'percentage': 0,
                'message': 'Prices are stable - timing has minimal impact',
                'recommendation': 'Book when convenient',
            }
    
    def _generate_price_forecast(self, days_until: int, season: str) -> List[Dict[str, Any]]:
        """Generate price forecast for next few weeks."""
        forecast = []
        base_price = 100  # Normalized base
        
        for week in range(0, 9, 2):  # Forecast for 0, 2, 4, 6, 8 weeks
            days_ahead = days_until - (week * 7)
            if days_ahead < 0:
                continue
            
            # Apply seasonal and time-based multipliers
            multiplier = 1.0
            
            # Seasonal effect
            if season == 'high_season':
                multiplier *= 1.2
            elif season == 'low_season':
                multiplier *= 0.9
            
            # Time effect (prices increase as date approaches)
            if days_ahead < 14:
                multiplier *= 1.3
            elif days_ahead < 30:
                multiplier *= 1.15
            elif days_ahead > 90:
                multiplier *= 0.95
            
            forecast.append({
                'weeks_from_now': week,
                'days_before_departure': days_ahead,
                'predicted_price_index': round(base_price * multiplier, 2),
                'recommendation': 'Book now' if week == 0 and days_ahead < 30 else 'Monitor',
            })
        
        return forecast


class SentimentAnalyzer:
    """
    Analyzes sentiment from travel reviews, blog posts, and social media.
    Provides destination sentiment scores and insights.
    """
    
    def __init__(self):
        # Sentiment lexicons
        self.positive_words = {
            'amazing', 'beautiful', 'excellent', 'great', 'wonderful', 'fantastic',
            'incredible', 'stunning', 'perfect', 'lovely', 'charming', 'delightful',
            'breathtaking', 'magnificent', 'spectacular', 'outstanding', 'superb',
            'memorable', 'enjoyable', 'pleasant', 'relaxing', 'peaceful', 'friendly',
            'affordable', 'convenient', 'accessible', 'safe', 'clean', 'comfortable',
            'delicious', 'authentic', 'unique', 'fascinating', 'impressive',
        }
        
        self.negative_words = {
            'terrible', 'awful', 'disappointing', 'overpriced', 'dirty', 'dangerous',
            'crowded', 'touristy', 'boring', 'poor', 'bad', 'worst', 'horrible',
            'rude', 'unfriendly', 'inconvenient', 'expensive', 'noisy', 'dirty',
            'unsafe', 'sketchy', 'run-down', 'mediocre', 'bland', 'generic',
            'scam', 'rip-off', 'avoid', 'disappointing', 'frustrating',
        }
        
        # Intensifiers (multiply sentiment strength)
        self.intensifiers = {
            'very': 1.5, 'really': 1.4, 'extremely': 1.6, 'absolutely': 1.7,
            'incredibly': 1.6, 'super': 1.4, 'quite': 1.2, 'somewhat': 0.7,
        }
        
        # Negators (flip sentiment)
        self.negators = {'not', "n't", 'no', 'never', 'neither', 'nobody', 'nothing'}
    
    async def analyze_destination_sentiment(
        self,
        texts: List[str],
        destination: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze overall sentiment for a destination.
        
        Args:
            texts: List of review/blog text snippets
            destination: Destination name (for context)
        
        Returns:
            Dict with sentiment scores and analysis
        """
        if not texts:
            return {
                'overall_sentiment': 'unknown',
                'score': 0.5,
                'confidence': 0.0,
                'message': 'No reviews available for analysis',
            }
        
        # Analyze each text
        individual_scores = []
        all_aspects = {
            'positive': [],
            'negative': [],
            'neutral': [],
        }
        
        for text in texts:
            result = self._analyze_single_text(text)
            individual_scores.append(result['score'])
            
            # Collect aspect mentions
            all_aspects['positive'].extend(result.get('positive_aspects', []))
            all_aspects['negative'].extend(result.get('negative_aspects', []))
        
        # Calculate aggregate scores
        avg_score = np.mean(individual_scores) if individual_scores else 0.5
        std_dev = np.std(individual_scores) if len(individual_scores) > 1 else 0
        
        # Determine sentiment category
        sentiment_category = self._categorize_sentiment(avg_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(len(texts), std_dev)
        
        # Get most common aspects
        top_positive = self._get_top_aspects(all_aspects['positive'])[:5]
        top_negative = self._get_top_aspects(all_aspects['negative'])[:5]
        
        return {
            'overall_sentiment': sentiment_category,
            'score': round(avg_score, 3),
            'confidence': round(confidence, 3),
            'total_reviews_analyzed': len(texts),
            'sentiment_distribution': self._get_distribution(individual_scores),
            'top_positive_aspects': top_positive,
            'top_negative_aspects': top_negative,
            'summary': self._generate_summary(sentiment_category, avg_score, top_positive, top_negative),
            'recommendation': self._generate_recommendation(sentiment_category, avg_score, confidence),
            'analyzed_at': datetime.now().isoformat(),
        }
    
    def _analyze_single_text(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of a single text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = 0
        negative_count = 0
        positive_aspects = []
        negative_aspects = []
        
        # Track context for aspect extraction
        prev_word = ''
        prev_intensity = 1.0
        
        for i, word in enumerate(words):
            # Check for intensifiers
            if word in self.intensifiers:
                prev_intensity = self.intensifiers[word]
                continue
            
            # Check for negators
            is_negated = prev_word in self.negators or (i > 0 and words[i-1] in self.negators)
            
            # Count sentiment words
            if word in self.positive_words:
                multiplier = -1 if is_negated else 1
                positive_count += prev_intensity * multiplier
                if i > 0:
                    positive_aspects.append(words[i-1])  # Context word
            elif word in self.negative_words:
                multiplier = -1 if is_negated else 1
                negative_count += prev_intensity * multiplier
                if i > 0:
                    negative_aspects.append(words[i-1])  # Context word
            
            prev_word = word
            prev_intensity = 1.0
        
        # Calculate score (0-1 scale, 0.5 is neutral)
        total = positive_count + negative_count
        if total == 0:
            score = 0.5
        else:
            score = 0.5 + (positive_count - negative_count) / (2 * total)
            score = max(0, min(1, score))  # Clamp to [0, 1]
        
        return {
            'score': score,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'positive_aspects': positive_aspects,
            'negative_aspects': negative_aspects,
        }
    
    def _categorize_sentiment(self, score: float) -> str:
        """Convert numeric score to category."""
        if score >= 0.8:
            return 'very_positive'
        elif score >= 0.65:
            return 'positive'
        elif score >= 0.45:
            return 'neutral'
        elif score >= 0.3:
            return 'negative'
        else:
            return 'very_negative'
    
    def _calculate_confidence(self, num_texts: int, std_dev: float) -> float:
        """Calculate confidence in sentiment analysis."""
        # More texts = higher confidence
        text_confidence = min(1.0, num_texts / 20)  # Max confidence at 20+ texts
        
        # Lower std dev = higher confidence (consistent opinions)
        variance_confidence = max(0.5, 1.0 - std_dev)
        
        return text_confidence * variance_confidence
    
    def _get_distribution(self, scores: List[float]) -> Dict[str, int]:
        """Get distribution of sentiment categories."""
        distribution = {
            'very_positive': 0,
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'very_negative': 0,
        }
        
        for score in scores:
            category = self._categorize_sentiment(score)
            distribution[category] += 1
        
        return distribution
    
    def _get_top_aspects(self, aspects: List[str]) -> List[Dict[str, Any]]:
        """Get most frequently mentioned aspects."""
        from collections import Counter
        
        if not aspects:
            return []
        
        # Count aspect frequencies
        counter = Counter(aspects)
        
        # Return top aspects with counts
        return [
            {'aspect': aspect, 'count': count}
            for aspect, count in counter.most_common(10)
        ]
    
    def _generate_summary(
        self,
        sentiment: str,
        score: float,
        positive_aspects: List[Dict],
        negative_aspects: List[Dict]
    ) -> str:
        """Generate human-readable sentiment summary."""
        if sentiment in ['very_positive', 'positive']:
            base = f"Travelers generally have a positive impression"
            if positive_aspects:
                top_aspect = positive_aspects[0]['aspect']
                base += f", particularly praising {top_aspect}"
        elif sentiment in ['negative', 'very_negative']:
            base = f"Reviews indicate some concerns"
            if negative_aspects:
                top_aspect = negative_aspects[0]['aspect']
                base += f", especially regarding {top_aspect}"
        else:
            base = "Opinions are mixed among travelers"
        
        return base + "."
    
    def _generate_recommendation(
        self,
        sentiment: str,
        score: float,
        confidence: float
    ) -> str:
        """Generate recommendation based on sentiment."""
        if sentiment in ['very_positive', 'positive'] and confidence > 0.6:
            return "Highly recommended based on traveler feedback"
        elif sentiment == 'neutral':
            return "Consider your priorities - may be good for some travelers, not for others"
        elif sentiment in ['negative', 'very_negative'] and confidence > 0.6:
            return "Consider alternative destinations or manage expectations"
        else:
            return "Limited data - research further before deciding"


async def analyze_destination_comprehensive(
    destination: str,
    texts: List[str],
    price_data: Optional[List[Dict]] = None,
    travel_dates: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Combined analysis: sentiment + price prediction.
    
    Args:
        destination: Destination name
        texts: Review/blog texts for sentiment analysis
        price_data: Historical price data (optional)
        travel_dates: Travel dates for price prediction (optional)
    
    Returns:
        Combined analysis results
    """
    sentiment_analyzer = SentimentAnalyzer()
    price_predictor = PricePredictor()
    
    # Run analyses in parallel
    sentiment_task = sentiment_analyzer.analyze_destination_sentiment(texts, destination)
    
    if price_data and travel_dates:
        price_task = price_predictor.predict_best_booking_time(
            destination, travel_dates, price_history=price_data
        )
    else:
        price_task = asyncio.sleep(0, result={
            'prediction': {'action': 'No price data available'},
            'confidence': 0,
        })
    
    sentiment_result, price_result = await asyncio.gather(sentiment_task, price_task)
    
    return {
        'destination': destination,
        'sentiment_analysis': sentiment_result,
        'price_prediction': price_result,
        'combined_recommendation': _generate_combined_recommendation(
            sentiment_result, price_result
        ),
        'analyzed_at': datetime.now().isoformat(),
    }


def _generate_combined_recommendation(
    sentiment: Dict[str, Any],
    price: Dict[str, Any]
) -> str:
    """Generate combined recommendation from sentiment and price analysis."""
    sentiment_rec = sentiment.get('recommendation', '')
    price_rec = price.get('prediction', {}).get('action', '')
    
    if sentiment.get('score', 0.5) > 0.7 and 'Book' in price_rec:
        return f"Great choice! {sentiment_rec}. {price_rec} for best value."
    elif sentiment.get('score', 0.5) > 0.7:
        return f"Excellent destination! {sentiment_rec}. {price_rec}."
    elif sentiment.get('score', 0.5) < 0.4:
        return f"Consider alternatives. {sentiment_rec}. {price_rec}."
    else:
        return f"{sentiment_rec}. {price_rec}."


# Import asyncio for combined function
import asyncio
