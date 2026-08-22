from scraper.normalizer import (
    normalize_rent, normalize_bhk, normalize_gender, 
    normalize_food_pref, normalize_smoking_pref
)

def test_normalize_rent():
    assert normalize_rent("₹ 35,000") == 35000
    assert normalize_rent("35000") == 35000
    assert normalize_rent("Rs. 15,500") == 15500
    assert normalize_rent(None) == 0

def test_normalize_bhk():
    assert normalize_bhk("2 BHK") == 2
    assert normalize_bhk("3BHK") == 3
    assert normalize_bhk("1") == 1
    assert normalize_bhk("Studio") == 0
    assert normalize_bhk(None) == 0

def test_normalize_gender():
    assert normalize_gender("Boys") == "male"
    assert normalize_gender("Girls") == "female"
    assert normalize_gender("Male") == "male"
    assert normalize_gender("Female") == "female"
    assert normalize_gender("Any") == "any"
    assert normalize_gender(None) == "any"

def test_normalize_food_pref():
    assert normalize_food_pref("Veg") == "veg"
    assert normalize_food_pref("Non Veg") == "non_veg"
    assert normalize_food_pref("Any") == "any"
    assert normalize_food_pref(None) == "any"

def test_normalize_smoking_pref():
    assert normalize_smoking_pref("Smoker") == "smoker"
    assert normalize_smoking_pref("Non-smoker") == "non_smoker"
    assert normalize_smoking_pref("No Smoking") == "non_smoker"
    assert normalize_smoking_pref("Any") == "any"
    assert normalize_smoking_pref(None) == "any"
