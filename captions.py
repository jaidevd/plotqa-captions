"""This module contains functions that generate captions.

Every question in the dataset can be classified into one of 49 templates
(present in `qa_templates.yaml`), depending on how well the question string
matches a given template. Each template has an ID. The functions in this module reflect how
a QA pair for a given ID is converted into a caption.

For a question, once the template ID is found, the corresponding function is called to
generate the caption.
"""

from random import choice


def coerce_input(_type):
    """Coerce the answer of a question into the given type.

    E.g. if the question is "What's the ratio of X to Y", then the answer is likely a float.
    Using this as a decorator validates whether the answer to a given question template
    is indeed a float.
    """
    def converter(func):
        return lambda x: func(_type(x))
    return converter


def binary_check(func):
    """Validate that the answer is a binary ∈ {'yes', 'no'}."""
    def validate(arg):
        if arg.lower() not in {"yes", "no"}:
            t_id = func.__name__.split("_")[1]
            raise ValueError(f"Invalid answer {arg} for template ID {t_id}.")
        return func(arg)

    return validate


@coerce_input(float)
def randomize_18(answer):
    """The ratio of the metric in xvalue1 to that in xval2 is answer."""
    equals = [
        "The {{ metric }} in {{ xvalue1 }} is equal to that in {{ xvalue2 }}.",
        "The {{ metric }} in {{ xvalue2 }} is equal to that in {{ xvalue1 }}.",
        "The {{ metric }} in {{ xvalue1 }} is the same as that in {{ xvalue2 }}.",
        "The {{ metric }} in {{ xvalue2 }} is the same as that in {{ xvalue1 }}.",
    ]
    greaters = [  # xvalue1 / xvalue2 > 1
        "The {{ metric }} in {{ xvalue1 }} is {{ answer }} times greater than "
        "that in {{ xvalue2 }}.",
        "The {{ metric }} in {{ xvalue1 }} is greater than that in {{ xvalue2 }} "
        "by a factor of {{ answer }}.",
        "The ratio of the {{ metric }} in {{ xvalue1 }} to that in {{ xvalue2 }} "
        "is {{ answer }}.",
        "The ratio of the {{ metric }} in {{ xvalue2 }} to that in {{ xvalue1 }} "
        "is {{ 1 / answer }}.",
    ]
    lessers = [  # xvalue1 / xvalue2 < 1
        "The {{ metric }} in {{ xvalue2 }} is {{ 1 / answer }} times greater than "
        "that in {{ xvalue1 }}.",
        "The {{ metric }} in {{ xvalue2 }} is greater than that in {{ xvalue1 }} by "
        "a factor of {{ 1 / answer }}.",
        "The ratio of the {{ metric }} in {{ xvalue1 }} to that in {{ xvalue2 }} "
        "is {{ answer }}.",
        "The ratio of the {{ metric }} in {{ xvalue2 }} to that in {{ xvalue1 }} "
        "is {{ 1 / answer }}."
    ]
    if answer == 0:
        return "The {{ metric }} in {{ xvalue1 }} is zero."
    if answer == 1:
        return choice(equals)
    if answer > 1:
        return choice(greaters)
    return choice(lessers)


@coerce_input(float)
def randomize_37(answer):
    """The difference between the metric in x1 and that in x2 is answer."""
    equals = [  # metric == 0
        "There is no difference between the {{ metric }} in {{ xvalue1 }} "
        "and that in {{ xvalue2 }}.",
        "There is no difference between the {{ metric }} in {{ xvalue2 }} and that in "
        "{{ xvalue1 }}.",
        "The {{ metric }} in {{ xvalue1 }} is equal to that in {{ xvalue2 }}.",
        "The {{ metric }} in {{ xvalue2 }} is equal to that in {{ xvalue1 }}.",
        "The {{ metric }} in {{ xvalue2 }} is the same as that in {{ xvalue1 }}.",
        "The {{ metric }} in {{ xvalue1 }} is the same as that in {{ xvalue2 }}.",
    ]
    greaters = [  # metric > 0
        "The {{ metric }} in {{ xvalue1 }} exceeds that in {{ xvalue2 }} by {{ answer }}.",
        "The {{ metric }} in {{ xvalue1 }} is greater than that in {{ xvalue2 }} by {{ answer }}.",
        "The {{ metric }} in {{ xvalue2 }} is less than that in {{ xvalue1 }} by {{ answer }}.",
        "The {{ metric }} in {{ xvalue1 }} is {{ answer }} more than that in {{ xvalue2 }}.",
        "The difference between the {{ metric }} in {{ xvalue1 }} and that in {{ xvalue2 }} "
        "is {{ answer }}.",
    ]
    lessers = [  # metric < 0
        "The {{ metric }} in {{ xvalue2 }} exceeds that in {{ xvalue1 }} by {{ -1 * answer }}.",
        "The {{ metric }} in {{ xvalue2 }} is greater than that in {{ xvalue1 }} by "
        "{{ -1 * answer }}.",
        "The {{ metric }} in {{ xvalue1 }} is less than that in {{ xvalue2 }} by "
        "{{ -1 * answer }}.",
        "The {{ metric }} in {{ xvalue2 }} is {{ -1 * answer }} more than that in {{ xvalue1 }}.",
        "The difference between the {{ metric }} in {{ xvalue2 }} and that in {{ xvalue1 }} is "
        "{{ -1 * answer }}.",
    ]
    if answer == 0:
        return choice(equals)
    if answer > 0:
        return choice(greaters)
    return choice(lessers)


@coerce_input(float)
def randomize_39(answer):
    """The difference between X and Y is answer.""",
    greaters = [
        "The {{ X }} is higher than the {{ Y }} by {{ answer }}.",
        "The {{ X }} is greater than the {{ Y }} by {{ answer }}.",
        "The {{ X }} exceeds the {{ Y }} by {{ answer }}.",
        "The {{ Y }} is less than the {{ X }} by {{ answer }}.",
    ]
    lessers = [
        "The {{ Y }} is higher than the {{ X }} by {{ answer }}.",
        "The {{ Y }} is greater than the {{ X }} by {{ answer }}.",
        "The {{ Y }} exceeds the {{ X }} by {{ answer }}.",
    ]
    unequals = [
        "The difference between the {{ X }} and the {{ Y }} is {{ answer }}.",
        "The {{ X }} and the {{ Y }} differ by {{ answer }}.",
        "The difference between the {{ Y }} and the {{ X }} is {{ answer }}.",
        "The {{ Y }} and the {{ X }} differ by {{ answer }}."
    ]
    equals = [
        "The {{ X }} is equal to the {{ Y }}.",
        "The {{ Y }} is equal to the {{ X }}.",
        "The {{ X }} is the same as the {{ Y }}.",
        "The {{ Y }} is the same as the {{ X }}.",
        "There is no difference between the {{ X }} and the {{ Y }}.",
        "There is no difference between the {{ Y }} and the {{ X }}.",
    ]
    if answer == 0:
        return choice(equals)
    if answer > 0:
        choices = choice([unequals, greaters])
        return choice(choices)
    choices = choice([unequals, lessers])
    return choice(choices)


@coerce_input(float)
def randomize_42(answer):
    """In the year {{ year }}, what is the difference between the {{ metric }} in {{grp1}}
    and {{ metric }} in {{ grp2 }}?"""
    equals = [
        "The {{ X }} and the {{ Y }} are the same in {{ year }}.",
        "The {{ X }} and the {{ Y }} are equal in {{ year }}.",
        "In the year {{ year }}, the {{ X }} and the {{ Y }} are the same.",
        "In the year {{ year }}, the {{ X }} and the {{ Y }} are equal.",
        "In {{ year }}, the {{ X }} and the {{ Y }} are the same.",
        "In {{ year }}, the {{ X }} and the {{ Y }} are equal.",
        "There is no difference between the {{ X }} and the {{ Y }} in {{ year }}.",
        "There is no difference between the {{ X }} and the {{ Y }} in the year {{ year }}.",
        "In the year {{ year }}, there is no difference between the {{ X }} and the {{ Y }}.",
        "In {{ year }}, there is no difference between the {{ X }} and the {{ Y }}.",
        "The {{ Y }} and the {{ X }} are the same in {{ year }}.",
        "The {{ Y }} and the {{ X }} are equal in {{ year }}.",
        "In the year {{ year }}, the {{ Y }} and the {{ X }} are the same.",
        "In the year {{ year }}, the {{ Y }} and the {{ X }} are equal.",
        "In {{ year }}, the {{ Y }} and the {{ X }} are the same.",
        "In {{ year }}, the {{ Y }} and the {{ X }} are equal.",
        "There is no difference between the {{ Y }} and the {{ X }} in {{ year }}.",
        "There is no difference between the {{ Y }} and the {{ X }} in the year {{ year }}.",
        "In the year {{ year }}, there is no difference between the {{ Y }} and the {{ X }}.",
        "In {{ year }}, there is no difference between the {{ Y }} and the {{ X }}.",
    ]
    greaters = [
        "In {{ year }}, the difference between the {{ X }} and the {{ Y }} is {{ answer }}.",
        "In the {{ year }}, the difference between the {{ X }} and the {{ Y }} is {{ answer }}.",
        "In {{ year }}, the {{ X }} is greater than the {{ Y }} by {{ answer }}.",
        "In the year {{ year }}, the {{ X }} is greater than the {{ Y }} by {{ answer }}.",
        "The difference between the {{ X }} and the {{ Y }} is {{ answer }} in {{ year }}.",
        "The difference between the {{ X }} and the {{ Y }} is {{ answer }} in the {{ year }}.",
        "The {{ X }} is greater than the {{ Y }} by {{ answer }} in {{ year }}.",
        "The {{ X }} is greater than the {{ Y }} by {{ answer }} in the year {{ year }}.",
        "In {{ year }}, the {{ Y }} is less than the {{ X }} by {{ answer }}.",
        "In the year {{ year }}, the {{ Y }} is less than the {{ X }} by {{ answer }}.",
        "The {{ Y }} is less than the {{ X }} by {{ answer }} in {{ year }}.",
        "The {{ Y }} is less than the {{ X }} by {{ answer }} in the year {{ year }}.",
    ]
    lessers = [
        "In {{ year }}, the difference between the {{ Y }} and the {{ X }} is {{ answer }}.",
        "In the {{ year }}, the difference between the {{ Y }} and the {{ X }} is {{ answer }}.",
        "In {{ year }}, the {{ Y }} is greater than the {{ X }} by {{ answer }}.",
        "In the year {{ year }}, the {{ Y }} is greater than the {{ X }} by {{ answer }}.",
        "The difference between the {{ Y }} and the {{ X }} is {{ answer }} in {{ year }}.",
        "The difference between the {{ Y }} and the {{ X }} is {{ answer }} in the {{ year }}.",
        "The {{ Y }} is greater than the {{ X }} by {{ answer }} in {{ year }}.",
        "The {{ Y }} is greater than the {{ X }} by {{ answer }} in the year {{ year }}.",
        "In {{ year }}, the {{ X }} is less than the {{ Y }} by {{ answer }}.",
        "In the year {{ year }}, the {{ X }} is less than the {{ Y }} by {{ answer }}.",
        "The {{ X }} is less than the {{ Y }} by {{ answer }} in {{ year }}.",
        "The {{ X }} is less than the {{ Y }} by {{ answer }} in the year {{ year }}.",
    ]
    if answer == 0:
        return choice(equals)
    if answer > 0:
        return choice(greaters)
    return choice(lessers)


@coerce_input(float)
def randomize_44(answer):
    """What is the difference between the X and the Y in xvalue?"""
    equals = [
        "In {{ xvalue }}, the {{ X }} and the {{ Y }} are the same.",
        "In {{ xvalue }}, the {{ Y }} and the {{ X }} are the same.",
        "The {{ X }} and the {{ Y }} are the same in {{ xvalue }}.",
        "The {{ Y }} and the {{ X }} are the same in {{ xvalue }}.",
        "In {{ xvalue }}, the {{ X }} and the {{ Y }} are equal.",
        "In {{ xvalue }}, the {{ Y }} and the {{ X }} are equal.",
        "The {{ X }} and the {{ Y }} are equal in {{ xvalue }}.",
        "The {{ Y }} and the {{ X }} are equal in {{ xvalue }}.",
        "There is no difference between the {{ X }} and the {{ Y }} in {{ xvalue }}.",
        "There is no difference between the {{ Y }} and the {{ X }} in {{ xvalue }}.",
    ]
    greaters = [
        "The difference between the {{ X }} and the {{ Y }} is {{ answer }}.",
        "The difference between the {{ Y }} and the {{ X }} is {{ answer }}.",
        "The {{ X }} is greater than the {{ Y }} by {{ answer }}.",
        "The {{ Y }} is less than the {{ X }} by {{ answer }}.",
        "The {{ X }} is {{ answer }} more than the {{ Y }}.",
        "The {{ X }} is {{ answer }} greater than the {{ Y }}.",
        "The {{ Y }} is {{ answer }} less than the {{ X }}.",
    ]
    lessers = [
        "The difference between the {{ Y }} and the {{ X }} is {{ answer }}.",
        "The difference between the {{ X }} and the {{ Y }} is {{ answer }}.",
        "The {{ Y }} is greater than the {{ X }} by {{ answer }}.",
        "The {{ X }} is less than the {{ Y }} by {{ answer }}.",
        "The {{ Y }} is {{ answer }} more than the {{ X }}.",
        "The {{ Y }} is {{ answer }} greater than the {{ X }}.",
        "The {{ X }} is {{ answer }} less than the {{ Y }}.",
    ]
    if answer == 0:
        return choice(equals)
    if answer > 0:
        return choice(greaters)
    return choice(lessers)


@binary_check
def randomize_1(answer):
    """Does the metric monotonically increase over the group?"""
    yays = [
        "The {{ metric }} monotonically increases over the {{ group }}.",
        "The {{ metric }} monotonically grows over the {{ group }}.",
        "The {{ metric }} grows over the {{ group }}.",
        "The {{ metric }} increases over the {{ group }}.",
    ]
    nays = [
        "The {{ metric }} does not monotonically increase over the {{ group }}.",
        "The {{ metric }} does not monotonically grow over the {{ group }}.",
        "The {{ metric }} does not grow over the {{ group }}.",
        "The {{ metric }} does not increase over the {{ group }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


def randomize_19(answer):
    """In how many groups is the metric greater than value?"""
    zeroes = [
        "The {{ metric }} is not greater than {{ value }} in any {{ groups }}.",
        "The {{ metric }} is never more than {{ value }} in any {{ groups }}."
    ]
    others = [
        "The {{ metric }} is greater than {{ value }} in {{ answer }} {{ groups }}.",
        "In {{ answer }} {{ groups }}, the {{ metric }} is greater than {{ value }}.",
    ]
    if answer == 0:
        return choice(zeroes)
    return choice(others)


def randomize_6(answer):
    """In how many groups1 is the X greater than the average Y taken over all groups2?"""
    zeros = [
        "The {{ X }} is never greater than the average {{ Y }}.",
        "In no {{ group1 }} is the {{ X }} greater than the average {{ Y }}.",
        "The {{ X }} is never higher than the average {{ Y }}.",
    ]
    others = [
        "The {{ X }} is greater than the average {{ Y }} in {{ answer }} {{ group1 }}.",
        "The {{ X }} is more than the average {{ Y }} in {{ answer }} {{ group1 }}.",
        "The {{ X }} is higher than the average {{ Y }} in {{ answer }} {{ group1 }}.",
    ]
    if answer == 0:
        return choice(zeros)
    return choice(others)


@binary_check
def randomize_17(answer):
    """Is the metric in X less than that in Y?"""
    yays = [
        "The {{ metric }} in {{ X }} is less than that in {{ Y }}.",
        "The {{ metric }} in {{ X }} is lower than that in {{ Y }}.",
        "The {{ metric }} in {{ Y }} is more than that in {{ X }}.",
        "The {{ metric }} in {{ Y }} is greater than that in {{ X }}.",
        "The {{ metric }} in {{ Y }} is higher than that in {{ X }}.",
    ]
    nays = [
        "The {{ metric }} in {{ X }} is not lower than that in {{ Y }}.",
        "The {{ metric }} in {{ X }} is not less than that in {{ Y }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_3(answer):
    """Is the sum of the {{metric1}} in {{ x1 }} and {{ x2 }} greater than the maximum
    {{metric2}} across all {{ groups }}?"""

    adj1, adj2 = ("greater", "higher", "more"), ("highest", "maximum", "greatest")
    yays_fmt = "The sum of the {{{{ metric1 }}}} in {{{{ x1 }}}} and {{{{ x2 }}}} is {a1} " \
        "than the {a2} {{{{ metric2 }}}} across all {{{{ groups }}}}."
    yays = []
    for a1 in adj1:
        for a2 in adj2:
            yays.append(yays_fmt.format(a1=a1, a2=a2))
    nays_fmt = "The sum of the {{{{ metric1 }}}} in {{{{ x1 }}}} and {{{{ x2 }}}} is not " \
        "{a1} than the {a2} {{{{ metric2 }}}} across all {{{{ groups }}}}."
    nays = []
    for a1 in adj1:
        for a2 in adj2:
            nays.append(nays_fmt.format(a1=a1, a2=a2))
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_8(answer):
    """Is it the case that in every {group} the sum of the {X} and {Y} is greater than the {Z}?"""
    yays = [
        "The sum of the {{ X }} and {{ Y }} is greater than the {{ Z }} in every {{ group }}.",
        "The sum of the {{ X }} and {{ Y }} is always greater than the {{ Z }}.",
        "In every {{ group }}, the sum of the {{ X }} and {{ Y }} is greater than the {{ Z }}.",
        "The sum of the {{ X }} and {{ Y }} is higher than the {{ Z }} in every {{ group }}.",
        "The sum of the {{ X }} and {{ Y }} is always higher than the {{ Z }}.",
        "In every {{ group }}, the sum of the {{ X }} and {{ Y }} is higher than the {{ Z }}.",
        "The sum of the {{ X }} and {{ Y }} is more than the {{ Z }} in every {{ group }}.",
        "The sum of the {{ X }} and {{ Y }} is always more than the {{ Z }}.",
        "In every {{ group }}, the sum of the {{ X }} and {{ Y }} is more than the {{ Z }}.",
    ]
    nays = [
        "The sum of the {{ X }} and {{ Y }} is not greater than the {{ Z }} in every {{ group }}."
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_9(answer):
    """Is the difference between the {{ X }} in {{ group1 }} and {{ group2 }} greater than the
    difference between the {{ Y }} in {{ group3 }} and {{ group4 }}?"""
    yays = [
        "The difference between the {{ X }} in {{ group1 }} and {{ group2 }} is greater than"
        " the difference between the {{ Y }} in {{ group3 }} and {{ group4 }}.",
        "The difference between the {{ X }} in {{ group2 }} and {{ group1 }} is greater than"
        " the difference between the {{ Y }} in {{ group4 }} and {{ group3 }}.",
        "The difference between the {{ Y }} in {{ group3 }} and {{ group4 }} is less than"
        " the difference between the {{ X }} in {{ group1 }} and {{ group2 }}.",
        "The difference between the {{ Y }} in {{ group4 }} and {{ group3 }} is less than"
        " the difference between the {{ X }} in {{ group2 }} and {{ group1 }}.",
        "The difference between the {{ X }} in {{ group1 }} and {{ group2 }} is more than"
        " the difference between the {{ Y }} in {{ group3 }} and {{ group4 }}.",
        "The difference between the {{ X }} in {{ group2 }} and {{ group1 }} is higher than"
        " the difference between the {{ Y }} in {{ group4 }} and {{ group3 }}.",
    ]
    nays = [
        "The difference between the {{ X }} in {{ group1 }} and {{ group2 }} is the same as"
        " the difference between the {{ Y }} in {{ group3 }} and {{ group4 }}.",
        "The difference between the {{ X }} in {{ group2 }} and {{ group1 }} is the same as"
        " the difference between the {{ Y }} in {{ group4 }} and {{ group3 }}.",
        "The difference between the {{ X }} in {{ group1 }} and {{ group2 }} is equal to"
        " the difference between the {{ Y }} in {{ group3 }} and {{ group4 }}.",
        "The difference between the {{ X }} in {{ group2 }} and {{ group1 }} is equal to"
        " the difference between the {{ Y }} in {{ group4 }} and {{ group3 }}.",
        "The difference between the {{ Y }} in {{ group3 }} and {{ group4 }} is the same as"
        " the difference between the {{ X }} in {{ group1 }} and {{ group2 }}.",
        "The difference between the {{ Y }} in {{ group4 }} and {{ group3 }} is the same as"
        " the difference between the {{ X }} in {{ group2 }} and {{ group1 }}.",
        "The difference between the {{ Y }} in {{ group3 }} and {{ group4 }} is equal to"
        " the difference between the {{ X }} in {{ group1 }} and {{ group2 }}.",
        "The difference between the {{ Y }} in {{ group3 }} and {{ group4 }} is equal to"
        " the difference between the {{ X }} in {{ group2 }} and {{ group1 }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


def randomize_11(answer):
    """What is the difference between the highest and the lowest {{ ylabel }}?"""
    nodiff = [
        "There is no difference between the highest and the lowest {{ ylabel }}.",
        "The highest and the lowest {{ ylabel }} are equal.",
        "The highest and the lowest {{ ylabel }} are the same.",
    ]
    diff = [
        "The difference between the highest and the lowest {{ ylabel }} is {{ answer }}.",
        "The highest and the lowest {{ ylabel }} differ by {{ answer }}.",
    ]
    if answer == 0:
        return choice(nodiff)
    return choice(diff)


def randomize_15(answer):
    """What is the difference between the highest and the second highest {{ ylabel }}?

    CAUTION: These answers don't make sense. If the difference is zero, it doesn't make
    sense to say that the difference between the highest and the second highest metric is zero.
    """
    nodiff = [
        "There is no difference between the highest and the second highest {{ ylabel }}.",
        "The highest {{ ylabel }} is the same as the second highest {{ ylabel }}.",
        "The highest {{ ylabel }} is equal to the second highest {{ ylabel }}.",
    ]
    diff = [
        "The difference between the highest and second highest {{ ylabel }} is {{ answer }}.",
        "The highest and the second highest {{ ylabel }} differ by {{ answer }}.",
        "The top two {{ ylabel }} differ by {{ answer }}.",
    ]
    if answer == 0:
        return choice(nodiff)
    return choice(diff)


@binary_check
def randomize_20(answer):
    """Is the {{ X }} strictly greater than the {{ Y }} over the {{ groups }}?"""
    yays = [
        "The {{ X }} is strictly greater than the {{ Y }} over the {{ groups }}.",
        "Over the {{ groups }}, the {{ X }} is strictly greater than the {{ Y }}.",
        "The {{ X }} is strictly higher than the {{ Y }} over the {{ groups }}.",
        "Over the {{ groups }}, the {{ X }} is strictly higher than the {{ Y }}.",
        "The {{ Y }} is strictly less than the {{ X }} over the {{ groups }}.",
        "Over the {{ groups }}, the {{ Y }} is strictly less than the {{ X }}.",
        "The {{ Y }} is strictly lower than the {{ X }} over the {{ groups }}.",
        "Over the {{ groups }}, the {{ Y }} is strictly lower than the {{ X }}.",
    ]
    nays = [
        "The {{ X }} is not strictly greater than the {{ Y }} over the {{ groups }}.",
        "Over the {{ groups }}, the {{ X }} is not strictly greater than the {{ Y }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_36(answer):
    """Is the {{ metric }} in {{ X }} less than that in {{ Y }}?"""
    yays = [
        "The {{ metric }} in {{ X }} is less than that in {{ Y }}.",
        "The {{ metric }} in {{ X }} is lower than that in {{ Y }}.",
        "The {{ metric }} in {{ Y }} is greater than that in {{ X }}.",
        "The {{ metric }} in {{ Y }} is higher than that in {{ X }}.",
        "The {{ metric }} in {{ Y }} is more than that in {{ X }}.",
    ]
    nays = ["The {{ metric }} in {{ X }} is not less than that in {{ Y }}."]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_16(answer):
    """Is the difference between the {{ metric }} in {{ X }} and {{ Y }} greater than the
    difference between any two {{ groups }}?"""
    yays = [
        "The difference between the {{ metric }} in {{ X }} and {{ Y }} is the "
        "highest between any two groups.",
        "The difference between the {{ metric }} in {{ Y }} and {{ X }} is the "
        "highest between any two groups.",
        "The difference between the {{ metric }} in {{ X }} and {{ Y }} is the "
        "greatest between any two groups.",
        "The difference between the {{ metric }} in {{ Y }} and {{ X }} is the "
        "greatest between any two groups.",
    ]
    nays = [
        "The difference between the {{ metric }} in {{ X }} and {{ Y }} is not greater than the "
        "difference between any two {{ groups }}."
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_21(answer):
    """Is the {{ X }} strictly less than the {{ Y }} over the {{ groups }}?"""
    yays = [
        "The {{ X }} is strictly less than the {{ Y }} over the {{ groups }}.",
        "The {{ Y }} is strictly greater than the {{ X }} over the {{ groups }}.",
        "The {{ Y }} is strictly higher than the {{ X }} over the {{ groups }}.",
        "Over all {{ groups }}, the {{ X }} is strictly less than the {{ Y }}.",
        "Over all {{ groups }}, the {{ Y }} is strictly higher than the {{ X }}.",
        "Over all {{ groups }}, the {{ Y }} is strictly greater than the {{ X }}.",
    ]
    nays = [
        "The {{ X }} is not strictly less than the {{ Y }} over the {{ groups }}.",
        "The {{ Y }} is not strictly greater than the {{ X }} over the {{ groups }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_12(answer):
    """Is the sum of the {{ m1 }} in {{ X }} and {{ Y }} greater than the maximum
    {{ m2 }} across all {{ groups }}?"""
    yays = [
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is greater than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is higher than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is more than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ X }} and {{ Y }} is more than the "
        "maximum {{ m2 }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ X }} and {{ Y }} is more than the "
        "highest {{ m2 }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ X }} and {{ Y }} is more than the "
        "greatest {{ m2 }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is greater than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is higher than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is more than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ Y }} and {{ X }} is more than the "
        "maximum {{ m2 }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ Y }} and {{ X }} is more than the "
        "highest {{ m2 }}.",
        "Across all {{ groups }}, the sum of the {{ m1 }} in {{ Y }} and {{ X }} is more than the "
        "greatest {{ m2 }}.",
    ]
    nays = [
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not greater than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not higher than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ X }} and {{ Y }} is not higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not greater than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not higher than the maximum {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not greater than the highest {{ m2 }} "
        "across all {{ groups }}.",
        "The sum of the {{ m1 }} in {{ Y }} and {{ X }} is not higher than the greatest {{ m2 }} "
        "across all {{ groups }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_7(answer):
    """Is it the case that in every {{ group }} the sum of the {{ metric }} is greater than
    the sum of {{ X }} and {{ Y }}?"""
    yays = [
        "In every {{ group }}, the sum of the {{ metric }} is greater than the sum of "
        "{{ X }} and {{ Y }}.",
        "In every {{ group }}, the sum of the {{ metric }} is higher than the sum of "
        "{{ X }} and {{ Y }}.",
        "In every {{ group }}, the sum of the {{ metric }} is more than the sum of "
        "{{ X }} and {{ Y }}.",
        "The sum of the {{ metric }} is greater than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is higher than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is more than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "In every {{ group }}, the sum of the {{ metric }} is greater than the sum of "
        "{{ Y }} and {{ X }}.",
        "In every {{ group }}, the sum of the {{ metric }} is higher than the sum of "
        "{{ Y }} and {{ X }}.",
        "In every {{ group }}, the sum of the {{ metric }} is more than the sum of "
        "{{ Y }} and {{ X }}.",
        "The sum of the {{ metric }} is greater than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is higher than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is more than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
    ]
    nays = [
        "The sum of the {{ metric }} is not greater than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is not more than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is not higher than the sum of the {{ X }} and {{ Y }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is not greater than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is not more than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
        "The sum of the {{ metric }} is not higher than the sum of the {{ Y }} and {{ X }} "
        "in every {{ group }}.",
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_14(answer):
    """Does the {{ ylabel }} monotonically increase over the {{ plural_xlabel }}?"""
    if answer.lower() == "yes":
        return "The {{ ylabel }} monotonically increases over the {{ plural_xlabel }}."
    return "The {{ ylabel }} does not monotonically increase over the {{ plural_xlabel }}."


@binary_check
def randomize_47(answer):
    """Is the {{ X }} strictly greater than the {{ Y }} over the years?"""
    yays = [
        "The {{ X }} is strictly greater than the {{ Y }} over the years.",
        "The {{ Y }} is strictly less than the {{ X }} over the years."
    ]
    nays = [
        "The {{ X }} is not strictly greater than the {{ Y }} over the years.",
        "The {{ X }} is less than or equal to {{ Y }} over the years."
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_48(answer):
    """Is the {{ X }} strictly less than the {{ Y }} over the years?"""
    yays = [
        "The {{ X }} is strictly less than the {{ Y }} over the years.",
        "The {{ Y }} is strictly greater than the {{ X }} over the years."
    ]
    nays = [
        "The {{ X }} is not strictly less than the {{ Y }} over the years.",
        "The {{ X }} is greater than or equal to the {{ Y }} over the years."
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


@binary_check
def randomize_49(answer):
    """Is it the case that in every {{ group }}, the sum of the {{ X }} and
    {{ Y }} is greater than the {{ Z }}?"""
    yays = [
        "In every {{ group }}, the sum of the {{ X }} and {{ Y }} is greater than the {{ Z }}.",
        "In every {{ group }}, the sum of the {{ Y }} and {{ X }} is greater than the {{ Z }}.",
        "In every {{ group }}, the {{ Z }} is less than the sum of the {{ X }} and {{ Y }}.",
        "In every {{ group }}, the {{ Z }} is less than the sum of the {{ Y }} and {{ X }}.",
    ]
    nays = [
        "The sum of the {{ X }} and {{ Y }} is less than or equal to the {{ Z }} in every group.",
        "The sum of the {{ Y }} and {{ X }} is less than or equal to the {{ Z }} in every group."
    ]
    if answer.lower() == "yes":
        return choice(yays)
    return choice(nays)


if __name__ == "__main__":
    print(randomize_3("foo"))
