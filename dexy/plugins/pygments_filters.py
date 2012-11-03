from dexy.common import OrderedDict
from dexy.filter import DexyFilter
from dexy.plugins.standard_filters import StartSpaceFilter
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.formatters import LatexFormatter
from pygments.formatters import get_formatter_for_filename
from pygments.lexers import get_lexer_by_name
from pygments.lexers import get_lexer_for_filename
from pygments.lexers.agile import PythonConsoleLexer
from pygments.lexers.agile import RubyConsoleLexer
from pygments.lexers.text import TexLexer
from pygments.lexers.web import JavascriptLexer
from pygments.lexers.web import XmlLexer
import dexy.commands
import pygments.lexers.web
import re

class SyntaxHighlightRstFilter(DexyFilter):
    ALIASES = ['pyg4rst']

    def process_dict(self, input_dict):
        n = self.args().get('n', 2)
        result = OrderedDict()

        lexer = get_lexer_for_filename(self.input().storage.data_file())
        lexer_alias = lexer.aliases[0]

        for section_name, section_text in input_dict.iteritems():
            with_spaces = StartSpaceFilter.add_spaces_at_start(section_text, n)
            result[section_name] = ".. code:: %s\n\n%s" % (lexer_alias, with_spaces)

        return result

class PygmentsFilter(DexyFilter):
    """
    Apply Pygments syntax highlighting. Image formats require PIL.
    """
    INPUT_EXTENSIONS = [".*"]
    IMAGE_OUTPUT_EXTENSIONS = ['.png', '.bmp', '.gif', '.jpg']
    MARKUP_OUTPUT_EXTENSIONS = [".html", ".tex", ".svg"] # make sure .html is first!
    OUTPUT_EXTENSIONS = MARKUP_OUTPUT_EXTENSIONS + IMAGE_OUTPUT_EXTENSIONS
    ALIASES = ['pyg', 'pygments']
    FRAGMENT = True

    @classmethod
    def data_class_alias(klass, file_ext):
        if file_ext in klass.MARKUP_OUTPUT_EXTENSIONS:
            return 'sectioned'
        else:
            return 'generic'

    @classmethod
    def docmd_css(klass, style='default'):
        print klass.generate_css(style)

    @classmethod
    def docmd_sty(klass, style='default'):
        print klass.generate_sty(style)

    @classmethod
    def generate_css(self, style='default'):
        formatter = HtmlFormatter(style=style)
        return formatter.get_style_defs()

    @classmethod
    def generate_sty(self, style='default'):
        formatter = LatexFormatter(style=style)
        return formatter.get_style_defs()

    def create_lexer_instance(self, args):
        ext = self.artifact.prior.ext
        lexer = None
        lexer_args = {}

        # Pick out any options which are prefixed with "lexer-"
        for k in args.keys():
            m = re.match("^lexer-(.+)$", k)
            if m:
                option_name = m.groups()[0]
                option_value = args[k]
                self.log.debug("Using custom lexer option for %s with value %s" % (option_name, option_value))
                del args[k]
                lexer_args[option_name] = option_value

        # Create a lexer instance.
        if args.has_key('lexer'):
            self.log.debug("custom lexer alias %s specified" % args['lexer'])
            lexer = get_lexer_by_name(args['lexer'], **lexer_args)
            del args['lexer']
        else:
            is_json_file = ext in ('.json', '.dexy') or self.output().name.endswith(".dexy")
            if ext == '.pycon':
                lexer_class = PythonConsoleLexer
            elif ext == '.rbcon':
                lexer_class = RubyConsoleLexer
            elif is_json_file and (pygments.__version__ < '1.5'):
                lexer_class = JavascriptLexer
            elif is_json_file:
                lexer_class = pygments.lexers.web.JSONLexer
            elif ext == '.Rd':
                lexer_class = TexLexer # does a passable job
            elif ext == '.svg':
                lexer_class = XmlLexer
            else:
                fake_file_name = "input_text%s" % ext
                lexer = get_lexer_for_filename(fake_file_name, **lexer_args)

            if not lexer:
                lexer = lexer_class(**lexer_args)

        self.log.debug("Using lexer %s" % lexer.__class__.__name__)
        return lexer

    def create_formatter_instance(self, args):
        formatter_args = {'lineanchors' : self.output().web_safe_document_key() }

        # Python 2.6 doesn't like unicode keys as kwargs
        for k, v in args.iteritems():
            formatter_args[str(k)] = v

        return get_formatter_for_filename(self.output().name, **formatter_args)

    def process(self):
        if self.artifact.ext in self.IMAGE_OUTPUT_EXTENSIONS:
            try:
                import PIL
            except ImportError:
                print "python imaging library is required by pygments to create image output"
                raise dexy.exceptions.InactiveFilter('pyg', self.artifact.key)

        input_dict = self.input().as_sectioned()
        ext = self.artifact.prior.ext

        if input_dict.has_key('1') and not input_dict['1'] and ext in [".css", ".sty"]:
            # Special case if we get a virtual empty file, generate style file
            self.artifact.final = True
            self.artifact.ext = ext
            output_dict = OrderedDict()
            if ext == '.css':
                output_dict['1'] = self.generate_css(self.arg_value('style', 'default'))
            elif ext == '.sty':
                output_dict['1'] = self.generate_sty(self.arg_value('style', 'default'))
            else:
                raise dexy.commands.UserFeedback("pyg filter doesn't know how to generate a stylesheet for %s extension" % ext)
            return output_dict
        else:
            args = self.args().copy()
            lexer = self.create_lexer_instance(args)

            formatter_args = {'lineanchors' : self.output().web_safe_document_key() }

            # Python 2.6 hates unicode keys
            for k, v in args.iteritems():
                formatter_args[str(k)] = v

            formatter = get_formatter_for_filename(self.output().name, **formatter_args)

            if self.artifact.ext in self.IMAGE_OUTPUT_EXTENSIONS:
                with open(self.output_filepath(), 'wb') as f:
                    f.write(highlight(self.input().data(), lexer, formatter))

            else:
                output_dict = OrderedDict()
                for k, v in input_dict.items():
                    output_dict[k] = highlight(v.decode("utf-8"), lexer, formatter)
                self.output().set_data(output_dict)
