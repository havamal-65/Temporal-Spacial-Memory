"""
Simple Temporal Analysis Demo for "The Hobbit"

This script demonstrates basic pattern matching to extract temporal expressions from text.
"""

import re
from typing import List, Dict, Any

# Enhanced patterns for literary temporal expressions
LITERARY_TIME_PATTERNS = {
    "literary_duration": re.compile(
        r"\b((?:a |one |two |three |four |five |six |seven |eight |nine |ten |eleven |twelve |thirteen |fourteen |fifteen |twenty |thirty |forty |fifty |hundred |thousands? of |many |several |few |couple of )?"
        r"(?:minute|hour|day|night|week|month|year|decade|century|age)s?(?:(?: and | or )(?:a |one |two |three |four |five |six |seven |eight |nine |ten |eleven |twelve |thirteen |fourteen |fifteen |twenty |thirty |forty |fifty |hundred |many |several |few |couple of )?(?:minute|hour|day|night|week|month|year|decade|century|age)s?)?)\b",
        re.IGNORECASE
    ),
    "literary_relative": re.compile(
        r"\b(?:long ago|once upon a time|in ancient times|in olden days|in times of old|in the old days|once|before now|after that|since then|ever since|later|earlier|at that moment|at that time|in my time|in my grandfather's time|at present|nowadays|soon|recently|" 
        r"the (?:day|night|week|month|year) before|the next (?:day|night|week|month|year)|"
        r"(?:first|second|third|fourth|last) (?:age|day|night|week|month|year))\b",
        re.IGNORECASE
    ),
    "literary_time_of_day": re.compile(
        r"\b(?:dawn|daybreak|sunrise|morning|noon|midday|afternoon|evening|dusk|twilight|sunset|nightfall|midnight|night)\b",
        re.IGNORECASE
    ),
    "literary_seasons": re.compile(
        r"\b(?:spring|summer|autumn|fall|winter|midwinter|midsummer|harvest time|yuletide)\b",
        re.IGNORECASE
    ),
    "ordinal_time": re.compile(
        r"\b(?:(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|last) (?:time|day|night|week|month|year|age))\b",
        re.IGNORECASE
    ),
    "fantasy_time": re.compile(
        r"\b(?:(?:age|era|time) of (?:legends|dragons|elves|dwarves|magic|men|heroes|gods|darkness|light))\b",
        re.IGNORECASE
    ),
    "weekday": re.compile(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
        re.IGNORECASE
    ),
    "month_name": re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
        re.IGNORECASE
    ),
    "dates_with_ordinals": re.compile(
        r"\b(?:(?:January|February|March|April|May|June|July|August|September|October|November|December) (?:the )?(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth|Twenty-First|Twenty-Second|Twenty-Third|Twenty-Fourth|Twenty-Fifth|Twenty-Sixth|Twenty-Seventh|Twenty-Eighth|Twenty-Ninth|Thirtieth|Thirty-First))\b|"
        r"\b(?:(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|Thirteenth|Fourteenth|Fifteenth|Sixteenth|Seventeenth|Eighteenth|Nineteenth|Twentieth|Twenty-First|Twenty-Second|Twenty-Third|Twenty-Fourth|Twenty-Fifth|Twenty-Sixth|Twenty-Seventh|Twenty-Eighth|Twenty-Ninth|Thirtieth|Thirty-First) of (?:January|February|March|April|May|June|July|August|September|October|November|December))\b",
        re.IGNORECASE
    ),
    "special_dates": re.compile(
        r"\b(?:Mid-?year's [Dd]ay|Yule|New Year|Lithe|Mid-?summer)\b"
    ),
    "forever_expressions": re.compile(
        r"\b(?:forever|for ever(?: and ever)?|eternity|always|never|evermore)\b",
        re.IGNORECASE
    )
}

# Sample excerpts from The Hobbit with various temporal expressions
HOBBIT_EXCERPTS = [
    {
        "chapter": "Chapter 1: An Unexpected Party",
        "paragraph_id": "01.005",
        "text": "Long ago in my grandfather Took's time, Old Took was still the head of the family. My grandfather was famous for the Old Took's twelfth birthday party."
    },
    {
        "chapter": "Chapter 2: Roast Mutton",
        "paragraph_id": "02.038",
        "text": "By the next morning they had forgotten about the trolls and set off again into the wild. After breakfast they went on again, and by noon they reached a high hill."
    },
    {
        "chapter": "Chapter 3: A Short Rest",
        "paragraph_id": "03.003",
        "text": "They stayed long in that good house, fourteen days at least, and they found it hard to leave. Bilbo would gladly have stopped there for ever and ever."
    },
    {
        "chapter": "Chapter 5: Riddles in the Dark",
        "paragraph_id": "05.034",
        "text": "A few hours later, Bilbo woke up, in an unpleasant state. Gollum was at his side hissing to himself about his precious that had been lost for ages and ages."
    },
    {
        "chapter": "Chapter 9: Barrels Out of Bond",
        "paragraph_id": "09.025",
        "text": "Now the Wood-elves made merry for the return of their king, and after the autumn feast, for two days and two nights they partied, drinking wine and singing songs."
    },
    {
        "chapter": "Chapter 17: The Clouds Burst",
        "paragraph_id": "17.042",
        "text": "The Elvenking hurried forward to join the battle. But Bilbo remained behind, sitting on the stone, and thinking of what Gandalf had said to him long ago: 'You are only quite a little fellow in a wide world after all!'"
    },
    {
        "chapter": "Chapter 19: The Last Stage",
        "paragraph_id": "19.022",
        "text": "It was on May the First that they came back at last to the brink of the valley of Rivendell, where stood the Last (or the First) Homely House. They arrived on a Thursday, and on Friday there was a big party in the great hall with the elves."
    }
]

class TemporalMatch:
    """A simple class to represent a matched temporal expression."""
    def __init__(self, text, pattern_type, start, end):
        self.text = text
        self.pattern_type = pattern_type
        self.start = start
        self.end = end
    
    def __repr__(self):
        return f"TemporalMatch('{self.text}', type={self.pattern_type})"

def extract_literary_temporal_expressions(text: str) -> List[TemporalMatch]:
    """Extract temporal expressions from literary text using the patterns."""
    results = []
    
    # Apply literary patterns
    for pattern_name, pattern in LITERARY_TIME_PATTERNS.items():
        for match in pattern.finditer(text):
            start, end = match.span()
            match_text = match.group(0)
            
            # Create a temporal match
            temporal_match = TemporalMatch(
                text=match_text,
                pattern_type=pattern_name,
                start=start,
                end=end
            )
            
            # Check if this expression overlaps with any existing one
            # If it does, keep the longer one
            overlapping = False
            for i, existing in enumerate(results):
                if (start <= existing.end and end >= existing.start):
                    overlapping = True
                    if (end - start) > (existing.end - existing.start):
                        results[i] = temporal_match
                    break
            
            if not overlapping:
                results.append(temporal_match)
    
    # Sort by start position
    results.sort(key=lambda match: match.start)
    return results

def print_temporal_analysis(excerpt: Dict[str, str], matches: List[TemporalMatch]):
    """Print the temporal analysis in a readable format."""
    print(f"\n{'=' * 80}")
    print(f"Analyzing: {excerpt['chapter']} (Paragraph {excerpt['paragraph_id']})")
    print(f"{'=' * 80}")
    print(f"Text: {excerpt['text']}")
    print(f"{'-' * 80}")
    
    if not matches:
        print("No temporal expressions found in this excerpt.")
        return
    
    print(f"Found {len(matches)} temporal expressions:")
    for i, match in enumerate(matches, 1):
        print(f"\n{i}. Expression: \"{match.text}\"")
        print(f"   Type: {match.pattern_type}")
        print(f"   Position: {match.start}-{match.end}")

def main():
    """Main function to run the demo."""
    print("\nENHANCED TEMPORAL ANALYSIS OF 'THE HOBBIT'")
    print("=========================================\n")
    print("This demo extracts temporal expressions from excerpts of J.R.R. Tolkien's 'The Hobbit',")
    print("using pattern matching specifically designed for literary texts.")
    
    all_matches = []
    
    for excerpt in HOBBIT_EXCERPTS:
        # Extract temporal expressions with our patterns
        matches = extract_literary_temporal_expressions(excerpt['text'])
        all_matches.extend(matches)
        
        # Print the analysis
        print_temporal_analysis(excerpt, matches)
    
    print(f"\n{'-' * 80}")
    print(f"Total temporal expressions found: {len(all_matches)}")
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 