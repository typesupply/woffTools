"""
A module for reporting information about the contents of
WOFF files. *reportInfo* is the only public function.

This can also be used as a command line tool.
"""

# import test

importErrors = []
try:
    import numpy
except:
    importErrors.append("numpy")
try:
    import fontTools
except ImportError:
    importErrors.append("fontTools")
try:
    import woffTools
except ImportError:
    importErrors.append("woffTools")

if importErrors:
    import sys
    print("Could not import needed module(s): %s" % ", ".join(importErrors))
    sys.exit()

# import

import os
import optparse
from woffTools import WOFFFont
from woffTools.tools.support import startHTML, finishHTML, findUniqueFileName
from woffTools.tools.css import makeFontFaceRule


# ----------------
# Report Functions
# ----------------

def writeFileInfo(font, fontPath, writer):
    # start the block
    writer.begintag("div", c_l_a_s_s="infoBlock")
    # title
    writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
    writer.write("File Information")
    writer.endtag("h3")
    # table
    writer.begintag("table", c_l_a_s_s="report")
    writeFileInfoRow("FILE", os.path.basename(fontPath), writer)
    writeFileInfoRow("DIRECTORY", os.path.dirname(fontPath), writer)
    writeFileInfoRow("FILE SIZE", str(font.reader.length) + " bytes", writer)
    writeFileInfoRow("VERSION", "%d.%d" % (font.majorVersion, font.minorVersion), writer)
    writer.endtag("table")
    ## close the container
    writer.endtag("div")

def writeFileInfoRow(title, value, writer):
    # row
    writer.begintag("tr")
    # title
    writer.begintag("td", c_l_a_s_s="title")
    writer.write(title)
    writer.endtag("td")
    # message
    writer.begintag("td")
    writer.write(value)
    writer.endtag("td")
    # close row
    writer.endtag("tr")

def writeSFNTInfo(font, writer):
    # start the block
    writer.begintag("div", c_l_a_s_s="infoBlock")
    # title
    writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
    writer.write("sfnt Tables")
    writer.endtag("h3")
    # tables
    writer.begintag("table", c_l_a_s_s="sfntTableData")
    writer.begintag("tr")
    columns = "tag offset compLength origLength origChecksum".split()
    for c in columns:
        writer.begintag("th")
        writer.write(c)
        writer.endtag("th")
    writer.endtag("tr")
    for tag, entry in sorted(font.reader.tables.items()):
        if entry.compLength == entry.origLength:
            writer.begintag("tr", c_l_a_s_s="uncompressed")
        else:
            writer.begintag("tr")
        for attr in columns:
            v = getattr(entry, attr)
            if attr == "origChecksum":
                v = hex(v)
            else:
                v = str(v)
            writer.begintag("td")
            writer.write(v)
            writer.endtag("td")
        writer.endtag("tr")
    writer.endtag("table")
    ## close the block
    writer.endtag("div")

def writeMetadata(font, writer):
    # start the block
    writer.begintag("div", c_l_a_s_s="infoBlock")
    # title
    writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
    writer.write("Metadata")
    writer.endtag("h3")
    # content
    if font.metadata is not None:
        for element in font.metadata:
            writeMetadataElement(element, writer)
    # close the block
    writer.endtag("div")

def writeMetadataElement(element, writer):
    writer.begintag("div", c_l_a_s_s="metadataElement")
    # tag
    writer.begintag("h5", c_l_a_s_s="metadata")
    writer.write(element.tag)
    writer.endtag("h5")
    # attributes
    if len(element.attrib):
        writer.begintag("h6", c_l_a_s_s="metadata")
        writer.write("Attributes:")
        writer.endtag("h6")
        # key, value pairs
        writer.begintag("table", c_l_a_s_s="metadata")
        for key, value in sorted(element.attrib.items()):
            writer.begintag("tr")
            writer.begintag("td", c_l_a_s_s="key")
            writer.write(key)
            writer.endtag("td")
            writer.begintag("td", c_l_a_s_s="value")
            writer.write(value)
            writer.endtag("td")
            writer.endtag("tr")
        writer.endtag("table")
    # text
    if element.text is not None and element.text.strip():
        writer.begintag("h6", c_l_a_s_s="metadata")
        writer.write("Text:")
        writer.endtag("h6")
        writer.begintag("p", c_l_a_s_s="metadata")
        writer.write(element.text)
        writer.endtag("p")
    # child elements
    if len(element):
        writer.begintag("h6", c_l_a_s_s="metadata")
        writer.write("Child Elements:")
        writer.endtag("h6")
        for child in element:
            writeMetadataElement(child, writer)
    # close
    writer.endtag("div")

hexFilter = "".join([(len(repr(chr(x))) == 3) and chr(x) or "." for x in range(256)])

def writePrivateData(font, writer):
    # start the block
    writer.begintag("div", c_l_a_s_s="infoBlock")
    # title
    writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
    writer.write("Private Data")
    writer.endtag("h3")
    # content
    if font.privateData:
        # adapted from http://code.activestate.com/recipes/142812/
        src = font.privateData
        length = 16
        result = []
        for i in xrange(0, len(src), length):
            s = src[i:i+length]
            hexa = []
            c = []
            for x in s:
                x = "%02X" % ord(x)
                c.append(x)
                if len(c) == 4:
                    hexa.append("".join(c))
                    c = []
            if c:
                hexa.append("".join(c))
            hexa = " ".join(hexa)
            if len(hexa) != 35:
                hexa += " " * (35 - len(hexa))
            printable = s.translate(hexFilter)
            result.append("%04X %s %s\n" % (i, hexa, printable))
        privateData = "".join(result)
        writer.begintag("pre", c_l_a_s_s="privateData")
        writer.write(privateData)
        writer.endtag("pre")
    # close the block
    writer.endtag("div")

def writeFontFaceRule(font, fontPath, writer):
    # start the block
    writer.begintag("div", c_l_a_s_s="infoBlock")
    # title
    writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
    writer.write("@font-face")
    writer.endtag("h3")
    # the text
    fontFaceRule = makeFontFaceRule(font, fontPath, doLocalSrc=False)
    writer.begintag("pre", c_l_a_s_s="fontFaceRule")
    writer.write(fontFaceRule)
    writer.endtag("pre")
    # close the container
    writer.endtag("div")

# ---------------
# Public Function
# ---------------

def reportInfo(font, fontPath):
    """
    Create a report about the contents of font. This returns HTML.

    Arguments

    **font** - A *WOFFFont* object from *woffLib*.
    **fontPath** - The location of the font file. At the least, this should be the file name for the font.
    """
    # start the html
    title = "Info: %s" % os.path.basename(fontPath)
    writer = startHTML(title=title)
    # file info
    writeFileInfo(font, fontPath, writer)
    # SFNT tables
    writeSFNTInfo(font, writer)
    # metadata
    writeMetadata(font, writer)
    # private data
    writePrivateData(font, writer)
    # @font-face
    writeFontFaceRule(font, fontPath, writer)
    # finish the html
    text = finishHTML(writer)
    # return
    return text

# --------------------
# Command Line Behvior
# --------------------

usage = "%prog [options] fontpath1 fontpath2"

description = """This tool displays information about the
contents of one or more WOFF files.
"""

def main():
    parser = optparse.OptionParser(usage=usage, description=description, version="%prog 0.1beta")
    parser.add_option("-d", dest="outputDirectory", help="Output directory. The default is to output the report into the same directory as the font file.")
    parser.add_option("-o", dest="outputFileName", help="Output file name. The default is \"fontfilename_info.html\".")
    parser.set_defaults(excludeTests=[])
    (options, args) = parser.parse_args()
    outputDirectory = options.outputDirectory
    if outputDirectory is not None and not os.path.exists(outputDirectory):
        print("Directory does not exist: %s" % outputDirectory)
        sys.exit()
    for fontPath in args:
        if not os.path.exists(fontPath):
            print("File does not exist: %s" % fontPath)
            sys.exit()
        else:
            print("Creating Info Report: %s..." % fontPath)
            fontPath = fontPath.decode("utf-8")
            font = WOFFFont(fontPath)
            html = reportInfo(font, fontPath)
            # make the output file name
            if options.outputFileName is not None:
                fileName = options.outputFileName
            else:
                fileName = os.path.splitext(os.path.basename(fontPath))[0]
                fileName += "_info.html"
            # make the output directory
            if options.outputDirectory is not None:
                directory = options.outputDirectory
            else:
                directory = os.path.dirname(fontPath)
            # write the file
            path = os.path.join(directory, fileName)
            path = findUniqueFileName(path)
            f = open(path, "wb")
            f.write(html)
            f.close()

if __name__ == "__main__":
    main()
