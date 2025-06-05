from agno.tools import tool
from dataclasses import dataclass
from typing import Optional

@dataclass
class ClinicalInfo:
    location: str
    duration: str
    appearance: str
    symptoms: str

@tool(description="Get clinical information from the patient")
async def get_clinical_input(location: str, duration: str, appearance: str, symptoms: str) -> ClinicalInfo:
    """
    Collect clinical information from the patient about their skin condition.
    
    Args:
        location (str): Location of the skin condition
        duration (str): How long has the condition been present
        appearance (str): Description of appearance (color, size, texture)
        symptoms (str): Any symptoms (itching, pain, etc)
    
    Returns:
        ClinicalInfo: Structured clinical information
    """
    return ClinicalInfo(
        location=location,
        duration=duration,
        appearance=appearance,
        symptoms=symptoms
    )
