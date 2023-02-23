ROMAN_DIGITS = "IVXLCDM"


def roman_to_int(s: str) -> int:
    rom_val = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    int_val = 0
    for i in range(len(s)):
        if i > 0 and rom_val[s[i]] > rom_val[s[i - 1]]:
            int_val += rom_val[s[i]] - 2 * rom_val[s[i - 1]]
        else:
            int_val += rom_val[s[i]]
    return int_val


def int_to_roman(num) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            roman_num += syb[i]
            num -= val[i]
        i += 1
    return roman_num


def parse_roman_plant_index(s: str) -> tuple[str, str]:
    """
    parse the roman plant index number, e.g. "Aloe depressa VI" -> ("Aloe depressa", "VI")
    """
    s_ending = s.split(" ")[-1]
    if any(s for s in s_ending if s not in ROMAN_DIGITS):
        raise ValueError(f"Invalid roman number: {s_ending}")
    return s[: -len(s_ending)].strip(), s_ending


def has_roman_plant_index(s: str) -> bool:
    """
    return True if supplied plant name has a roman plant name index, e.g. "Aloe depressa VI"
    """
    s_ending = s.split(" ")[-1]
    return not any(s for s in s_ending if s not in ROMAN_DIGITS)
