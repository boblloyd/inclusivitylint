import pytest
import re
import sys

import blocklint.main as bl
from blocklint.args import Args

# this is hacky, but only for testing...
try:  # python 2
    from StringIO import StringIO
    stdin_str = u'\n'.join([u'bab']*10 + [u'aba']*10)
except:  # python 3
    from io import StringIO
    stdin_str = '\n'.join(['bab']*10 + ['aba']*10)


def test_main(mocker):
    sys.stdin = StringIO(stdin_str)
    mock_print = mocker.patch('blocklint.main.print')
    bl.main(('--stdin --blocklist aba').split())
    assert mock_print.call_args_list == [
        mocker.call('stdin:' + str(i) + ':1: use of "aba"')
        for i in range(11, 21)]


def test_main_max_issues(mocker):
    sys.stdin = StringIO(stdin_str)
    mock_exit = mocker.patch('sys.exit')

    # higher
    mock_print = mocker.patch('blocklint.main.print')
    bl.main(('--stdin --blocklist aba --max-issue-threshold 11').split())
    assert mock_print.call_args_list == [
        mocker.call('stdin:' + str(i) + ':1: use of "aba"')
        for i in range(11, 21)]
    mock_exit.assert_not_called()

    # equal
    sys.stdin = StringIO('\n'.join(['bab']*10 + ['aba']*10))
    mock_print.reset_mock()
    bl.main(('--stdin --blocklist aba --max-issue-threshold 10').split())
    assert mock_print.call_args_list == (
        [mocker.call('stdin:' + str(i) + ':1: use of "aba"')
         for i in range(11, 21)] +
        [mocker.call('Found 10 issues, with maximum set to 10!')])
    mock_exit.assert_called_with(1)

    # lower
    sys.stdin = StringIO('\n'.join(['bab']*10 + ['aba']*10))
    mock_print.reset_mock()
    mock_exit.reset_mock()
    bl.main(('--stdin --blocklist aba --max-issue-threshold 9').split())
    assert mock_print.call_args_list == ([
        mocker.call('stdin:' + str(i) + ':1: use of "aba"')
        for i in range(11, 21)] +
        [mocker.call('Found 10 issues, with maximum set to 9!')])
    mock_exit.assert_called_with(1)


def test_get_args_wordlists(mocker):
    mocker.patch('os.getcwd', return_value='')
    arg_obj = Args()
    # defaults
    args = arg_obj.process_args([])
    assert arg_obj.blocklist == ['blacklist', 'master', 'slave', 'whitelist']
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == []
    assert args == {
        'blocklist': ['blacklist', 'master', 'slave', 'whitelist'],
        'exactlist': [],
        'files': [],
        'end_pos': False,
        'stdin': False,
        'max_issue_threshold': None,
        'skip_files': None,
        'wordlist': []}

    # set each list in turn
    args = arg_obj.process_args('--stdin --blocklist test'.split())
    assert arg_obj.blocklist == ['test']
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == []
    assert args == {
        'blocklist': ['test'],
        'exactlist': [],
        'files': [],
        'end_pos': False,
        'stdin': True,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': []}

    args = arg_obj.process_args('--exactlist test,test2'.split())
    assert arg_obj.blocklist == []
    assert arg_obj.exactlist == ['test', 'test2']
    assert arg_obj.wordlist == []
    assert args == {
        'blocklist': [],
        'exactlist': ['test', 'test2'],
        'files': [],
        'end_pos': False,
        'stdin': False,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': []}

    args = arg_obj.process_args('--wordlist test2'.split())
    assert arg_obj.blocklist == []
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == ['test2']
    assert args == {
        'blocklist': [],
        'exactlist': [],
        'files': [],
        'end_pos': False,
        'stdin': False,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': ['test2']}

    # remove duplicate words
    args = arg_obj.process_args(('--end-pos --blocklist test,test '
                        '--exactlist test2,test2 '
                        '--wordlist test3,test3').split())
    assert arg_obj.blocklist == ['test']
    assert arg_obj.exactlist == ['test2']
    assert arg_obj.wordlist == ['test3']
    assert args == {
        'blocklist': ['test'],
        'exactlist': ['test2'],
        'files': [],
        'end_pos': True,
        'stdin': False,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': ['test3']}

    # remove words from restrictive lists that are in more permissive ones
    # e.g. blocklist will match words and exact
    args = arg_obj.process_args(('-e --blocklist test '
                        '--exactlist test '
                        '--wordlist test').split())
    assert arg_obj.blocklist == ['test']
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == []
    assert args == {
        'blocklist': ['test'],
        'exactlist': [],
        'files': [],
        'end_pos': True,
        'stdin': False,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': []}

    args = arg_obj.process_args(('--blocklist test1 '
                        '--exactlist test '
                        '--wordlist test').split())
    assert arg_obj.blocklist == ['test1']
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == ['test']
    assert args == {
        'blocklist': ['test1'],
        'exactlist': [],
        'files': [],
        'end_pos': False,
        'stdin': False,
        'skip_files': None,
        'max_issue_threshold': None,
        'wordlist': ['test']}

    args = arg_obj.process_args(('--blocklist test1 '
                        '--skip-files tests/sample_files/test.py,'
                        'tests/sample_files/test.txt '
                        'files tests/sample_files/test.py '
                        'tests/sample_files/test.cc').split())

    # Test skip_files filter
    assert arg_obj.blocklist == ['test1']
    assert arg_obj.exactlist == []
    assert arg_obj.wordlist == []
    assert args == {
        'blocklist': ['test1'],
        'exactlist': [],
        'files': ['tests/sample_files/test.cc'],
        'end_pos': False,
        'stdin': False,
        'skip_files': set(('tests/sample_files/test.py', 'tests/sample_files/test.txt')),
        'max_issue_threshold': None,
        'wordlist': []}


def test_ignore_special():
    assert '' == bl.ignore_special('')
    assert 'a' == bl.ignore_special('a')
    assert 'a[^a-zA-Z0-9]?b' == bl.ignore_special('ab')
    assert 'a[^a-zA-Z0-9]?b[^a-zA-Z0-9]?c' == bl.ignore_special('abc')


def test_word_boundaries():
    assert '' == bl.word_boundaries('')
    assert r'\ba\b' == bl.word_boundaries('a')
    assert r'\bab\b' == bl.word_boundaries('ab')


def test_generate_re(mocker):
    # to test, just returning the re and if it's ignoring case
    mock_re = mocker.patch('re.compile', side_effect=lambda *x:
                           x[0] + ('i' if len(x) > 1 and x[1] == re.IGNORECASE
                                   else ''))
    assert bl.generate_re({'blocklist': [], 'wordlist': [],
                           'exactlist': []}) == {}

    assert bl.generate_re({'blocklist': ['bab'],
                           'wordlist': ['cac'],
                           'exactlist': ['dad']}) == {
                               'bab': 'b[^a-zA-Z0-9]?a[^a-zA-Z0-9]?bi',
                               'cac': r'\bc[^a-zA-Z0-9]?a[^a-zA-Z0-9]?c\bi',
                               'dad': r'\bdad\b'}


def test_generate_re_matches():
    regexes = bl.generate_re({'blocklist': ['bab', 'longerwordtotest'],
                              'wordlist': ['cac'],
                              'exactlist': ['dad']})

    assert list(bl.check_line('no matches', regexes, 'test', 1)) == []
    assert list(bl.check_line('bab bab bab', regexes, 'test', 1)) == [
        'test:1:1: use of "bab"',  # gets all babs
        'test:1:5: use of "bab"',
        'test:1:9: use of "bab"'
    ]
    assert list(bl.check_line('B-a*B bab bab', regexes, 'test', 1)) == [
        'test:1:1: use of "bab"',  # ignore case, special
        'test:1:7: use of "bab"',
        'test:1:11: use of "bab"'
    ]
    assert list(bl.check_line('this is a l!o@n#g$e%r^w&o*r(d)t-o_t+e=s/t',
                              regexes, 'test', 1)) == [
        'test:1:11: use of "longerwordtotest"'  # special
    ]
    assert list(bl.check_line('more l\\o|n?g[e]r{w}o,r.d<t>o`t~e;s:t',
                              regexes, 'test', 2, end_pos=True)) == [
        'test:2:6:36: use of "longerwordtotest"'  # more special
    ]
    assert list(bl.check_line('hereinababword', regexes, 'test', 3)) == [
        'test:3:8: use of "bab"'  # ignore case, special
    ]

    assert list(bl.check_line('aCAC not found, but !c@A?c. is ',
                              regexes, 'test', 4, end_pos=True)) == [
        'test:4:22:26: use of "cac"'  # ignore case, special
    ]

    assert list(bl.check_line('adad d@ad and DaD are missed, but not ,dad"',
                              regexes, 'test', 5)) == [
        'test:5:40: use of "dad"'  # ignore case, special
    ]

    regexes = bl.generate_re({
        'blocklist': ['blacklist', 'master', 'slave', 'whitelist'],
        'wordlist': [],
        'exactlist': [],
    })
    assert list(bl.check_line(
        'int test(std::vector<int> blacklist, int master){',
        regexes, 'test', 1)) == [
            'test:1:27: use of "blacklist"',
            'test:1:42: use of "master"'
        ]
