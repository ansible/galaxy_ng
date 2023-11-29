SURVEY_FIELDS = [
    'docs',
    'ease_of_use',
    'does_what_it_says',
    'works_as_is',
    'used_in_production'
]


def calculate_survey_score(surveys):

    answer_count = 0
    survey_score = 0.0

    for survey in surveys:
        for k in SURVEY_FIELDS:
            data = getattr(survey, k)
            if data is not None:
                answer_count += 1
                survey_score += (data - 1) / 4

    score = (survey_score / answer_count) * 5

    return score
