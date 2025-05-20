import sys
from pathlib import Path

# Assurez-vous que le chemin du projet est dans sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from app.db.queries import normalize_transcript_format

def test_normalize_transcript_format():
    """Test de la fonction de normalisation des transcriptions."""
    
    # Cas 1: Texte sans préfixe "Speaker"
    text1 = "A: Bonjour\nB: Comment ça va ?"
    expected1 = "Speaker A: Bonjour\nSpeaker B: Comment ça va ?"
    result1 = normalize_transcript_format(text1)
    assert result1 == expected1, f"Expected: {expected1}, Got: {result1}"
    print(f"Test 1 passed: {result1}")
    
    # Cas 2: Texte avec préfixe "Speaker" déjà présent
    text2 = "Speaker A: Bonjour\nSpeaker B: Comment ça va ?"
    expected2 = text2  # Pas de changement
    result2 = normalize_transcript_format(text2)
    assert result2 == expected2, f"Expected: {expected2}, Got: {result2}"
    print(f"Test 2 passed: {result2}")
    
    # Cas 3: Texte mixte
    text3 = "Speaker A: Bonjour\nB: Comment ça va ?\nSpeaker C: Très bien, merci !"
    expected3 = "Speaker A: Bonjour\nSpeaker B: Comment ça va ?\nSpeaker C: Très bien, merci !"
    result3 = normalize_transcript_format(text3)
    assert result3 == expected3, f"Expected: {expected3}, Got: {result3}"
    print(f"Test 3 passed: {result3}")
    
    # Cas 4: Texte sans préfixe du tout
    text4 = "Bonjour, comment ça va ?"
    expected4 = text4  # Pas de changement
    result4 = normalize_transcript_format(text4)
    assert result4 == expected4, f"Expected: {expected4}, Got: {result4}"
    print(f"Test 4 passed: {result4}")
    
    # Cas 5: Texte avec différents formats de préfixes
    text5 = "1: Premier intervenant\nA: Deuxième intervenant"
    expected5 = "Speaker 1: Premier intervenant\nSpeaker A: Deuxième intervenant"
    result5 = normalize_transcript_format(text5)
    assert result5 == expected5, f"Expected: {expected5}, Got: {result5}"
    print(f"Test 5 passed: {result5}")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_normalize_transcript_format()
