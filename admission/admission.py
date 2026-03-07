from admission.admission_data import ADMISSION_DATA


def get_gpa_probability(school, student_gpa):

    gpa_data = ADMISSION_DATA[school]["gpa"]

    for gpa_range, values in gpa_data.items():

        admit, reject = values
        total = admit + reject

        if total == 0:
            continue

        if "-" in gpa_range:
            low, high = gpa_range.split("-")
            low = float(low)
            high = float(high)

            if low <= student_gpa < high:
                return admit / total

        else:
            if student_gpa >= float(gpa_range):
                return admit / total

    return 0.2


def get_school_background_probability(school, background):

    school_data = ADMISSION_DATA[school]["graduated_school"]

    if background not in school_data:
        return 0.3

    admit, reject = school_data[background]
    total = admit + reject

    if total == 0:
        return 0.3

    return admit / total


def get_gre_score(school, gre):

    median = ADMISSION_DATA[school]["median_gre"]

    if gre is None:
        return 0.5

    ratio = gre / median

    return min(ratio, 1.2) / 1.2


def compute_admission_probability(profile, school):

    gpa = profile.get("gpa")
    gre = profile.get("gre")
    background = profile.get("graduated_school")

    gpa_prob = get_gpa_probability(school, gpa)

    gre_score = get_gre_score(school, gre)

    school_prob = get_school_background_probability(
        school,
        background
    )

    probability = (
        0.5 * gpa_prob +
        0.3 * gre_score +
        0.2 * school_prob
    )

    return probability


def classify_probability(prob):

    if prob < 0.35:
        return "Reach"

    if prob < 0.65:
        return "Match"

    return "Safety"


def evaluate_dream_school(profile, school):

    prob = compute_admission_probability(
        profile,
        school
    )

    tier = classify_probability(prob)

    return {
        "probability": prob,
        "tier": tier
    }