from __future__ import annotations

ROMAN_DIGITS = "IVXLCDM"


def roman_to_int(roman_number: str) -> int:
    rom_val = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    int_val = 0
    for position, roman_number_char in enumerate(roman_number):  # range(len(roman_number)):
        if position > 0 and rom_val[roman_number_char] > rom_val[roman_number[position - 1]]:
            int_val += rom_val[roman_number_char] - 2 * rom_val[roman_number[position - 1]]
        else:
            int_val += rom_val[roman_number_char]
    return int_val


def int_to_roman(num: int) -> str:
    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
    roman_num = ""
    counter = 0
    while num > 0:  # pylint: disable=while-used
        for _ in range(num // val[counter]):
            roman_num += syb[counter]
            num -= val[counter]
        counter += 1
    return roman_num


def parse_roman_plant_index(plant_name: str) -> tuple[str, str]:
    """parse the roman plant index number, e.g. "Aloe depressa VI" -> ("Aloe depressa", "VI")"""
    s_ending = plant_name.split(" ")[-1]
    if any(s for s in s_ending if s not in ROMAN_DIGITS):
        raise ValueError(f"Invalid roman number: {s_ending}")
    return plant_name[: -len(s_ending)].strip(), s_ending


def has_roman_plant_index(plant_name: str) -> bool:
    """Return True if supplied plant name has a roman plant name index, e.g. "Aloe depressa VI"."""
    s_ending = plant_name.split(" ")[-1]
    return not any(s for s in s_ending if s not in ROMAN_DIGITS)
