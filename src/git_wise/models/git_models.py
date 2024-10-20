from enum import Enum
class Language(Enum):
    ENGLISH = ("English (default)", "en")
    CHINESE = ("Chinese", "zh")
    CUSTOM = ("Custom", None)

class DetailLevel(Enum):
   DETAILED = (
       "Detailed - Comprehensive commit messages with context",
       """detailed:
       - Clear summary line (<72 chars)
       - Full context & motivation
       - List key changes with bullets
       - Reference related issues
       Length: ~300 words"""
   )
   
   BRIEF = (
       "Brief - Concise but informative messages (Recommended)", 
       """brief:
       - Clear summary line (<72 chars)
       - 2-3 key points
       - Focus on what & why
       Length: ~100 words"""
   )
   
   MINIMAL = (
       "Minimal - Just the essential changes",
       """minimal:
       - Single line (<72 chars)
       - Type + core change only
       Length: 50-72 chars"""
   )

class Model(Enum):
    GPT4O_MINI = ("GPT-4o-mini (Recommended, sufficient for most cases and more cost-effective)", "gpt-4o-mini")
    GPT4O = ("GPT-4o (Full capability, higher cost)", "gpt-4o")