import argparse
import configparser
import os

class Args:
    """
    Args
    Handles the parsing and assignment of arguments.  This is a class representation of the
    blocklint arguments, rather than an array of arguments.  If a value is None it is not
    required and not provided (i.e. skip_files may be None, but max_threshold would have a
    default)
    """

    def __init__(self):
        self.blocklist = 'master,slave,whitelist,blacklist'
        self.exactlist = None
        self.wordlist = None
        self.max_issue_threshold = 0
        self.skip_files = None
        self.end_pos = False
        self.files = None
        self.wordlists = ('blocklist', 'wordlist', 'exactlist')
    
    def process_args(self, args):
        # from least to most restrictive

        parser = argparse.ArgumentParser(description='Lint block-listed words')
        parser.add_argument('files', nargs='*',
                            help='Files or directories to lint, default all '
                            'files in current directory')
        parser.add_argument('--blocklist', help='Comma separated list of words '
                            'to lint in any context, with possibly special '
                            'characters between, case insensitive; '
                            'DEFAULT to master,slave,whitelist,blacklist')
        parser.add_argument('--wordlist', help='Comma separated list of words '
                            'to lint as whole words, with possibly special '
                            'characters between, case insensitive')
        parser.add_argument('--exactlist', help='Comma separated list of words '
                            'to lint as whole words exactly as entered')
        parser.add_argument('-e', '--end-pos', action='store_true',
                            help='Show the end position of a match in output')
        parser.add_argument('--stdin', action='store_true',
                            help='Use stdin as input instead of file list')
        parser.add_argument("--max-issue-threshold", type=int, required=False,
                            help='Cause non-zero exit status of more than this '
                            'many issues found')
        parser.add_argument("--skip-files", type=str,
                            help='Paths to files that should _not_ be checked by '
                            'blocklint, even if within a checked directory')
        args = vars(parser.parse_args(args))

        args = self.get_config(args)
        args = self.get_skip_files(args)

        # TODO add in checks for config files
        if self._no_lists_provided(args):
            args['blocklist'] = 'master,slave,whitelist,blacklist'

        args = self.get_word_list(args)
        args = self.get_file_list(args)

        return args
    
    def _no_lists_provided(self, args):
        return args['blocklist'] is None and \
                args['wordlist'] is None and \
                args['exactlist'] is None
    
    def get_word_list(self, args):
        for wordlist in self.wordlists:
            if args[wordlist] is not None:
                # split CSV, remove duplicates
                if os.path.exists(args[wordlist]):
                    # reading from a file
                    with open(args[wordlist], 'r', encoding="UTF-8") as wordlist_file:
                        setattr(self, wordlist, wordlist_file.read())
                        args[wordlist] = wordlist_file.read()
                else:
                    setattr(self, wordlist, set(args[wordlist].split(',')))
                    args[wordlist] = set(args[wordlist].split(','))
            else:
                setattr(self, wordlist, set())
                args[wordlist] = set()                
        return self._unique_wordlists(args)

    def _unique_wordlists(self, args):
        # remove repeats across lists from least to most restrictive
        for i, wordlist in enumerate(self.wordlists):
            for other in self.wordlists[i+1:]:
                setattr(self, other, getattr(self, other) - getattr(self, wordlist))
                args[other] -= args[wordlist]

            # sort for deterministic output
            setattr(self, wordlist, sorted(getattr(self, wordlist)))
            args[wordlist] = sorted(args[wordlist])
        return args

    def get_file_list(self, args):
        # parse files argument into individual files
        if not args['files']:
            args['files'] = [os.getcwd()]

        files = []
        for file in args['files']:
            if os.path.isdir(file):
                files += [os.path.join(file, f) for f in os.listdir(file)
                        if os.path.isfile(os.path.join(file, f))]
            # isabs detects pipes
            elif os.path.isfile(file) or os.path.isabs(file):
                files.append(file)
        if args['skip_files'] is not None:
            files = [file for file in files if file not in args['skip_files']]

        args['files'] = files
        return args

    def get_config(self, args):
        config_paths = [
            os.path.join(os.path.expanduser('~'), '.blocklint'),
            './.blocklint',
            './setup.cfg',
            './tox.ini',
        ]
        present_config_files = [
            path for path in config_paths if os.path.exists(path)
        ]
        config = configparser.ConfigParser()
        for path in present_config_files:
            config.read(path)
        config_settings = {}  # type: Dict[str, Union[str, bool, int, Set[str]]]
        if 'blocklint' in config:
            config_settings = dict(config['blocklint'])
        for key in args:
            if args[key] is None and key in config_settings:
                if key in ['end_pos', 'stdin']:
                    config_settings[key] = config.getboolean('blocklint', key)
                if key in ['max_issue_threshold']:
                    config_settings[key] = config.getint('blocklint', key)
                if key in ['skip_files']:
                    config_settings[key] = config.get('blocklint', key)
                args[key] = config_settings[key]       
        return args

    def get_skip_files(self, args):
        if args['skip_files'] is not None:
            # config files have multiline args
            skip_files = args['skip_files'].split('\n')
            skip_files = [path for line in skip_files
                        for path in line.split(',')]
            args['skip_files'] = set(skip_files)
        return args