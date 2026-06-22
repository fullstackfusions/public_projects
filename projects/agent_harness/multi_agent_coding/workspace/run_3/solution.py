def encode(s: str) -> str:
    """Compresses a string using run-length encoding."""
    if not s:
        return ""

    encoded_string = ""
    count = 1
    for i in range(len(s)):
        if i + 1 < len(s) and s[i] == s[i + 1]:
            count += 1
        else:
            if count > 1:
                encoded_string += str(count) + s[i]
            else:
                encoded_string += s[i]
            count = 1

    return encoded_string


def decode(s: str) -> str:
    """Reverses the run-length encoding."""
    if not s:
        return ""

    decoded_string = ""
    i = 0
    while i < len(s):
        count_str = ""
        while i < len(s) and s[i].isdigit():
            count_str += s[i]
            i += 1

        if not count_str:
            decoded_string += s[i]
            i += 1
        else:
            try:
                count = int(count_str)
                decoded_string += s[i] * count
                i += 1
            except ValueError:
                # Handle invalid encoded strings gracefully.  Just append the character and move on.
                decoded_string += s[i]
                i += 1

    return decoded_string