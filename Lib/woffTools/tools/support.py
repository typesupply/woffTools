from xml.etree import ElementTree
from cStringIO import StringIO

# ----------------------
# Very Simple XML Writer
# ----------------------

class XMLWriter(object):

    def __init__(self):
        self._root = None
        self._elements = []

    def simpletag(self, tag, **kwargs):
        ElementTree.SubElement(self._elements[-1], tag, **kwargs)

    def begintag(self, tag, **kwargs):
        if self._elements:
            s = ElementTree.SubElement(self._elements[-1], tag, **kwargs)
        else:
            s = ElementTree.Element(tag, **kwargs)
            if self._root is None:
                self._root = s
        self._elements.append(s)

    def endtag(self, tag):
        assert self._elements[-1].tag == tag
        del self._elements[-1]

    def write(self, text):
        if self._elements[-1].text is None:
            self._elements[-1].text = text
        else:
            self._elements[-1].text += text

    def compile(self, encoding="utf-8"):
        f = StringIO()
        tree = ElementTree.ElementTree(self._root)
        indent(tree.getroot())
        tree.write(f, encoding=encoding)
        text = f.getvalue()
        del f
        return text

def indent(elem, level=0):
    # this is from http://effbot.python-hosting.com/file/effbotlib/ElementTree.py
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for e in elem:
            indent(e, level + 1)
        if not e.tail or not e.tail.strip():
            e.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

# ------------
# HTML Helpers
# ------------

defaultCSS = """
        body {
            background-color: #e5e5e5;
            padding: 15px 15px 0px 15px;
            margin: 0px;
            font-family: Helvetica, Verdana, Arial, sans-serif;
        }

        h2.readError {
            background-color: red;
            color: white;
            margin: 20px 15px 20px 15px;
            padding: 10px;
            border-radius: 5px;
            -webkit-border-radius: 5px;
            -moz-border-radius: 5px;
            -webkit-box-shadow: #999 0 2px 5px;
            -moz-box-shadow: #999 0 2px 5px;
            font-size: 25px;
        }

        /* info blocks */

        .infoBlock {
            background-color: white;
            margin: 0px 0px 15px 0px;
            padding: 15px;
            border-radius: 5px;
            -webkit-border-radius: 5px;
            -moz-border-radius: 5px;
            -webkit-box-shadow: rgba(0, 0, 0, .3) 0 2px 5px;
            -moz-box-shadow: rgba(0, 0, 0, .3) 0 2px 5px;
        }

        h3.infoBlockTitle {
            font-size: 20px;
            margin: 0px 0px 15px 0px;
            padding: 0px 0px 10px 0px;
            border-bottom: 1px solid #e5e5e5;
        }

        h4.infoBlockTitle {
            font-size: 17px;
            margin: 0px 0px 15px 0px;
            padding: 0px 0px 10px 0px;
            border-bottom: 1px solid #e5e5e5;
        }

        table.report {
            border-collapse: collapse;
            width: 100%;
            font-size: 14px;
        }

        table.report tr {
            border-top: 1px solid white;
        }

        table.report tr.testPass {
            background-color: #c8ffaf;
        }

        table.report tr.testError {
            background-color: #ffc3af;
        }

        table.report tr.testWarning {
            background-color: #ffe1af;
        }

        table.report tr.testNote {
            background-color: #96e1ff;
        }

        table.report tr.testTraceback {
            background-color: red;
            color: white;
        }

        table.report td {
            padding: 7px 5px 7px 5px;
            vertical-align: top;
        }

        table.report td.title {
            width: 80px;
            text-align: right;
            font-weight: bold;
            text-transform: uppercase;
        }

        .infoBlock td p.info {
            font-size: 12px;
            font-style: italic;
            margin: 5px 0px 0px 0px;
        }

        /* SFNT table */

        table.sfntTableData {
            font-size: 14px;
            width: 100%;
            border-collapse: collapse;
            padding: 0px;
        }

        table.sfntTableData th {
            padding: 5px 0px 5px 0px;
            text-align: left
        }

        table.sfntTableData td {
            width: 20%;
            padding: 5px 0px 5px 0px;
            border: 1px solid #e5e5e5;
            border-left: none;
            border-right: none;
            font-family: Consolas, Menlo, "Vera Mono", Monaco, monospace;
        }

        /* Metadata */

        .metadataElement {
            background: rgba(0, 0, 0, 0.03);
            margin: 10px 0px 10px 0px;
            border: 2px solid #d8d8d8;
            padding: 10px;
        }

        h5.metadata {
            font-size: 14px;
            margin: 5px 0px 10px 0px;
            padding: 0px 0px 5px 0px;
            border-bottom: 1px solid #d8d8d8;
        }

        h6.metadata {
            font-size: 12px;
            font-weight: normal;
            margin: 10px 0px 10px 0px;
            padding: 0px 0px 5px 0px;
            border-bottom: 1px solid #d8d8d8;
        }

        table.metadata {
            font-size: 12px;
            width: 100%;
            border-collapse: collapse;
            padding: 0px;
        }

        table.metadata td.key {
            width: 5em;
            padding: 5px 5px 5px 0px;
            border-right: 1px solid #d8d8d8;
            text-align: right;
            vertical-align: top;
        }

        table.metadata td.value {
            padding: 5px 0px 5px 5px;
            border-left: 1px solid #d8d8d8;
            text-align: left;
            vertical-align: top;
        }

        p.metadata {
            font-size: 12px;
            font-style: italic;
        }

        /* Private Data */

        p.privateData {
            font-size: 12px;
            margin: 0px;
            padding: 0px;
        }
"""

def startHTML(title=None, cssReplacements={}):
    writer = XMLWriter()
    # start the html
    writer.begintag("html", xmlns="http://www.w3.org/1999/xhtml", lang="en")
    # start the head
    writer.begintag("head")
    writer.simpletag("meta", http_equiv="Content-Type", content="text/html; charset=utf-8")
    # title
    if title is not None:
        writer.begintag("title")
        writer.write(title)
        writer.endtag("title")
    # write the css
    writer.begintag("style", type="text/css")
    css = defaultCSS
    for before, after in cssReplacements.items():
        css = css.replace(before, after)
    writer.write(css)
    writer.endtag("style")
    # close the head
    writer.endtag("head")
    # start the body
    writer.begintag("body")
    # return the writer
    return writer

def finishHTML(writer):
    # close the body
    writer.endtag("body")
    # close the html
    writer.endtag("html")
    # get the text
    text = "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Transitional//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd\">\n"
    text += writer.compile()
    text = text.replace("c_l_a_s_s", "class").replace("http_equiv", "http-equiv")
    # return
    return text
