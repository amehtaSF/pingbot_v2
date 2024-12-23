import random
import string


def generate_non_confusable_code(length=8):
    # Define non-confusable characters
    non_confusable_chars = ''.join(ch for ch in string.ascii_lowercase if ch not in {'l', 'o'})
    non_confusable_chars += ''.join(ch for ch in string.ascii_uppercase if ch not in {'I', 'O'})
    non_confusable_chars += ''.join(ch for ch in string.digits if ch not in {'0', '1'})
    # Generate an length-character code
    return ''.join(random.choices(non_confusable_chars, k=length))