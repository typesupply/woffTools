"""
A module for automatically creating CSS @font-face rules from
WOFF files. *makeFontFaceRule* is the only public function.

This can also be used as a command line tool for generating
CSS @font-face rules from WOFF files.
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
import urllib
import optparse
from woffTools import WOFFFont
from woffTools.tools.support import findUniqueFileName

# -----------
# Descriptors
# -----------

def makeFontFaceFontFamily(font):
    familyPriority = [
        (21, 1, 0, 0),          # WWS Family Name, Mac, English, Roman
        (21, 1, None, None),    # WWS Family Name, Mac, Any, Any
        (21, None, None, None), # WWS Family Name, Any, Any, Any
        (16, 1, 0, 0),          # Preferred Family, Mac, English, Roman
        (16, 1, None, None),    # Preferred Family, Mac, Any, Any
        (16, None, None, None), # Preferred Family, Any, Any, Any
        (1, 1, 0, 0),           # Font Family Name, Mac, English, Roman
        (1, 1, None, None),     # Font Family Name, Mac, Any, Any
        (1, None, None, None)   # Font Family Name, Any, Any, Any
    ]
    familyName = _skimNameIDs(font, familyPriority)
    descriptor = "font-family: \"%s\";" % familyName
    return descriptor

def makeFontFaceSrc(font, fileName, doLocalSrc=True):
    sources = []
    if doLocalSrc:
        # postscript name
        postscriptPriority = [
            (6, 1, 0, 0),           # Postscript Name, Mac, English, Roman
            (6, 1, None, None),     # Postscript Name, Mac, Any, Any
            (6, None, None, None),  # Postscript Name, Any, Any, Any
        ]
        postscriptName = _skimNameIDs(font, postscriptPriority)
        # full name
        fullNamePriority = [
            (4, 1, 0, 0),           # Full Font Name, Mac, English, Roman
            (4, 1, None, None),     # Full Font Name, Mac, Any, Any
            (4, None, None, None),  # Full Font Name, Any, Any, Any
        ]
        fullName = _skimNameIDs(font, fullNamePriority)
        # store
        s = "local(\"%s\")" % postscriptName
        sources.append(s)
        if postscriptName != fullName:
            s = "local(\"%s\")" % fullName
            sources.append(s)
    # file name
    s = "url(\"%s\")" % urllib.quote(fileName) # XXX:  format(\"woff\")
    sources.append(s)
    # write
    sources = "\n\t".join(sources)
    descriptor = "src: %s;" % sources
    return descriptor

def makeFontFaceFontWeight(font):
    os2 = font["OS/2"]
    value = os2.usWeightClass
    descriptor = "font-weight: %d;" % value
    if value < 100 or value > 900:
        descriptor += " /* ERROR! Weight value is out of the 100-900 value range. */"
    elif value % 100:
        descriptor += " /* ERROR! Weight value is not a multiple of 100. */"
    return descriptor

def makeFontFaceFontStretch(font):
    os2 = font["OS/2"]
    value = os2.usWidthClass
    options = "ultra-condensed extra-condensed condensed semi-condensed normal semi-expanded expanded extra-expanded ultra-expanded".split(" ")
    try:
        value = options[value-1]
    except IndexError:
        value = "normal; /* ERROR! The value in the OS/2 table usWidthClass is not valid! */"
    descriptor = "font-stretch: %s;" % value
    return descriptor

def makeFontFaceFontStyle(font):
    os2 = font["OS/2"]
    if os2.fsSelection & 1:
        value = "italic"
    else:
        value = "normal"
    descriptor = "font-style: %s;" % value
    return descriptor

def makeFontFaceUnicodeRange(font):
    # compile ranges
    cmap = font["cmap"]
    table = cmap.getcmap(3, 1)
    mapping = table.cmap
    ranges = []
    for value in sorted(mapping.keys()):
        newRanges = []
        handled = False
        for rangeMin, rangeMax in ranges:
            if value >= rangeMin and value <= rangeMax:
                handled = True
            elif rangeMin - 1 == value:
                rangeMin = value
                handled = True
            elif rangeMax + 1 == value:
                rangeMax = value
                handled = True
            newRanges.append((rangeMin, rangeMax))
        if not handled:
            newRanges.append((value, value))
        ranges = sorted(newRanges)
    # convert ints to proper hexk values
    formatted = []
    for minValue, maxValue in ranges:
        if minValue == maxValue:
            uniRange = hex(minValue)[2:].upper()
        else:
            minCode = hex(minValue)[2:].upper()
            maxCode = hex(maxValue)[2:].upper()
            uniRange = "-".join((minCode, maxCode))
        formatted.append("U+%s" % uniRange)
    # break into nice lines
    perLine = 4
    chunks = []
    while formatted:
        if len(formatted) > perLine:
            chunks.append(formatted[:perLine])
            formatted = formatted[perLine:]
        else:
            chunks.append(formatted)
            formatted = []
    formatted = []
    for index, chunk in enumerate(chunks):
        s = ", ".join(chunk)
        if index < len(chunks) - 1:
            s += ","
        formatted.append(s)
    formatted = "\n\t".join(formatted)
    # write
    descriptor = "unicode-range: %s;" % formatted
    return descriptor

# -------
# Helpers
# -------

def _skimNameIDs(font, priority):
    nameIDs = {}
    for nameRecord in font["name"].names:
        nameID = nameRecord.nameID
        platformID = nameRecord.platformID
        platEncID = nameRecord.platEncID
        langID = nameRecord.langID
        text = nameRecord.string
        nameIDs[nameID, platformID, platEncID, langID] = text
    for (nameID, platformID, platEncID, langID) in priority:
        for (nID, pID, pEID, lID), text in nameIDs.items():
            if nID != nameID:
                continue
            if pID != platformID and platformID is not None:
                continue
            if pEID != platEncID and platEncID is not None:
                continue
            if lID != langID and langID is not None:
                continue
            text = "".join([i for i in text if i != "\x00"])
            return text

# ---------------
# Public Function
# ---------------

def makeFontFaceRule(font, fontPath, doLocalSrc=True):
    """
    Create a CSS @font-face rule from the given font. This always
    returns the CSS text.

    Arguments

    **font** - A *WOFFFont* object from *woffLib*.
    **fontPath** - The location of the font file. At the least, this should be the file name for the font.
    **doLocalSrc** - Generate "local" references as part of the "src" descriptor.
    """
    # create text
    sections = [
        makeFontFaceFontFamily(font),
        makeFontFaceSrc(font, os.path.basename(fontPath), doLocalSrc=doLocalSrc),
        makeFontFaceFontWeight(font),
        makeFontFaceFontStretch(font),
        makeFontFaceFontStyle(font),
        makeFontFaceUnicodeRange(font)
    ]
    lines = []
    for section in sections:
        lines += ["\t" + line for line in section.splitlines()]
    rule = ["/* Automatically generated from: %s %d.%d */" % (os.path.basename(fontPath), font.majorVersion, font.minorVersion)]
    rule += [""]
    rule += ["@font-face {"] + lines + ["}"]
    rule = "\n".join(rule)
    return rule

# --------------------
# Command Line Behvior
# --------------------

usage = "%prog [options] fontpath1 fontpath2"

description = """This tool examines the contents of a WOFF
file and attempts to generate a CSS @font-face rule based
on the data found in the WOFF file. The results of this
tool should always be carefully checked.
"""

def main():
    parser = optparse.OptionParser(usage=usage, description=description, version="%prog 0.1beta")
    parser.add_option("-d", dest="outputDirectory", help="Output directory. The default is to output the CSS into the same directory as the font file.")
    parser.add_option("-o", dest="outputFileName", help="Output file name. The default is \"fontfilename.css\". If this file already exists a time stamp will be added to the file name.")
    parser.add_option("-l", action="store_true", dest="skipLocalSrc", help="Skip \"local\" instructions as part of the \"src\" descriptor.")
    (options, args) = parser.parse_args()
    outputDirectory = options.outputDirectory
    if outputDirectory is not None and not os.path.exists(outputDirectory):
        print "Directory does not exist:", outputDirectory
        sys.exit()
    for fontPath in args:
        if not os.path.exists(fontPath):
            print "File does not exist:", fontPath
            sys.exit()
        else:
            print "Creating CSS: %s..." % fontPath
            font = WOFFFont(fontPath)
            css = makeFontFaceRule(font, fontPath, doLocalSrc=not options.skipLocalSrc)
            # make the output file name
            if options.outputFileName is not None:
                fileName = options.outputFileName
            else:
                fileName = os.path.splitext(os.path.basename(fontPath))[0]
                fileName += ".css"
            # make the output directory
            if options.outputDirectory is not None:
                directory = options.outputDirectory
            else:
                directory = os.path.dirname(fontPath)
            # write the file
            path = os.path.join(directory, fileName)
            path = findUniqueFileName(path)
            f = open(path, "wb")
            f.write(css)
            f.close()

if __name__ == "__main__":
    main()
