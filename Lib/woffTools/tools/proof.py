"""
A module for automatically creating simple proof files from
WOFF files. *proofFont* is the only public function.

This can also be used as a command line tool for generating
proofs from WOFF files.
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
    print "Could not import needed module(s):", ", ".join(importErrors)
    sys.exit()

# import

import os
import optparse
import unicodedata
from woffTools import WOFFFont
from woffTools.tools.css import makeFontFaceRule, makeFontFaceFontFamily
from woffTools.tools.support import startHTML, finishHTML, findUniqueFileName


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
    writeFileInfoRow("VERSION", "%d.%d" % (font.majorVersion, font.minorVersion), writer)
    writer.endtag("table")
    # close the container
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

def writeCharacterSet(font, writer, pointSizes=[9, 10, 11, 12, 14, 18, 24, 36, 48, 72], sampleText=None):
    characterSet = makeCharacterSet(font)
    for size in pointSizes:
        # start the block
        writer.begintag("div", c_l_a_s_s="infoBlock")
        # title
        writer.begintag("h4", c_l_a_s_s="infoBlockTitle")
        writer.write("%dpx" % size)
        writer.endtag("h4")
        # character set
        writer.begintag("p", style="font-size: %dpx;" % size, c_l_a_s_s="characterSet")
        writer.write(characterSet)
        writer.endtag("p")
        # sample text
        if sampleText:
            writer.begintag("p", style="font-size: %dpx;" % size, c_l_a_s_s="sampleText")
            writer.write(sampleText)
            writer.endtag("p")
        # close the container
        writer.endtag("div")

# -------------
# Character Set
# -------------

def makeCharacterSet(font):
    cmap = font["cmap"]
    table = cmap.getcmap(3, 1)
    mapping = table.cmap
    categorizedCharacters = {}
    glyphNameToCharacter = {}
    for value, glyphName in sorted(mapping.items()):
        character = unichr(value)
        # skip whitespace
        if not character.strip():
            continue
        if glyphName not in glyphNameToCharacter:
            glyphNameToCharacter[glyphName] = []
        glyphNameToCharacter[glyphName].append(character)
    # use the glyph order defined in the font
    sortedCharacters = []
    for glyphName in font.getGlyphOrder():
        if glyphName in glyphNameToCharacter:
            sortedCharacters += glyphNameToCharacter[glyphName]
    return u"".join(sortedCharacters)

# ---------------
# Public Function
# ---------------

def proofFont(font, fontPath, sampleText=None):
    """
    Create a proof file from the given font. This always
    returns HTML.

    Arguments:
    **font** - A *WOFFFont* object from *woffLib*.
    **fontPath** - The location of the font file. At the least, this should be the file name for the font.
    **sampleText** - A string of text to display. If not provided, no text will be displayed.
    """
    # start the html
    title = "Proof: %s" % os.path.basename(fontPath)
    cssReplacements = {
        "/* proof: @font-face rule */" : makeFontFaceRule(font, fontPath, doLocalSrc=False),
        "/* proof: @font-face font-family */" : makeFontFaceFontFamily(font)
    }
    writer = startHTML(title=title, cssReplacements=cssReplacements)
    # file info
    writeFileInfo(font, fontPath, writer)
    # character set
    writeCharacterSet(font, writer, sampleText=sampleText)
    # finish the html
    text = finishHTML(writer)
    text = text.replace("%%break%%", "</br>")
    # return
    return text

# --------------------
# Command Line Behvior
# --------------------

usage = "%prog [options] fontpath1 fontpath2"

description = """This tool displays information about the
contents of one or more WOFF files.
"""

defaultSampleText = "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG. The quick brown fox jumps over the lazy dog."

def main():
    parser = optparse.OptionParser(usage=usage, description=description, version="%prog 0.1beta")
    parser.add_option("-d", dest="outputDirectory", help="Output directory. The default is to output the proof into the same directory as the font file.")
    parser.add_option("-o", dest="outputFileName", help="Output file name. The default is \"fontfilename_proof.html\".")
    parser.add_option("-t", dest="sampleTextFile", help="Sample text file. A file containing sample text to display. If not file is provided, The quick brown fox... will be used.")
    parser.set_defaults(excludeTests=[])
    (options, args) = parser.parse_args()
    outputDirectory = options.outputDirectory
    if outputDirectory is not None and not os.path.exists(outputDirectory):
        print "Directory does not exist:", outputDirectory
        sys.exit()
    sampleText = defaultSampleText
    if options.sampleTextFile:
        if not os.path.exists(options.sampleTextFile):
            print "Sample text file does not exist:", options.sampleTextFile
            sys.exit()
        f = open(options.sampleTextFile, "r")
        sampleText = f.read()
        f.close()
    for fontPath in args:
        if not os.path.exists(fontPath):
            print "File does not exist:", fontPath
            sys.exit()
        else:
            print "Creating Proof: %s..." % fontPath
            fontPath = fontPath.decode("utf-8")
            font = WOFFFont(fontPath)
            html = proofFont(font, fontPath, sampleText=sampleText)
            # make the output file name
            if options.outputFileName is not None:
                fileName = options.outputFileName
            else:
                fileName = os.path.splitext(os.path.basename(fontPath))[0]
                fileName += "_proof.html"
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
