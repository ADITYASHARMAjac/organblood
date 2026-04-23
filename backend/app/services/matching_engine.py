# MATCHING ALGORITHM - Core Business Logic
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import math
from app.config import settings


@dataclass
class MatchScore:
    """Match scoring result"""
    donor_id: str
    request_id: str
    compatibility_score: float
    distance_km: float
    blood_match_score: float = 100.0
    urgency_weight: float = 1.0
    distance_factor: float = 1.0
    
    def get_score_components(self) -> Dict[str, float]:
        return {
            "blood_match": self.blood_match_score,
            "urgency_weight": self.urgency_weight,
            "distance_factor": self.distance_factor,
            "final_score": self.compatibility_score
        }


class MatchingEngine:
    """Core matching algorithm implementation"""
    
    # Blood group compatibility matrix
    BLOOD_COMPATIBILITY = {
        "DONOR": {
            "O+": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],  # Can give to all
            "O-": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],  # Universal donor
            "A+": ["A+", "A-", "AB+", "AB-"],
            "A-": ["A+", "A-", "AB+", "AB-"],
            "B+": ["B+", "B-", "AB+", "AB-"],
            "B-": ["B+", "B-", "AB+", "AB-"],
            "AB+": ["AB+", "AB-"],
            "AB-": ["AB+", "AB-"],
        },
        "RECIPIENT": {
            "O+": ["O+", "O-"],
            "O-": ["O-"],
            "A+": ["O+", "O-", "A+", "A-"],
            "A-": ["O-", "A-"],
            "B+": ["O+", "O-", "B+", "B-"],
            "B-": ["O-", "B-"],
            "AB+": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],  # Universal recipient
            "AB-": ["O-", "A-", "B-", "AB-"],
        }
    }
    
    # Organ compatibility (simplified)
    ORGAN_COMPATIBILITY = {
        "KIDNEY": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        "HEART": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        "LIVER": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        "PANCREAS": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
        "CORNEA": ["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"],
    }

    @staticmethod
    def _normalize_token(value: Optional[str]) -> str:
        return str(value or "").strip().upper()
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula
        Returns distance in kilometers
        """
        R = settings.HAVERSINE_EARTH_RADIUS_KM
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        distance = R * c
        return round(distance, 2)
    
    @staticmethod
    def is_blood_compatible(donor_blood: str, recipient_blood: str) -> bool:
        """Check if donor's blood can be given to recipient"""
        donor_norm = MatchingEngine._normalize_token(donor_blood)
        recipient_norm = MatchingEngine._normalize_token(recipient_blood)
        if not donor_norm:
            return False
        # Emergency-flexible request. Admin still reviews downstream.
        if recipient_norm in {"", "ANY"}:
            return True

        recipient_can_receive = MatchingEngine.BLOOD_COMPATIBILITY["RECIPIENT"].get(recipient_norm, [])
        return donor_norm in recipient_can_receive
    
    @staticmethod
    def is_organ_compatible(donor_blood: str, recipient_blood: str, organ_type: str) -> bool:
        """Check if organ can be donated (simplified based on blood type)"""
        organ_norm = MatchingEngine._normalize_token(organ_type)
        if organ_norm in {"", "ANY"}:
            return MatchingEngine.is_blood_compatible(donor_blood, recipient_blood)
        if organ_norm not in MatchingEngine.ORGAN_COMPATIBILITY:
            return False
        # In real scenario, this should also include HLA typing and crossmatch.
        return MatchingEngine.is_blood_compatible(donor_blood, recipient_blood)
    
    @staticmethod
    def calculate_blood_match_score(donor_blood: str, recipient_blood: str) -> float:
        """
        Calculate blood match score (0-100)
        - Perfect match: 100
        - Compatible: 90
        - Incompatible: 0
        """
        donor_norm = MatchingEngine._normalize_token(donor_blood)
        recipient_norm = MatchingEngine._normalize_token(recipient_blood)
        if not donor_norm:
            return 0.0
        if recipient_norm in {"", "ANY"}:
            return 85.0
        if donor_norm == recipient_norm:
            return 100.0
        elif MatchingEngine.is_blood_compatible(donor_norm, recipient_norm):
            return 90.0
        else:
            return 0.0
    
    @staticmethod
    def calculate_distance_factor(distance_km: float) -> float:
        """
        Calculate distance factor (0-1)
        Closer = higher score
        Uses exponential decay
        """
        max_range = settings.MATCH_SEARCH_RADIUS_KM
        if distance_km > max_range:
            return 0.0
        
        # Exponential decay: closer distances get higher scores
        factor = math.exp(-distance_km / max_range)
        return round(factor, 2)
    
    @staticmethod
    def calculate_urgency_weight(urgency_level: str) -> float:
        """Get urgency weight multiplier"""
        weights = {
            "CRITICAL": settings.URGENCY_WEIGHT_CRITICAL,
            "MEDIUM": settings.URGENCY_WEIGHT_MEDIUM,
            "LOW": settings.URGENCY_WEIGHT_LOW,
        }
        return weights.get(urgency_level, 0.5)
    
    @staticmethod
    def calculate_compatibility_score(
        blood_match_score: float,
        distance_factor: float,
        urgency_weight: float
    ) -> float:
        """
        Calculate final compatibility score (0-100)
        
        Formula:
        score = (blood_match × 0.4 + distance_factor × 0.4) × urgency_weight × 100
        """
        # Weighted formula
        base_score = (blood_match_score * 0.4 + distance_factor * 100 * 0.4) / 100
        final_score = base_score * urgency_weight * 100
        
        return round(min(max(final_score, 0), 100), 2)
    
    @staticmethod
    def match_donor_to_request(
        donor: Dict,
        request: Dict,
        donor_location: Tuple[float, float],
        request_location: Tuple[float, float]
    ) -> Optional[MatchScore]:
        """
        Match a single donor to a request
        Returns MatchScore if compatible, None otherwise
        """
        # Extract data
        donor_blood = donor.get("blood_group")
        recipient_blood = request.get("blood_group_needed")
        donor_id = donor.get("id")
        request_id = request.get("id")
        request_type = request.get("request_type")
        urgency_level = request.get("urgency_level", "MEDIUM")
        
        # 1. Check blood compatibility
        if request_type in {"BLOOD", "PLASMA"}:
            blood_match_score = MatchingEngine.calculate_blood_match_score(donor_blood, recipient_blood)
            if blood_match_score == 0:
                return None  # Incompatible
        elif request_type == "ORGAN":
            organ_type = request.get("organ_type_needed")
            if not MatchingEngine.is_organ_compatible(donor_blood, recipient_blood, organ_type):
                return None
            blood_match_score = 90.0 if MatchingEngine._normalize_token(recipient_blood) in {"", "ANY"} else 95.0
        else:
            return None
        
        # 2. Calculate distance
        distance_km = MatchingEngine.haversine_distance(
            donor_location[0], donor_location[1],
            request_location[0], request_location[1]
        )
        
        # 3. Check if within search radius
        if distance_km > settings.MATCH_SEARCH_RADIUS_KM:
            return None
        
        # 4. Calculate factors
        distance_factor = MatchingEngine.calculate_distance_factor(distance_km)
        urgency_weight = MatchingEngine.calculate_urgency_weight(urgency_level)
        
        # 5. Calculate final score
        compatibility_score = MatchingEngine.calculate_compatibility_score(
            blood_match_score,
            distance_factor,
            urgency_weight
        )
        
        return MatchScore(
            donor_id=donor_id,
            request_id=request_id,
            compatibility_score=compatibility_score,
            distance_km=distance_km,
            blood_match_score=blood_match_score,
            urgency_weight=urgency_weight,
            distance_factor=distance_factor
        )
    
    @staticmethod
    def find_best_matches(
        available_donors: List[Dict],
        request: Dict,
        request_location: Tuple[float, float],
        top_n: Optional[int] = None
    ) -> List[MatchScore]:
        """
        Find best donor matches for a request
        
        Args:
            available_donors: List of available donors
            request: Blood/Organ request
            request_location: (latitude, longitude) of request
            top_n: Return top N matches (default from config)
        
        Returns:
            List of MatchScore objects, sorted by compatibility score (descending)
        """
        if top_n is None:
            top_n = settings.TOP_MATCHES_RETURNED
        
        matches = []
        
        # Calculate match score for each donor
        for donor in available_donors:
            donor_location = (float(donor.get("latitude")), float(donor.get("longitude")))
            match_score = MatchingEngine.match_donor_to_request(
                donor, request, donor_location, request_location
            )
            
            if match_score and match_score.compatibility_score > 0:
                matches.append(match_score)
        
        # Sort by compatibility score (descending)
        matches.sort(key=lambda x: x.compatibility_score, reverse=True)
        
        # Return top N
        return matches[:top_n]


# ==================== TESTING ====================
if __name__ == "__main__":
    # Test Haversine distance
    # Mumbai to Bangalore: ~970 km
    distance = MatchingEngine.haversine_distance(19.0760, 72.8777, 12.9716, 77.5946)
    print(f"Distance Mumbai to Bangalore: {distance} km")
    
    # Test blood compatibility
    print(f"O+ can give to AB-: {MatchingEngine.is_blood_compatible('O+', 'AB-')}")
    print(f"O- can give to everyone: {MatchingEngine.is_blood_compatible('O-', 'AB+')}")
    
    # Test blood match score
    print(f"Perfect match (O+ to O+): {MatchingEngine.calculate_blood_match_score('O+', 'O+')}")
    print(f"Compatible match (O+ to AB+): {MatchingEngine.calculate_blood_match_score('O+', 'AB+')}")
    
    # Test distance factor
    print(f"Distance factor for 5km: {MatchingEngine.calculate_distance_factor(5.0)}")
    print(f"Distance factor for 100km: {MatchingEngine.calculate_distance_factor(100.0)}")
    
    # Test urgency weight
    print(f"Critical urgency weight: {MatchingEngine.calculate_urgency_weight('CRITICAL')}")
    print(f"Low urgency weight: {MatchingEngine.calculate_urgency_weight('LOW')}")
