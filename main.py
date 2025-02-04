#!/usr/bin/env python3
import os
import sys
import time

from lib import datastore
from lib import blue_sky
from lib import words
from lib.constants import BACKOFF, MAX_ATTEMPTS, MAX_STATUS_LEN, TIMEOUT_BACKOFF
import wikipedia


def main():
    if os.environ.get("LOCAL_DATASTORE"):
        storage = datastore.LocalDatastore(os.environ.get("LOCAL_DATASTORE"))
    elif os.environ.get("S3_BUCKET"):
        storage = datastore.S3Datastore(os.environ["S3_BUCKET"], os.environ["S3_KEY"])
    else:
        storage = datastore.NullDatastore()
    rhyming_dict = storage.load()
    (new_rhyming_dict, title1, title2) = searchForCamptown(
        rhyming_dict, MAX_ATTEMPTS, BACKOFF
    )
    storage.dump(new_rhyming_dict)
    if title1 and title2:
        postSkeet(title1, title2)


def lambda_handler(event, context):
    return main()


def postSkeet(title1, title2):
    status_text = "\n".join((title1, "Doo dah, doo dah", title2, "Oh, doo dah day"))

    if len(status_text) <= MAX_STATUS_LEN:
        _ = blue_sky.sendOneSkeet(status_text)
        print(status_text)
    else:
        print(f"Oh no, this was too long: {status_text}")


def sameFinalWord(title1, title2):
    return title1.lower().split()[-1] == title2.lower().split()[-1]


def searchForCamptown(rhyming_dict, attempts=MAX_ATTEMPTS, backoff=BACKOFF):
    """Loop MAX_ATTEMPT times, searching for a Camptown meter wikipedia title.

    Args:
        Integer: attempts, retries remaining.
        Integer: backoff, seconds to wait between each loop.
    Returns:
        String or False: String of wikipedia title in Camptown meter, or False if
                         none found.
    """
    for attempt in range(attempts):
        rhymes = checkTenPagesForCamptown()
        for rhyme, title in rhymes:
            old_title = rhyming_dict.get(rhyme, None)
            if old_title:
                if sameFinalWord(old_title, title):
                    print(
                        f"{old_title} and {title} are not a good rhyme so I will just throw {title} away for now."
                    )
                    continue
                print(f"\nMatched: {title} and {old_title}")
                del rhyming_dict[rhyme]
                return (rhyming_dict, old_title, title)
            else:
                print(f"\nAdding {title}, which rhymes with {rhyme}")
                rhyming_dict[rhyme] = title

        time.sleep(backoff)

    print(f"\nNo matches found.")
    return (rhyming_dict, None, None)


def checkTenPagesForCamptown():
    """Get 10 random wiki titles, check if any of them isCamptown().

    We grab the max allowed Wikipedia page titles (10) using wikipedia.random().
    If any title is in Camptown meter, return the title. Otherwise, return False.

    Args:
        None
    Returns:
        List of (String,String) pairs
    """
    wikipedia.set_rate_limiting(True)
    try:
        titles = wikipedia.random(10)
    except wikipedia.exceptions.HTTPTimeoutError as e:
        print(f"Wikipedia timout exception: {e}")
        time.sleep(TIMEOUT_BACKOFF)
        main()
    except wikipedia.exceptions.WikipediaException as e:
        print(f"Wikipedia exception: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Exception while fetching wiki titles: {e}")
        sys.exit(1)

    rhymes = []
    for title in titles:
        rhyme = words.getRhymingPartIfCamptown(title)
        if rhyme:
            rhymes.append((rhyme, title))
    return rhymes


if __name__ == "__main__":
    main()
