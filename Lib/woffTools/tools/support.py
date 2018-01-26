from fontTools.misc.py23 import *
import os
import time
from xml.etree import ElementTree

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
    i = "\n" + level * "\t"
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "\t"
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

table.report tr.testPass, table.report tr.testReportPass {
	background-color: #c8ffaf;
}

table.report tr.testError, table.report tr.testReportError {
	background-color: #ffc3af;
}

table.report tr.testWarning, table.report tr.testReportWarning {
	background-color: #ffe1af;
}

table.report tr.testNote, table.report tr.testReportNote {
	background-color: #96e1ff;
}

table.report tr.testTraceback, table.report tr.testReportTraceback {
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

table.report td.testReportResultCount {
	width: 100px;
}

table.report td.toggleButton {
	text-align: center;
	width: 50px;
	border-left: 1px solid white;
	cursor: pointer;
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

table.sfntTableData tr.uncompressed {
	background-color: #ffc3af;
}

table.sfntTableData td {
	width: 20%;
	padding: 5px 0px 5px 0px;
	border: 1px solid #e5e5e5;
	border-left: none;
	border-right: none;
	font-family: Consolas, Menlo, "Vera Mono", Monaco, monospace;
}

pre {
	font-size: 12px;
	font-family: Consolas, Menlo, "Vera Mono", Monaco, monospace;
	margin: 0px;
	padding: 0px;
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

/* Proof */

/* proof: @font-face rule */

p.characterSet {
	/* proof: @font-face font-family */
	line-height: 135%;
	word-wrap: break-word;
	margin: 0px;
	padding: 0px;
}

p.sampleText {
	/* proof: @font-face font-family */
	line-height: 135%;
	margin: .5em 0px 0px 0px;
	padding: .5em 0px 0px 0px;
	border-top: 1px solid #e5e5e5;
}
"""

defaultJavascript = """

//<![CDATA[
	function testResultToggleButtonHit(buttonID, className) {
		// change the button title
		var element = document.getElementById(buttonID);
		if (element.innerHTML == "Show" ) {
			element.innerHTML = "Hide";
		}
		else {
			element.innerHTML = "Show";
		}
		// toggle the elements
		var elements = getTestResults(className);
		for (var e = 0; e < elements.length; ++e) {
			toggleElement(elements[e]);
		}
		// toggle the info blocks
		toggleInfoBlocks();
	}

	function getTestResults(className) {
		var rows = document.getElementsByTagName("tr");
		var found = Array();
		for (var r = 0; r < rows.length; ++r) {
			var row = rows[r];
			if (row.className == className) {
				found[found.length] = row;
			}
		}
		return found;
	}

	function toggleElement(element) {
		if (element.style.display != "none" ) {
			element.style.display = "none";
		}
		else {
			element.style.display = "";
		}
	}

	function toggleInfoBlocks() {
		var tables = document.getElementsByTagName("table")
		for (var t = 0; t < tables.length; ++t) {
			var table = tables[t];
			if (table.className == "report") {
				var haveVisibleRow = false;
				var rows = table.rows;
				for (var r = 0; r < rows.length; ++r) {
					var row = rows[r];
					if (row.style.display == "none") {
						var i = 0;
					}
					else {
						haveVisibleRow = true;
					}
				}
				var div = table.parentNode;
				if (haveVisibleRow == true) {
					div.style.display = "";
				}
				else {
					div.style.display = "none";
				}
			}
		}
	}
//]]>
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
    # write the javascript
    writer.begintag("script", type="text/javascript")
    javascript = defaultJavascript
    ## hack around some ElementTree escaping
    javascript = javascript.replace("<", "l_e_s_s")
    javascript = javascript.replace(">", "g_r_e_a_t_e_r")
    writer.write(javascript)
    writer.endtag("script")
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
    text = text.replace("c_l_a_s_s", "class")
    text = text.replace("a_p_o_s_t_r_o_p_h_e", "'")
    text = text.replace("l_e_s_s", "<")
    text = text.replace("g_r_e_a_t_e_r", ">")
    text = text.replace("http_equiv", "http-equiv")
    # return
    return text

# ---------
# File Name
# ---------

def findUniqueFileName(path):
    if not os.path.exists(path):
        return path
    folder = os.path.dirname(path)
    fileName = os.path.basename(path)
    fileName, extension = os.path.splitext(fileName)
    stamp = time.strftime("%Y-%m-%d %H-%M-%S %Z")
    newFileName = "%s (%s)%s" % (fileName, stamp, extension)
    newPath = os.path.join(folder, newFileName)
    # intentionally break to prevent a file overwrite.
    # this could happen if the user has a directory full
    # of files with future time stamped file names.
    # not likely, but avoid it all the same.
    assert not os.path.exists(newPath)
    return newPath
