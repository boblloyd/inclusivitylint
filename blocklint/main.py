from __future__ import print_function
import re
import sys
from collections import OrderedDict
from blocklint.args import Args

if sys.version_info >= (3, 5):
    from typing import Dict, Set, Union


ignore_class = '[^a-zA-Z0-9]'

# TODO fix broken pipe error
# https://pycodestyle.pycqa.org/en/latest/intro.html#configuration
# try:
#     if sys.platform == 'win32':
#         USER_CONFIG = os.path.expanduser(r'~\.pycodestyle')
#     else:
#         USER_CONFIG = os.path.join(
#             os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config'),
#             'pycodestyle'
#         )
# except ImportError:
#     USER_CONFIG = None


def main(args=None):
    args = Args().process_args(args)
    word_checkers = generate_re(args)
    total_issues = 0

    if args['stdin']:
        total_issues += process_file(sys.stdin, 'stdin', word_checkers,
                                     args['end_pos'])
    else:
        for file in args['files']:
            with open(file, 'r') as handle:
                total_issues += process_file(handle, file, word_checkers,
                                             args['end_pos'])

    if (args['max_issue_threshold'] is not None
            and args['max_issue_threshold'] <= total_issues):
        print(("Found {issues} issues, with maximum set to "
               "{max}!").format(
                   issues=total_issues,
                   max=args['max_issue_threshold']))
        sys.exit(1)


def process_file(input_file, file_name, word_checkers, end_pos):
    num_matched = 0
    try:
        for i, line in enumerate(input_file, 1):
            for match in check_line(line, word_checkers,
                                    file_name, i, end_pos):
                num_matched += 1
                print(match)
    except FileNotFoundError:
        pass
    except UnicodeDecodeError:
        pass
    return num_matched

def generate_re(args):
    result = OrderedDict()

    for word in args['blocklist']:
        result[word] = re.compile(ignore_special(word), re.IGNORECASE)

    for word in args['wordlist']:
        result[word] = re.compile(word_boundaries(ignore_special(word)),
                                  re.IGNORECASE)

    for word in args['exactlist']:
        result[word] = re.compile(word_boundaries(re.escape(word)))

    return result


def ignore_special(input_pattern):
    return (ignore_class + '?').join(re.escape(char) for char in input_pattern)


def word_boundaries(input_pattern):
    if input_pattern:
        input_pattern = r'\b' + input_pattern + r'\b'
    return input_pattern


def check_line(line, word_checkers, file, line_number, end_pos=False):
    fmt_str = '{file}:{line_number}:{start}: use of "{word}"'
    if end_pos:
        fmt_str = '{file}:{line_number}:{start}:{end}: use of "{word}"'

    pragma_regex = re.compile(r"blocklint:.*pragma")
    if pragma_regex.search(line):
        return

    for word, regex in word_checkers.items():
        for match in regex.finditer(line):
            yield fmt_str.format(
                file=file,
                line_number=line_number,
                start=match.start()+1,
                end=match.end(),
                word=word)


if __name__ == '__main__':
    main()
