from dexy.common import OrderedDict
from dexy.plugins.process_filters import SubprocessFilter
from dexy.plugins.process_filters import SubprocessStdoutFilter
import json
import os
import re
import shutil

class CasperJsSvg2PdfFilter(SubprocessFilter):
    """
    Converts an SVG file to PDF by running it through casper js.
    # TODO convert this to phantomjs, no benefit to using casper here (js is not user facing) and more restrictive
    """
    ALIASES = ['svg2pdf']
    EXECUTABLE = 'casperjs'
    INPUT_EXTENSIONS = ['.svg']
    OUTPUT_EXTENSIONS = ['.pdf']
    VERSION_COMMAND = 'casperjs --version'

    def command_string(self):
        args = {
            'prog' : self.executable(),
            'args' : self.command_line_args() or ""
        }
        return "%(prog)s %(args)s script.js" % args

    def script_js(self, width, height):
        svgfile = self.prior().name
        pdffile = self.result().name
        return """
        var casper = require('casper').create({
             viewportSize : {width : %(width)s, height : %(height)s}
        });
        casper.start('%(svgfile)s', function() {
            this.capture('%(pdffile)s');
        });

        casper.run();
        """ % locals()

    def setup_wd(self):
        tmpdir = self.artifact.tmp_dir()

        if not os.path.exists(tmpdir):
            self.artifact.create_working_dir(
                    input_filepath=self.input_filepath(),
                    populate=True
                )

        width = self.args().get('width', 200)
        height = self.args().get('height', 200)
        js = self.script_js(width, height)

        script_name = "script.js"

        workfile_path = os.path.join(tmpdir, script_name)
        with open(workfile_path, "w") as f:
            f.write(js)

        return tmpdir

class CasperJsStdoutFilter(SubprocessStdoutFilter):
    """
    Runs scripts using casper js. Saves cookies.
    """
    ALIASES = ['casperjs']
    EXECUTABLE = 'casperjs'
    INPUT_EXTENSIONS = ['.js', '.txt']
    OUTPUT_EXTENSIONS = ['.txt']
    VERSION_COMMAND = 'casperjs --version'

    def command_string_stdout(self):
        args = {
            'cookie_file' : 'cookies.txt',
            'prog' : self.executable(),
            'args' : self.command_line_args() or "",
            'scriptargs' : self.command_line_scriptargs() or "",
            'script_file' : self.prior().name
        }
        return "%(prog)s --cookies-file=%(cookie_file)s %(args)s %(script_file)s %(scriptargs)s" % args

class PhantomJsStdoutFilter(SubprocessStdoutFilter):
    """
    Runs scripts using phantom js.
    """
    ALIASES = ['phantomjs']
    EXECUTABLE = 'phantomjs'
    INPUT_EXTENSIONS = ['.js', '.txt']
    OUTPUT_EXTENSIONS = ['.txt']
    VERSION_COMMAND = 'phantomjs --version'
    # TODO ensure phantom.exit() is called in script?

class PhantomJsRenderSubprocessFilter(SubprocessFilter):
    """
    Renders HTML to PNG/PDF using phantom.js. If the HTML relies on local
    assets such as CSS or image files, these should be specified as inputs.
    """
    ALIASES = ['phrender']
    EXECUTABLE = 'phantomjs'
    INPUT_EXTENSIONS = [".html", ".txt"]
    OUTPUT_EXTENSIONS = [".png", ".pdf"]
    VERSION_COMMAND = 'phantomjs --version'
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 768

    def command_string(self):
        args = {
            'prog' : self.executable(),
            'args' : self.command_line_args() or ""
        }
        return "%(prog)s %(args)s script.js" % args

    def setup_wd(self):
        wd = self.artifact.create_working_dir(self.input_filepath())

        width = self.arg_value('width', self.DEFAULT_WIDTH)
        height = self.arg_value('height', self.DEFAULT_HEIGHT)

        timeout = self.setup_timeout()
        if not timeout:
            timeout = 200

        args = {
                'address' : self.prior().name,
                'output' : self.result().name,
                'width' : width,
                'height' : height,
                'timeout' : timeout
                }

        js = """
        address = '%(address)s'
        output = '%(output)s'
        var page = new WebPage(),
            address, output, size;

        page.viewportSize = { width: %(width)s, height: %(height)s };
        page.open(address, function (status) {
            if (status !== 'success') {
                console.log('Unable to load the address!');
            } else {
                window.setTimeout(function () {
                page.render(output);
                phantom.exit();
                }, %(timeout)s);
            }
        });
        """ % args

        scriptfile = os.path.join(wd, "script.js")
        self.log.debug("scriptfile: %s" % scriptfile)
        with open(scriptfile, "w") as f:
            f.write(js)

        return wd
