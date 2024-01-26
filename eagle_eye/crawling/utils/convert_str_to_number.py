def convert_str_to_number(input):
    if type(input) == int:
        return input
    elif type(input) == str:
        unit = input[-1]
        if unit == "만":
            multiplier = 10000
        elif unit == "억":
            multiplier = 100000000
        else:
            return int(input)

        number = float(input[:-1])
        return int(number * multiplier)
