from dexy.plugin import PluginMeta
import dexy.doc
import json
import re

class Parser:
    """
    Parse various types of config file.
    """
    ALIASES = []

    __metaclass__ = PluginMeta

    @classmethod
    def is_active(klass):
        return True

    def __init__(self, wrapper=None):
        self.wrapper = wrapper

class OriginalDexyParser(Parser):
    ALIASES = [".dexy", "dexy.json"]

    def parse(self, input_text):
        info = json.loads(input_text)
        for k, v in info.iteritems():
            if "allinputs" in v:
                pass # TODO convert this..

            doc = dexy.doc.PatternDoc(k, wrapper=self.wrapper, **v)
            self.wrapper.docs.append(doc)

class TextFileParser(Parser):
    ALIASES = ["docs.txt"]

    def parse(self, input_text):
        for line in input_text.splitlines():
            line = line.strip()
            if not (line == "" or re.match("\s*#", line)):
                if " " in line:
                    pattern, raw_args = line.split(" ", 1)
                    try:
                        args = json.loads(raw_args)
                    except ValueError as e:
                        print e.message
                        self.wrapper.log.debug("Failed to parse extra args '%s' with json parser" % raw_args)
                        args = {}
                else:
                    pattern = line
                    args = {}

                if not "*" in pattern:
                    doc = dexy.doc.Doc(pattern, depends=True, wrapper=self.wrapper, **args)
                else:
                    doc = dexy.doc.PatternDoc(pattern, depends=True, wrapper=self.wrapper, **args)

                self.wrapper.docs.append(doc)
        return self.wrapper.docs
