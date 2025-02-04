import string
import urllib

from lib.constants import (
    BANNED_PHRASES,
    BANNED_WORDS,
    CAMPTOWN_STRESSES,
    CHARS_ONLY,
    DICTIONARY_OVERRIDES,
    PRONUNCIATION_OVERRIDES,
)
from num2words import num2words as n2w
import pronouncing


def isCamptown(title: str):
    """Checks if a Wikipedia page title has the same stress pattern as Camptown.

    >>> isCamptown('Pedro, Marshal of Navarre')
    True

    >>> isCamptown('Single Payer Health Insurance')
    False

    >>> isCamptown('Romeo, Romeo, wherefore art thou, Romeo?')
    False
    """
    if containsBanned(title):
        return False

    title = cleanStr(title)
    title_stresses = getTitleStresses(title)
    # print(f"Stresses for {title}: {title_stresses}")
    if (not title_stresses) or (len(title_stresses) != 7):
        return False

    return True if CAMPTOWN_STRESSES.match(title_stresses) else False


def containsBanned(title: str):
    """Return True if banned words or phrases in string.

    This implementation is slow, but is was fast to write and I don't care about
    speed for this script.
    """

    def _containsBannedWord(title: str):
        for word in title.split():
            word = CHARS_ONLY.sub("", word.lower())
            if word in BANNED_WORDS:
                return True
        return False

    def _containsBannedPhrase(title: str):
        for phrase in BANNED_PHRASES:
            if phrase in title.lower():
                return True
        return False

    return _containsBannedWord(title) or _containsBannedPhrase(title)


def splitWords(s: str):
    # cmudict has apostrophes in words, so we should allow those.
    my_punctuation = string.punctuation.replace("'", "")
    return s.translate(str.maketrans('', '', my_punctuation)).split()


def getRhymingPartIfCamptown(title: str):
    if not isCamptown(title):
        return None
    print(f'{title}...')
    title_words = splitWords(title)
    last_word = title_words[-1]
    # This should never fail if isCamptown is true.
    phones = phonesForWord(numbersToWords(last_word))
    print(f'phones for {last_word}: {phones}')
    if not phones:
        return None
    return pronouncing.rhyming_part(phones[0])


def getTitleStresses(title: str):
    """Takes a wikipedia title and gets the combined stresses of all words.

    >>> getTitleStresses('Teenage Mutant Ninja Turtles')
    '12101010'

    Args:
        title: String, title of a wikipedia page.
    Returns:
        String, stresses of each syllable as 0, 1, and 2s.
    """
    title_words = splitWords(title)
    title_stresses = ""
    while title_words:
        if len(title_stresses) > 8:
            return None
        word = title_words.pop(0)
        word_stresses = getWordStresses(word)
        # print(f"Stresses for {word}: {word_stresses}")
        # If word was a long number, it may have been parsed into several words.
        if isinstance(word_stresses, list):
            title_words = word_stresses + title_words
        else:
            title_stresses += getWordStresses(word)

    return title_stresses


def getWordStresses(word: str):
    word = numbersToWords(word)
    if " " in word:
        return word.split()

    for override, stresses in PRONUNCIATION_OVERRIDES:
        if word.lower() == override.lower():
            return stresses

    try:
        phones = phonesForWord(word)
        stresses = pronouncing.stresses(phones[0])
    except IndexError:
        # Hacky way of discarding candidate title
        return "1111111111"
    return stresses


def phonesForWord(word):
    override_phones = DICTIONARY_OVERRIDES.get(word.lower())
    if override_phones:
        return override_phones
    else:
        return pronouncing.phones_for_word(word)

def numbersToWords(word):
    ordinal_number_endings = ("nd", "rd", "st", "th")
    if word.isdigit():
        if len(word) == 4:
            try:
                word = n2w(word, to="year")
            except Exception:
                # Hacky way of discarding candidate title
                return "1111111111"
        else:
            try:
                word = n2w(word)
            except Exception:
                # Hacky way of discarding candidate title
                return "1111111111"
    if word[:-2].isdigit() and word[-2:] in ordinal_number_endings:
        word = word[-2:]
        try:
            word = n2w(word, to="ordinal")
        except Exception:
            # Hacky way of discarding candidate title
            return "1111111111"

    return word


def cleanStr(s: str):
    """Remove characters that the pronouncing dictionary doesn't like.

    This isn't very efficient, but it's readable at least. :-)

    >>> cleanStr('fooBar123')
    'fooBar123'

    >>> cleanStr('Hello ([world])')
    'Hello world'

    >>> cleanStr('{hello-world}')
    'hello world'

    Args:
        s: String to be stripped of offending characters
    Returns:
        String without offending characters
    """
    DEL_CHARS = ["(", ")", "[", "]", "{", "}", ",", ":", ";", "."]
    SWAP_CHARS = [("-", " "), ("&", " and ")]

    for char in DEL_CHARS:
        s = s.replace(char, "")

    for char, replacement in SWAP_CHARS:
        s = s.replace(char, replacement)

    return s


def getWikiUrl(title: str):
    title = title.replace(" ", "_")
    title = urllib.parse.quote_plus(title)
    return "https://en.wikipedia.org/wiki/" + title


def addPadding(title: str):
    """If a title has 2 or 3 words, add extra spaces.

    The logo generator only makes the 4th word in turtle font. Adding spaces
    is a workaround to push the last word to the 4th word index, according to
    logo generator logic.

    Note that hyphenated words count separately by the logo generater.
    I.e. "noise-reduction" is two words.

    Also note if there is somehow an 8-syllable word in trochaic tetrameter,
    then we simply return it.

    >>> addPadding('Microsoft Transaction Server')
    'Microsoft  Transaction Server'

    >>> addPadding('Two Words')
    '  Two  Words'

    >>> addPadding('Teenage Mutant Ninja Turtles')
    'Teenage Mutant Ninja Turtles'

    Args:
        title: String, a wikipedia title in-tact
    Returns
        String, the title now with extra spaces
    """
    original_title = title
    # TODO: Make a sub-function for dealing with hyphens without replacing them.
    title = title.replace("-", " ")
    title_list = title.split()

    if len(title_list) > 3:
        return original_title
    if len(title_list) == 3:
        return title_list[0] + "  " + title_list[1] + " " + title_list[2]
    if len(title_list) == 2:
        return "  " + title_list[0] + "  " + title_list[1]
    if len(title_list) < 2:
        return original_title
