import re

def strip_number_from_string(input_string):
    #match = re.search(r'(\D+)(\d+)$', input_string)
    #match = re.search(r'([\w\d_]*)(\d+)$', input_string)
    match = re.search(r'([\w_]*[A-Za-z_])(\d+)$', input_string)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        return prefix, int(number)
    else:
        return input_string, None
