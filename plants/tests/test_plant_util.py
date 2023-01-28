# testing utility functions, i.e. no fixtures, database dependencies or test client required
import pytest

from plants.modules.plant.util import parse_roman_plant_index, roman_to_int, int_to_roman, has_roman_plant_index


def test_parse_roman_plant_index():
    subsequent_name = parse_roman_plant_index("Aloe depressa VI")
    assert subsequent_name == ("Aloe depressa", "VI")
    subsequent_name = parse_roman_plant_index("Aloe depressa I")
    assert subsequent_name == ("Aloe depressa", "I")
    subsequent_name = parse_roman_plant_index("× Aloe rauhii 'Demi' × Gasteria batesiana IX")
    assert subsequent_name == ("× Aloe rauhii 'Demi' × Gasteria batesiana", "IX")
    with pytest.raises(ValueError):
        parse_roman_plant_index("Aloe depressa")


def test_has_roman_plant_index():
    assert has_roman_plant_index("Aloe depressa VI") is True
    assert has_roman_plant_index("× Aloe rauhii 'Demi' × Gasteria batesiana IX") is True
    assert has_roman_plant_index("Aloe depressa") is False


def test_roman_to_int():
    assert roman_to_int("II") == 2
    assert roman_to_int("III") == 3
    assert roman_to_int("IV") == 4
    assert roman_to_int("V") == 5
    assert roman_to_int("VI") == 6
    assert roman_to_int("VII") == 7
    assert roman_to_int("VIII") == 8
    assert roman_to_int("IX") == 9
    assert roman_to_int("X") == 10
    assert roman_to_int("XIV") == 14


def test_int_to_roman():
    assert int_to_roman(2) == "II"
    assert int_to_roman(3) == "III"
    assert int_to_roman(4) == "IV"
    assert int_to_roman(5) == "V"
    assert int_to_roman(6) == "VI"
    assert int_to_roman(7) == "VII"
    assert int_to_roman(8) == "VIII"
    assert int_to_roman(9) == "IX"
    assert int_to_roman(10) == "X"
    assert int_to_roman(14) == "XIV"
