"""
A module for validating the the file structure of WOFF Files.
*validateFont* is the only public function.

This can also be used as a command line tool for validating WOFF files.
"""

"""
TO DO:
- split length and offset tests into smaller functions that can be more easily doctested
- test for proper ordering of table data, metadata, private data
- test metadata extension element
- test for gaps in table data
- test for overlapping tables
- the checksum calculation uses the function sin FontTools. those seem to be incorrect.
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
import sys
import struct
import zlib
import optparse
import numpy
import sstruct
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError
from fontTools.ttLib.sfnt import getSearchRange, SFNTDirectoryEntry, \
    sfntDirectoryFormat, sfntDirectorySize, sfntDirectoryEntryFormat, sfntDirectoryEntrySize
from woffTools.tools.support import startHTML, finishHTML, findUniqueFileName

# ------
# Header
# ------

headerFormat = """
    > # big endian
    signature:      4s
    flavor:         4s
    length:         L
    numTables:      H
    reserved:       H
    totalSfntSize:  L
    majorVersion:   H
    minorVersion:   H
    metaOffset:     L
    metaLength:     L
    metaOrigLength: L
    privOffset:     L
    privLength:     L
"""
headerSize = sstruct.calcsize(headerFormat)

def testHeaderSize(data, reporter):
    """
    Tests:
    - length of file is long enough to contain header.
    """
    if len(data) < headerSize:
        reporter.logError(message="The header is not the proper length.")
        return True
    else:
        reporter.logPass(message="The header length is correct.")

def testHeaderStructure(data, reporter):
    """
    Tests:
    - header structure by trying to unpack header.
    """
    try:
        sstruct.unpack2(headerFormat, data)
        reporter.logPass(message="The header structure is correct.")
    except:
        reporter.logError(message="The header is not properly structured.")
        return True

def testHeaderSignature(data, reporter):
    """
    Tests:
    - signature is "wOFF"
    """
    header = unpackHeader(data)
    signature = header["signature"]
    if signature != "wOFF":
        reporter.logError(message="Invalid signature: %s." % signature)
        return True
    else:
        reporter.logPass(message="The signature is correct.")

def testHeaderFlavor(data, reporter):
    """
    Tests:
    - flavor is OTTO, 0x00010000 or true.
    - if flavor is OTTO, CFF is present.
    - if flavor is not OTTO, CFF is not present.
    - flavor could not be validated because the directory could not be unpacked.
    """
    header = unpackHeader(data)
    flavor = header["flavor"]
    if flavor not in ("OTTO", "\000\001\000\000", "true"):
        reporter.logError(message="Unknown flavor: %s." % flavor)
    else:
        try:
            tags = [table["tag"] for table in unpackDirectory(data)]
            if "CFF " in tags and flavor != "OTTO":
                reporter.logError(message="A \"CFF\" table is defined in the font and the flavor is not set to \"OTTO\".")
            elif "CFF " not in tags and flavor == "OTTO":
                reporter.logError(message="The flavor is set to \"OTTO\" but no \"CFF\" table is defined.")
            else:
                reporter.logPass(message="The flavor is a correct value.")
        except:
            reporter.logWarning(message="Could not validate the flavor.")

def testHeaderLength(data, reporter):
    """
    Tests:
    - length of data matches defined length.
    - length of data is long enough for header and directory for defined number of tables.
    - length of data is long enough to contain table lengths defined in the directory,
      metaLength and privLength.
    """
    header = unpackHeader(data)
    length = header["length"]
    numTables = header["numTables"]
    minLength = headerSize + (directorySize * numTables)
    if length != len(data):
        reporter.logError(message="Defined length (%d) does not match actual length of the data (%d)." % (length, len(data)))
        return True
    if length < minLength:
        reporter.logError(message="Invalid length defined (%d) for number of tables defined." % length)
        return True
    directory = unpackDirectory(data)
    for entry in directory:
        compLength = entry["compLength"]
        if compLength % 4:
            compLength += 4 - (compLength % 4)
        minLength += compLength
    metaLength = header["metaLength"]
    privLength = header["privLength"]
    if privLength and metaLength % 4:
        metaLength += 4 - (metaLength % 4)
    minLength += metaLength + privLength
    if length < minLength:
        reporter.logError(message="Defined length (%d) does not match the required length of the data (%d)." % (length, minLength))
        return True
    reporter.logPass(message="The length defined in the header is correct.")

def testHeaderReserved(data, reporter):
    """
    Tests:
    - reserved is 0
    """
    header = unpackHeader(data)
    reserved = header["reserved"]
    if reserved != 0:
        reporter.logError(message="Invalid value in reserved field (%d)." % reserved)
        return True
    else:
        reporter.logPass(message="The value in the reserved field is correct.")

def testHeaderTotalSFNTSize(data, reporter):
    """
    Tests:
    - origLength values in the directory, with proper padding,
      sum to the totalSfntSize in the header.
    """
    header = unpackHeader(data)
    directory = unpackDirectory(data)
    totalSfntSize = header["totalSfntSize"]
    numTables = header["numTables"]
    requiredSize = sfntDirectorySize + (numTables * sfntDirectoryEntrySize)
    for table in directory:
        origLength = table["origLength"]
        if origLength % 4:
            origLength += 4 - (origLength % 4)
        requiredSize += origLength
    if totalSfntSize != requiredSize:
        reporter.logError(message="The total sfnt size (%d) does not match the required sfnt size (%d)." % (totalSfntSize, requiredSize))
    else:
        reporter.logPass(message="The total sfnt size is valid.")

def testHeaderMajorVersionAndMinorVersion(data, reporter):
    """
    Tests:
    - major version + minor version > 1.0
    """
    header = unpackHeader(data)
    majorVersion = header["majorVersion"]
    minorVersion = header["minorVersion"]
    version = "%d.%d" % (majorVersion, minorVersion)
    if float(version) < 1.0:
        reporter.logWarning(message="The major version (%d) and minor version (%d) create a version (%s) less than 1.0." % (majorVersion, minorVersion, version))
    else:
        reporter.logPass(message="The major version and minor version are valid numbers.")


# ---------------
# Table Directory
# ---------------

directoryFormat = """
    > # big endian
    tag:            4s
    offset:         L
    compLength:     L
    origLength:     L
    origChecksum:   L
"""
directorySize = sstruct.calcsize(directoryFormat)

def testHeaderNumTables(data, reporter):
    """
    Tests:
    - numTables in header is at least 1.
    - the number of tables defined in the header can be successfully unpacked.
    """
    header = unpackHeader(data)
    numTables = header["numTables"]
    if numTables < 1:
        reporter.logError(message="Invalid number of tables defined in header structure (%d)." % numTables)
        return True
    data = data[headerSize:]
    for index in range(numTables):
        try:
            d, data = sstruct.unpack2(directoryFormat, data)
        except:
            reporter.logError(message="The defined number of tables in the header (%d) does not match the actual number of tables (%d)." % (numTables, index))
            return True
    reporter.logPass(message="The number of tables defined in the header is valid.")

def testDirectoryTableOrder(data, reporter):
    """
    Tests:
    - directory in ascending order based on tag.
    """
    storedOrder = [table["tag"] for table in unpackDirectory(data)]
    if storedOrder != sorted(storedOrder):
        reporter.logError(message="The table directory entries are not stored in alphabetical order.")
    else:
        reporter.logPass(message="The table directory entries are stored in the proper order.")

def testDirectoryBorders(data, reporter):
    """
    Tests:
    - table offset is before the end of the header/directory.
    - table offset is after the end of the file.
    - table offset + length is greater than the available length.
    - table length is longer than the available length.
    """
    header = unpackHeader(data)
    totalLength = header["length"]
    numTables = header["numTables"]
    minOffset = headerSize + (directorySize * numTables)
    maxLength = totalLength - minOffset
    directory = unpackDirectory(data)
    shouldStop = False
    for table in directory:
        tag = table["tag"]
        offset = table["offset"]
        length = table["compLength"]
        offsetErrorMessage = "The \"%s\" table directory entry has an invalid offset (%d)." % (tag, offset)
        lengthErrorMessage = "The \"%s\" table directory entry has an invalid length (%d)." % (tag, length)
        haveError = False
        if offset < minOffset:
            reporter.logError(message=offsetErrorMessage)
            haveError = True
        elif offset > totalLength:
            reporter.logError(message=offsetErrorMessage)
            haveError = True
        elif (offset + length) > totalLength:
            reporter.logError(message=lengthErrorMessage)
            haveError = True
        elif length > maxLength:
            reporter.logError(message=lengthErrorMessage)
            haveError = True
        if haveError:
            shouldStop = True
        else:
            reporter.logPass(message="The \"%s\" table directory entry has a valid offset and length." % tag)
    if shouldStop:
        return True

def testDirectoryCompressedLength(data, reporter):
    """
    Tests:
    - compLength must be less than or equal to origLength
    """
    directory = unpackDirectory(data)
    for table in directory:
        tag = table["tag"]
        compLength = table["compLength"]
        origLength = table["origLength"]
        if compLength > origLength:
            reporter.logError(message="The \"%s\" table directory entry has an compressed length (%d) lager than the original length (%d)." % (tag, compLength, origLength))
        else:
            reporter.logPass(message="The \"%s\" table directory entry has proper compLength and origLength values." % tag)

def testDirectoryDecompressedLength(data, reporter):
    """
    Tests:
    - decompressed length matches origLength
    """
    directory = unpackDirectory(data)
    tableData = unpackTableData(data)
    for table in directory:
        tag = table["tag"]
        offset = table["offset"]
        compLength = table["compLength"]
        origLength = table["origLength"]
        if compLength >= origLength:
            continue
        decompressedData = tableData[tag]
        decompressedLength = len(decompressedData)
        if origLength != decompressedLength:
            reporter.logError(message="The \"%s\" table directory entry has an original length (%d) that does not match the actual length of the decompressed data (%d)." % (tag, origLength, decompressedLength))
        else:
            reporter.logPass(message="The \"%s\" table directory entry has a proper original length compared to the actual decompressed data." % tag)

def testDirectoryChecksums(data, reporter):
    """
    Tests:
    - checksum for table data, decompressed if necessary, matched
      the checkSum defined in the directory entry.
    """
    directory = unpackDirectory(data)
    tables = unpackTableData(data)
    for entry in directory:
        tag = entry["tag"]
        origChecksum = entry["origChecksum"]
        newChecksum = calcChecksum(tag, tables[tag])
        if newChecksum != origChecksum:
            reporter.logError(message="The \"%s\" table directory entry original checksum (%s) does not match the checksum (%s) calculated from the data." % (tag, hex(origChecksum), hex(newChecksum)))
        else:
            reporter.logPass(message="The \"%s\" table directory entry original checksum is correct." % tag)


# ------
# Tables
# ------

def testTableDataStart(data, reporter):
    """
    Tests:
    - table data starts immediately after the directory.
    """
    header = unpackHeader(data)
    directory = unpackDirectory(data)
    requiredStart = headerSize + (directorySize * header["numTables"])
    offsets = [entry["offset"] for entry in directory]
    start = min(offsets)
    if requiredStart != start:
        reporter.logError(message="The table data does not start (%d) in the required position (%d)." % (start, requiredStart))
    else:
        reporter.logPass(message="The table data begins in the proper position.")

def testTablePadding(data, reporter):
    """
    Tests:
    - table offsets are on four byte boundaries
    - final table ends on a four byte boundary.
        - if metadata or private data is present, use first offset.
        - if no metadata or pivate data is present, use end of file.
    """
    header = unpackHeader(data)
    directory = unpackDirectory(data)
    # test offset positions
    for table in directory:
        tag = table["tag"]
        offset = table["offset"]
        if offset % 4:
            reporter.logError(message="The \"%s\" table does not begin on a 4-byte boundary." % tag)
        else:
            reporter.logPass(message="The \"%s\" table begins on a proper 4-byte boundary." % tag)
    # test final table
    endError = False
    if header["metaOffset"] == 0 and header["privOffset"] == 0:
        if header["length"] % 4:
            endError = True
    else:
        if header["metaOffset"] != 0:
            sfntEnd = header["metaOffset"]
        else:
            sfntEnd = header["privOffset"]
        if sfntEnd % 4:
            endError = True
    if endError:
        reporter.logError(message="The sfnt data does not end with proper padding.")
    else:
        reporter.logPass(message="The sfnt data ends with proper padding.")

def testTableDecompression(data, reporter):
    """
    Tests:
    - the data for entries where compLength < origLength can be successfully decompressed.
    """
    shouldStop = False
    for table in unpackDirectory(data):
        tag = table["tag"]
        offset = table["offset"]
        compLength = table["compLength"]
        origLength = table["origLength"]
        if origLength <= compLength:
            continue
        entryData = data[offset:offset+compLength]
        try:
            decompressed = zlib.decompress(entryData)
            reporter.logPass(message="The \"%s\" table data can be decompressed with zlib." % tag)
        except zlib.error:
            shouldStop = True
            reporter.logError(message="The \"%s\" table data can not be decompressed with zlib." % tag)
    return shouldStop

def testHeadCheckSumAdjustment(data, reporter):
    """
    Tests:
    - Missing head table.
    - head table with a structure that can not be parsed.
    - head checkSumAdjustment that does not match the computed value for the sfnt data.
    """
    tables = unpackTableData(data)
    if "head" not in tables:
        reporter.logWarning(message="The font does not contain a \"head\" table.")
        return
    newChecksum = calcHeadCheckSum(data)
    data = tables["head"]
    try:
        format = ">l"
        checksum = struct.unpack(format, data[8:12])[0]
        if checksum != newChecksum:
            reporter.logError(message="The \"head\" table checkSumAdjustment (%s) does not match the calculated checkSumAdjustment (%s)." % (hex(checksum), hex(newChecksum)))
        else:
            reporter.logPass(message="The \"head\" table checkSumAdjustment is valid.")
    except:
        reporter.logError(message="The \"head\" table is not properly structured.")

def testDSIG(data, reporter):
    """
    Tests:
    - warn if DSIG is present
    """
    directory = unpackDirectory(data)
    for entry in directory:
        if entry["tag"] == "DSIG":
            reporter.logWarning(
                message="The font contains a \"DSIG\" table. This can not be validated by this tool.",
                information="If you need this functionality, contact the developer of this tool.")
            return
    reporter.logNote(message="The font does not contain a \"DSIG\" table.")


# --------
# Metadata
# --------

def shouldSkipMetadataTest(data, reporter):
    """
    This is used at the start of metadata test functions.
    It writes a note and returns True if not metadata exists.
    """
    header = unpackHeader(data)
    metaOffset = header["metaOffset"]
    metaLength = header["metaLength"]
    if metaOffset == 0 or metaLength == 0:
        reporter.logNote(message="No metadata to test.")
        return True

def testMetadataOffsetAndLength(data, reporter):
    """
    Tests:
    - if offset is zero, length is 0. vice-versa.
    - offset is before the end of the header/directory.
    - offset is after the end of the file.
    - offset + length is greater than the available length.
    - length is longer than the available length.
    - offset begins immediately after last table.
    - offset begins on 4-byte boundary.
    """
    header = unpackHeader(data)
    metaOffset = header["metaOffset"]
    metaLength = header["metaLength"]
    # empty offset or length
    if metaOffset == 0 or metaLength == 0:
        if metaOffset == 0 and metaLength == 0:
            reporter.logPass(message="The length and offset are appropriately set for empty metadata.")
        else:
            reporter.logError(message="The metadata offset (%d) and metadata length (%d) are not properly set. If one is 0, they both must be 0." % (metaOffset, metaLength))
        return
    # 4-byte boundary
    if metaOffset % 4:
        reporter.logError(message="The metadata does not begin on a four-byte boundary.")
        return
    # borders
    totalLength = header["length"]
    numTables = header["numTables"]
    directory = unpackDirectory(data)
    offsets = [headerSize + (directorySize * numTables)]
    for table in directory:
        tag = table["tag"]
        offset = table["offset"]
        length = table["compLength"]
        offsets.append(offset + length)
    minOffset = max(offsets)
    if minOffset % 4:
        minOffset += 4 - (minOffset % 4)
    maxLength = totalLength - minOffset
    offsetErrorMessage = "The metadata has an invalid offset (%d)." % metaOffset
    lengthErrorMessage = "The metadata has an invalid length (%d)." % metaLength
    if metaOffset < minOffset:
        reporter.logError(message=offsetErrorMessage)
    elif metaOffset > totalLength:
        reporter.logError(message=offsetErrorMessage)
    elif (metaOffset + metaLength) > totalLength:
        reporter.logError(message=lengthErrorMessage)
    elif metaLength > maxLength:
        reporter.logError(message=lengthErrorMessage)
    elif metaOffset != minOffset:
        reporter.logError(message=offsetErrorMessage)
    else:
        reporter.logPass(message="The metadata has properly set offset and length.")

def testMetadataDecompression(data, reporter):
    """
    Tests:
    - metadata can be decompressed with zlib.
    """
    if shouldSkipMetadataTest(data, reporter):
        return
    compData = unpackMetadata(data, decompress=False, parse=False)
    try:
        zlib.decompress(compData)
    except zlib.error:
        reporter.logError(message="The metdata can not be decompressed with zlib.")
        return True
    reporter.logPass(message="The metadata can be decompressed with zlib.")

def testMetadataDecompressedLength(data, reporter):
    """
    Tests:
    - decompressed metadata length matches metaOrigLength
    """
    if shouldSkipMetadataTest(data, reporter):
        return
    header = unpackHeader(data)
    metadata = unpackMetadata(data, parse=False)
    metaOrigLength = header["metaOrigLength"]
    decompressedLength = len(metadata)
    if metaOrigLength != decompressedLength:
        reporter.logError(message="The decompressed metadata length (%d) does not match the original metadata length (%d) in the header." % (decompressedLength, metaOrigLength))
    else:
        reporter.logPass(message="The decompressed metadata length matches the original metadata length in the header.")

def testMetadataParse(data, reporter):
    """
    Tests:
    - metadata can be parsed
    """
    if shouldSkipMetadataTest(data, reporter):
        return
    metadata = unpackMetadata(data, parse=False)
    try:
        tree = ElementTree.fromstring(metadata)
    except ExpatError:
        reporter.logError(message="The metadata can not be parsed.")
        return True
    reporter.logPass(message="The metadata can be parsed.")

def testMetadataStructure(data, reporter):
    """
    Refer to lower level tests.
    """
    if shouldSkipMetadataTest(data, reporter):
        return
    tree = unpackMetadata(data)
    testMetadataStructureTopElement(tree, reporter)
    testMetadataChildElements(tree, reporter)

def testMetadataStructureTopElement(tree, reporter):
    """
    Tests:
    - metadata is top element
    - version is only attribute of top element
    - version is 1.0
    - text in element
    """
    haveError = False
    # metadata as top element
    if tree.tag != "metadata":
        reporter.logError("The top element is not \"metadata\".")
        haveError = True
    # version as only attribute
    if tree.attrib.keys() != ["version"]:
        for key in sorted(tree.attrib.keys()):
            if key != "version":
                reporter.logError("Unknown \"%s\" attribute in \"metadata\" element." % key)
                haveError = True
    if "version" not in tree.attrib:
        reporter.logError("The \"version\" attribute is not defined in \"metadata\" element.")
        haveError = True
    else:
        # version is 1.0
        version = tree.attrib["version"]
        if version != "1.0":
            reporter.logError("Invalid value (%s) for \"version\" attribute in \"metadata\" element." % version)
            haveError = True
    # text in element
    if tree.text is not None and tree.text.strip():
        reporter.logError("Text defined in \"metadata\" element.")
        haveError = True
    if not haveError:
        reporter.logPass("The \"metadata\" element is properly formatted.")

def testMetadataChildElements(tree, reporter):
    """
    Tests:
    - uniqueid is present (warn)
    - unknown element tags (warn)
    - known tags are shuttled off to element specific functions
    """
    # look for known elements
    testMetadataElementExistence(tree, reporter)
    # look for duplicate elements
    testMetadataDuplicateElements(tree, reporter)
    # push elements to the appropriate functions
    optionalElements = "vendor credits description license copyright trademark licensee".split(" ")
    optionalElements = dict.fromkeys(optionalElements, 0)
    for element in tree:
        if element.tag == "uniqueid":
            testMetadataUniqueid(element, reporter)
        elif element.tag == "vendor":
            testMetadataVendor(element, reporter)
        elif element.tag == "credits":
            testMetadataCredits(element, reporter)
        elif element.tag == "description":
            testMetadataDescription(element, reporter)
        elif element.tag == "license":
            testMetadataLicense(element, reporter)
        elif element.tag == "copyright":
            testMetadataCopyright(element, reporter)
        elif element.tag == "trademark":
            testMetadataTrademark(element, reporter)
        elif element.tag == "licensee":
            testMetadataLicensee(element, reporter)
        else:
            reporter.logWarning(
                message="Unknown \"%s\" element." % element.tag,
                information="This element will be unknown to user agents.")

def testMetadataElementExistence(tree, reporter):
    """
    Warn/note missing elements.
    """
    foundUniqueid = False
    tags = "uniqueid vendor credits description license copyright trademark licensee".split(" ")
    tags = dict.fromkeys(tags, 0)
    for element in tree:
        if element.tag not in tags:
            continue
        tags[element.tag] += 1
    # unique id should get a warning
    if not tags.pop("uniqueid"):
        reporter.logWarning(message="No \"uniqueid\" child is in the \"metadata\" element.")
    # others get a note
    for tag, count in sorted(tags.items()):
        if count == 0:
            reporter.logNote(message="No \"%s\" child is in the \"metadata\" element." % tag)

def testMetadataDuplicateElements(tree, reporter):
    """
    Look for duplicated, known element tags.
    """
    tags = "uniqueid vendor credits description license copyright trademark licensee".split(" ")
    tags = dict.fromkeys(tags, 0)
    for element in tree:
        if element.tag in tags:
            tags[element.tag] += 1
    for tag, count in sorted(tags.items()):
        if count > 1:
            reporter.logWarning(message="The \"%s\" tag is used more than once in the \"metadata\" element." % tag)

def testMetadataUniqueid(element, reporter):
    """
    Tests:
    - id is present and contains text
    - unknown attributes
    - child-elements
    """
    required = "id".split(" ")
    haveError = testMetadataAbstractElement(element, reporter, tag="uniqueid", requiredAttributes=required)
    if not haveError:
        reporter.logPass(message="The \"uniqueid\" element is properly formatted.")

def testMetadataVendor(element, reporter):
    """
    Tests:
    - name is present and contains text
    - url is not present (note)
    - url is not empty
    - unknown attributes
    - child-elements
    """
    required = "name".split(" ")
    optional = "url".split(" ")
    haveError = testMetadataAbstractElement(element, reporter, tag="vendor", requiredAttributes=required, optionalAttributes=optional)
    if not haveError:
        reporter.logPass(message="The \"vendor\" element is properly formatted.")

def testMetadataCredits(element, reporter):
    """
    Tests:
    - no attributes
    - text
    - has at least one child element
    - unknown child elements
    """
    haveError = True
    if testMetadataAbstractElement(element, reporter, tag="vendor", knownChildElements=["credit"]):
        haveError = True
    if not haveError:
        reporter.logPass(message="The \"credits\" element is properly formatted.")
    # test credit child elements
    for child in element:
        if child.tag == "credit":
            testMetadataCredit(child, reporter)

def testMetadataCredit(element, reporter):
    """
    Tests:
    - name is present and contains text
    - url is not present (note)
    - url is not empty
    - role is not present (note)
    - role is not empty
    - unknown attributes
    - child-elements
    """
    required = "name".split(" ")
    optional = "url role".split(" ")
    haveError = testMetadataAbstractElement(element, reporter, tag="credit", requiredAttributes=required, optionalAttributes=optional)
    if not haveError:
        reporter.logPass(message="The \"credit\" element is properly formatted.")

def testMetadataDescription(element, reporter):
    """
    Tests:
    - no attributes
    - no text
    - has at least one text child element
    - unknown child elements
    - text element validity
    - duplicate languages
    """
    haveError = False
    if testMetadataAbstractElement(element, reporter, tag="description", knownChildElements=["text"], missingChildElementsAlertLevel="warning"):
        haveError = True
    # validate the text elements
    if testMetadataAbstractTextElements(element, reporter, "description"):
        haveError = True
    # test for duplicate text elements
    if testMetadataAbstractTextElementLanguages(element, reporter, "description"):
        haveError = True
    # test for text element compliance
    if not haveError:
        reporter.logPass(message="The \"description\" element is properly formatted.")

def testMetadataLicense(element, reporter):
    """
    Tests:
    - optional attributes
    - no unknown attributes
    - no text
    - has at least one text child element (warn)
    - unknown child elements
    - text element validity
    - duplicate languages
    """
    optional = "url id".split(" ")
    haveError = False
    if testMetadataAbstractElement(element, reporter, tag="license", optionalAttributes=optional, knownChildElements=["text"], missingChildElementsAlertLevel="warning"):
        haveError = True
    # validate the text elements
    if testMetadataAbstractTextElements(element, reporter, "license"):
        haveError = True
    # test for duplicate text elements
    if testMetadataAbstractTextElementLanguages(element, reporter, "license"):
        haveError = True
    # test for text element compliance
    if not haveError:
        reporter.logPass(message="The \"license\" element is properly formatted.")

def testMetadataCopyright(element, reporter):
    """
    Tests:
    - no attributes
    - no text
    - has at least one text child element
    - unknown child elements
    - text element validity
    - duplicate languages
    """
    haveError = False
    if testMetadataAbstractElement(element, reporter, tag="copyright", knownChildElements=["text"], missingChildElementsAlertLevel="warning"):
        haveError = True
    # validate the text elements
    if testMetadataAbstractTextElements(element, reporter, "copyright"):
        haveError = True
    # test for duplicate text elements
    if testMetadataAbstractTextElementLanguages(element, reporter, "copyright"):
        haveError = True
    # test for text element compliance
    if not haveError:
        reporter.logPass(message="The \"copyright\" element is properly formatted.")

def testMetadataTrademark(element, reporter):
    """
    Tests:
    - no attributes
    - no text
    - has at least one text child element
    - unknown child elements
    - text element validity
    - duplicate languages
    """
    haveError = False
    if testMetadataAbstractElement(element, reporter, tag="trademark", knownChildElements=["text"], missingChildElementsAlertLevel="warning"):
        haveError = True
    # validate the text elements
    if testMetadataAbstractTextElements(element, reporter, "trademark"):
        haveError = True
    # test for duplicate text elements
    if testMetadataAbstractTextElementLanguages(element, reporter, "trademark"):
        haveError = True
    # test for text element compliance
    if not haveError:
        reporter.logPass(message="The \"trademark\" element is properly formatted.")

def testMetadataLicensee(element, reporter):
    """
    Tests:
    - name is present and contains text
    - unknown attributes
    - child-elements
    - text
    """
    required = "name".split(" ")
    haveError = testMetadataAbstractElement(element, reporter, tag="vendor", requiredAttributes=required)
    if not haveError:
        reporter.logPass(message="The \"licensee\" element is properly formatted.")

# support

def testMetadataAbstractElement(element, reporter, tag,
    requiredAttributes=[], optionalAttributes=[], noteMissingOptionalAttributes=True,
    knownChildElements=[], missingChildElementsAlertLevel="error", requireText=False):
    haveError = False
    # missing required attribute
    if testMetadataAbstractElementRequiredAttributes(element, reporter, tag, requiredAttributes):
        haveError = True
    # missing optional attributes
    testMetadataAbstractElementOptionalAttributes(element, reporter, tag, optionalAttributes, noteMissingOptionalAttributes)
    # unknown attributes
    if testMetadataAbstractElementUnknownAttributes(element, reporter, tag, requiredAttributes, optionalAttributes):
        haveError = True
    # empty values
    if testMetadataAbstractElementEmptyValue(element, reporter, tag, requiredAttributes, optionalAttributes):
        haveError = True
    # text
    if requireText:
        if testMetadataAbstractElementRequiredText(element, reporter, tag):
            haveError = True
    else:
        if testMetadataAbstractElementIllegalText(element, reporter, tag):
            haveError = True
    # child elements
    if knownChildElements:
        if testMetadataAbstractElementKnownChildElements(element, reporter, tag, knownChildElements, missingChildElementsAlertLevel):
            haveError = True
    else:
        if testMetadataAbstractElementIllegalChildElements(element, reporter, tag):
            haveError = True
    return haveError

def testMetadataAbstractElementRequiredAttributes(element, reporter, tag, requiredAttributes):
    haveError = False
    for attr in sorted(requiredAttributes):
        if attr not in element.attrib:
            reporter.logError(message="Required attribute \"%s\" is not defined in the \"%s\" element." % (attr, tag))
            haveError = True
    return haveError

def testMetadataAbstractElementOptionalAttributes(element, reporter, tag, optionalAttributes, noteMissingOptionalAttributes=True):
    for attr in sorted(optionalAttributes):
        if attr not in element.attrib and noteMissingOptionalAttributes:
            reporter.logNote(message="Optional attribute \"%s\" is not defined in the \"%s\" element." % (attr, tag))

def testMetadataAbstractElementUnknownAttributes(element, reporter, tag, requiredAttributes, optionalAttributes):
    haveError = False
    for attr in sorted(element.attrib.keys()):
        if attr not in requiredAttributes and attr not in optionalAttributes:
            reporter.logWarning(
                message="Unknown \"%s\" attribute of \"%s\" element." % (attr, tag),
                information="This attribute will be unknown to user agents.")
            haveError = True
    return haveError

def testMetadataAbstractElementEmptyValue(element, reporter, tag, requiredAttributes, optionalAttributes):
    haveError = False
    for attr, value in sorted(element.attrib.items()):
        # skip unknown attributes
        if attr not in requiredAttributes and attr not in optionalAttributes:
            continue
        # empty value
        elif not value.strip():
            reporter.logError(message="The value for the \"%s\" attribute in the \"%s\" element is an empty string." % (attr, tag))
            haveError = True
    return haveError

def testMetadataAbstractElementRequiredText(element, reporter, tag):
    haveError = False
    if element.text is not None and element.text.strip():
        pass
    else:
        reporter.logError("Text not defined in \"%s\" element." % tag)
        haveError = True
    return haveError

def testMetadataAbstractElementIllegalText(element, reporter, tag):
    haveError = False
    if element.text is not None and element.text.strip():
        reporter.logError("Text defined in \"%s\" element." % tag)
        haveError = True
    return haveError

def testMetadataAbstractElementKnownChildElements(element, reporter, tag, knownChildElements, missingChildElementsAlertLevel="error"):
    foundTags = set()
    for child in element:
        if child.tag in knownChildElements:
            foundTags.add(child.tag)
        else:
            reporter.logWarning(
                message="Unknown \"%s\" child element in \"%s\" element." % (child.tag, tag),
                information="This element will be unknown to user agents.")
    haveError = False
    for childTag in sorted(knownChildElements):
        if childTag not in foundTags:
            if missingChildElementsAlertLevel == "error":
                reporter.logError(message="Child element \"%s\" is not defined in the \"%s\" element." % (childTag, tag))
            elif missingChildElementsAlertLevel == "warning":
                reporter.logWarning(message="Child element \"%s\" is not defined in the \"%s\" element." % (childTag, tag))
            elif missingChildElementsAlertLevel == "note":
                reporter.logNote(message="Child element \"%s\" is not defined in the \"%s\" element." % (childTag, tag))
            else:
                raise NotImplementedError("Unknown missingChildElementsAlertLevel value: %s" % missingChildElementsAlertLevel)
            haveError = True
    return haveError

def testMetadataAbstractElementIllegalChildElements(element, reporter, tag):
    haveError = False
    if len(element):
        reporter.logError("Child elements defined in \"%s\" element." % tag)
        haveError = True
    return haveError

def testMetadataAbstractTextElements(element, reporter, tag):
    """
    Tests:
    - no unknown attributes
    - no child elements
    - optional language
    - has text
    """
    haveError = False
    for child in element:
        if child.tag != "text":
            continue
        if testMetadataAbstractElement(child, reporter, tag, optionalAttributes=["lang"], requireText=True, noteMissingOptionalAttributes=False):
            haveError = True
    return haveError

def testMetadataAbstractTextElementLanguages(element, reporter, tag):
    """
    Tests:
    - duplicate languages
    """
    haveError = False
    languages = {}
    for child in element:
        if child.tag != "text":
            continue
        lang = child.attrib.get("lang", "undefined")
        if lang not in languages:
            languages[lang] = 0
        languages[lang] += 1
    for lang, count in sorted(languages.items()):
        if count > 1:
            haveError = True
            reporter.logError(message="More than one instance of language \"%s\" in the \"%s\" element." % (lang, tag))
    return haveError


# ------------
# Private Data
# ------------

def testPrivateDataOffsetAndLength(data, reporter):
    """
    Tests:
    - if offset is zero, length is 0. vice-versa.
    - offset is before the end of the header/directory.
    - offset is after the end of the file.
    - offset + length is greater than the available length.
    - length is longer than the available length.
    - offset begins immediately after last table.
    - offset begins on 4-byte boundary.
    """
    header = unpackHeader(data)
    privOffset = header["privOffset"]
    privLength = header["privLength"]
    # empty offset or length
    if privOffset == 0 or privLength == 0:
        if privOffset == 0 and privLength == 0:
            reporter.logPass(message="The length and offset are appropriately set for empty private data.")
        else:
            reporter.logError(message="The private data offset (%d) and private data length (%d) are not properly set. If one is 0, they both must be 0." % (privOffset, privLength))
        return
    # 4-byte boundary
    if privOffset % 4:
        reporter.logError(message="The private data does not begin on a four-byte boundary.")
        return
    # borders
    totalLength = header["length"]
    numTables = header["numTables"]
    directory = unpackDirectory(data)
    offsets = [headerSize + (directorySize * numTables)]
    for table in directory:
        tag = table["tag"]
        offset = table["offset"]
        length = table["compLength"]
        offsets.append(offset + length)
    if header["metaOffset"] != 0:
        offsets.append(header["metaOffset"] + header["metaLength"])
    minOffset = max(offsets)
    if minOffset % 4:
        minOffset += 4 - (minOffset % 4)
    maxLength = totalLength - minOffset
    offsetErrorMessage = "The metadata has an invalid offset (%d)." % privOffset
    lengthErrorMessage = "The metadata has an invalid length (%d)." % privLength
    if privOffset < minOffset:
        reporter.logError(message=offsetErrorMessage)
    elif privOffset > totalLength:
        reporter.logError(message=offsetErrorMessage)
    elif (privOffset + privLength) > totalLength:
        reporter.logError(message=lengthErrorMessage)
    elif privLength > maxLength:
        reporter.logError(message=lengthErrorMessage)
    elif privOffset != minOffset:
        reporter.logError(message=offsetErrorMessage)
    else:
        reporter.logPass(message="The private data has properly set offset and length.")

# ---------
# Reporters
# ---------

class TestResultGroup(list):

    def __init__(self, title):
        super(TestResultGroup, self).__init__()
        self.title = title

    def _haveType(self, tp):
        for data in self:
            if data["type"] == tp:
                return True
        return False

    def haveNote(self):
        return self._haveType("NOTE")

    def haveWarning(self):
        return self._haveType("WARNING")

    def haveError(self):
        return self._haveType("ERROR")

    def havePass(self):
        return self._haveType("PASS")

    def haveTraceback(self):
        return self._haveType("TRACEBACK")


class HTMLReporter(object):

    def __init__(self):
        self.title = ""
        self.fileInfo = []
        self.testResults = []
        self.haveReadError = False

    def logTitle(self, title):
        self.title = title

    def logFileInfo(self, title, value):
        self.fileInfo.append((title, value))

    def logTableInfo(self, tag=None, offset=None, compLength=None, origLength=None, origChecksum=None):
        self.tableInfo.append((tag, offset, compLength, origLength, origChecksum))

    def logTestTitle(self, title):
        self.testResults.append(TestResultGroup(title))

    def logNote(self, message, information=""):
        d = dict(type="NOTE", message=message, information=information)
        self.testResults[-1].append(d)

    def logWarning(self, message, information=""):
        d = dict(type="WARNING", message=message, information=information)
        self.testResults[-1].append(d)

    def logError(self, message, information=""):
        d = dict(type="ERROR", message=message, information=information)
        self.testResults[-1].append(d)

    def logPass(self, message, information=""):
        d = dict(type="PASS", message=message, information=information)
        self.testResults[-1].append(d)

    def logTraceback(self, text):
        d = dict(type="TRACEBACK", message=text, information="")
        self.testResults[-1].append(d)

    def getReport(self):
        writer = startHTML(title=self.title)
        # write the file info
        self._writeFileInfo(writer)
        # write major error alert
        if self.haveReadError:
            self._writeMajorError(writer)
        # write the test overview
        self._writeTestResultsOverview(writer)
        # write the test groups
        self._writeTestResults(writer)
        # close the html
        text = finishHTML(writer)
        # done
        return text

    def _writeFileInfo(self, writer):
        # write the font info
        writer.begintag("div", c_l_a_s_s="infoBlock")
        ## title
        writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
        writer.write("File Information")
        writer.endtag("h3")
        ## table
        writer.begintag("table", c_l_a_s_s="report")
        ## items
        for title, value in self.fileInfo:
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
        writer.endtag("table")
        ## close the container
        writer.endtag("div")

    def _writeMajorError(self, writer):
        writer.begintag("h2", c_l_a_s_s="readError")
        writer.write("The file contains major structural errors!")
        writer.endtag("h2")

    def _writeTestResultsOverview(self, writer):
        ## tabulate
        notes = 0
        passes = 0
        errors = 0
        warnings = 0
        for group in self.testResults:
            for data in group:
                tp = data["type"]
                if tp == "NOTE":
                    notes += 1
                elif tp == "PASS":
                    passes += 1
                elif tp == "ERROR":
                    errors += 1
                else:
                    warnings += 1
        total = sum((notes, passes, errors, warnings))
        ## container
        writer.begintag("div", c_l_a_s_s="infoBlock")
        ## header
        writer.begintag("h3", c_l_a_s_s="infoBlockTitle")
        writer.write("Results for %d Tests" % total)
        writer.endtag("h3")
        ## results
        results = [
            ("PASS", passes),
            ("WARNING", warnings),
            ("ERROR", errors),
            ("NOTE", notes),
        ]
        writer.begintag("table", c_l_a_s_s="report")
        for tp, value in results:
            # title
            writer.begintag("tr", c_l_a_s_s="testReport%s" % tp.title())
            writer.begintag("td", c_l_a_s_s="title")
            writer.write(tp)
            writer.endtag("td")
            # count
            writer.begintag("td", c_l_a_s_s="testReportResultCount")
            writer.write(str(value))
            writer.endtag("td")
            # empty
            writer.begintag("td")
            writer.endtag("td")
            # toggle button
            buttonID = "testResult%sToggleButton" % tp
            writer.begintag("td",
                id=buttonID, c_l_a_s_s="toggleButton",
                onclick="testResultToggleButtonHit(a_p_o_s_t_r_o_p_h_e%sa_p_o_s_t_r_o_p_h_e, a_p_o_s_t_r_o_p_h_e%sa_p_o_s_t_r_o_p_h_e);" % (buttonID, "test%s" % tp.title()))
            writer.write("Hide")
            writer.endtag("td")
            # close the row
            writer.endtag("tr")
        writer.endtag("table")
        ## close the container
        writer.endtag("div")

    def _writeTestResults(self, writer):
        for infoBlock in self.testResults:
            # container
            writer.begintag("div", c_l_a_s_s="infoBlock")
            # header
            writer.begintag("h4", c_l_a_s_s="infoBlockTitle")
            writer.write(infoBlock.title)
            writer.endtag("h4")
            # individual reports
            writer.begintag("table", c_l_a_s_s="report")
            for data in infoBlock:
                tp = data["type"]
                message = data["message"]
                information = data["information"]
                # row
                writer.begintag("tr", c_l_a_s_s="test%s" % tp.title())
                # title
                writer.begintag("td", c_l_a_s_s="title")
                writer.write(tp)
                writer.endtag("td")
                # message
                writer.begintag("td")
                writer.write(message)
                ## info
                if information:
                    writer.begintag("p", c_l_a_s_s="info")
                    writer.write(information)
                    writer.endtag("p")
                writer.endtag("td")
                # close row
                writer.endtag("tr")
            writer.endtag("table")
            # close container
            writer.endtag("div")


# ----------------
# Helper Functions
# ----------------

def unpackHeader(data):
    return sstruct.unpack2(headerFormat, data)[0]

def unpackDirectory(data):
    header = unpackHeader(data)
    numTables = header["numTables"]
    data = data[headerSize:]
    directory = []
    for index in range(numTables):
        table, data = sstruct.unpack2(directoryFormat, data)
        directory.append(table)
    return directory

def unpackTableData(data):
    directory = unpackDirectory(data)
    tables = {}
    for entry in directory:
        tag = entry["tag"]
        offset = entry["offset"]
        origLength = entry["origLength"]
        compLength = entry["compLength"]
        tableData = data[offset:offset+compLength]
        if compLength < origLength:
            tableData = zlib.decompress(tableData)
        tables[tag] = tableData
    return tables

def unpackMetadata(data, decompress=True, parse=True):
    header = unpackHeader(data)
    data = data[header["metaOffset"]:header["metaOffset"]+header["metaLength"]]
    if decompress and data:
        data = zlib.decompress(data)
    if parse and data:
        data = ElementTree.fromstring(data)
    return data

def unpackPrivateData(data):
    header = unpackHeader(data)
    data = data[header["privOffset"]:header["privOffset"]+header["privLength"]]
    return data

# adapted from fontTools.ttLib.sfnt

def calcChecksum(tag, data):
    if tag == "head":
        data = data[:8] + '\0\0\0\0' + data[12:]
    data = padData(data)
    data = struct.unpack(">%dL" % (len(data) / 4), data)
    a = numpy.array(tuple([0]) + data, numpy.uint32)
    cs = int(numpy.sum(a, dtype=numpy.uint32))
    return int(cs)

def calcHeadCheckSum(data):
    header = unpackHeader(data)
    directory = unpackDirectory(data)
    tables = unpackTableData(data)
    numTables = header["numTables"]
    # sort tables
    sorter = []
    for entry in directory:
        sorter.append((entry["offset"], entry, tables[entry["tag"]]))
    # build the sfnt directory
    searchRange, entrySelector, rangeShift = getSearchRange(numTables)
    sfntDirectoryData = dict(
        sfntVersion=header["flavor"],
        numTables=numTables,
        searchRange=searchRange,
        entrySelector=entrySelector,
        rangeShift=rangeShift
    )
    directory = sstruct.pack(sfntDirectoryFormat, sfntDirectoryData)
    sfntEntries = {}
    offset = sfntDirectorySize + (sfntDirectoryEntrySize * numTables)
    for index, entry, data in sorted(sorter):
        if entry["tag"] == "head":
            checksum = calcChecksum("head", data)
        else:
            checksum = entry["origChecksum"]
        sfntEntry = SFNTDirectoryEntry()
        sfntEntry.tag = entry["tag"]
        sfntEntry.checkSum = entry["origChecksum"]
        sfntEntry.offset = offset
        sfntEntry.length = entry["origLength"]
        sfntEntries[entry["tag"]] = sfntEntry
        offset += entry["origLength"]
        if entry["origLength"] % 4:
            offset += 4 - (entry["origLength"] % 4)
    for tag, sfntEntry in sorted(sfntEntries.items()):
        directory += sfntEntry.toString()
    # calculate
    tags = sfntEntries.keys()
    checksums = numpy.zeros(len(tags) + 1, numpy.uint32)
    for index, tag in enumerate(tags):
        checksums[index] = sfntEntries[tag].checkSum
    directoryEnd = sfntDirectorySize + (len(tags) * sfntDirectoryEntrySize)
    assert directoryEnd == len(directory)
    checksums[-1] = calcChecksum(None, directory)
    checksum = numpy.add.reduce(checksums, dtype=numpy.uint32)
    checkSumAdjustment = int(numpy.subtract.reduce(numpy.array([0xB1B0AFBA, checksum], numpy.uint32)))
    return checkSumAdjustment

def padData(data):
    remainder = len(data) % 4
    if remainder:
        data += "\0" * (4 - remainder)
    return data

# ---------------
# Public Function
# ---------------

tests = [
    ("Header - Size",                       "h-size",               testHeaderSize),
    ("Header - Structure",                  "h-structure",          testHeaderStructure),
    ("Header - Signature",                  "h-signature",          testHeaderSignature),
    ("Header - Flavor",                     "h-flavor",             testHeaderFlavor),
    ("Header - Length",                     "h-length",             testHeaderLength),
    ("Header - Reserved",                   "h-reserved",           testHeaderReserved),
    ("Header - Total sfnt Size",            "h-sfntsize",           testHeaderTotalSFNTSize),
    ("Header - Version",                    "h-version",            testHeaderMajorVersionAndMinorVersion),
    ("Header - Number of Tables",           "h-numtables",          testHeaderNumTables),
    ("Directory - Table Order",             "d-order",              testDirectoryTableOrder),
    ("Directory - Table Borders",           "d-borders",            testDirectoryBorders),
    ("Directory - Compressed Length",       "d-complength",         testDirectoryCompressedLength),
    ("Directory - Table Checksums",         "d-checksum",           testDirectoryChecksums),
    ("Tables - Start Position",             "t-start",              testTableDataStart),
    ("Tables - Padding",                    "t-padding",            testTablePadding),
    ("Tables - Decompression",              "t-decompression",      testTableDecompression),
    ("Tables - Original Length",            "t-origlength",         testDirectoryDecompressedLength),
    ("Tables - checkSumAdjustment",         "t-headchecksum",       testHeadCheckSumAdjustment),
    ("Tables - DSIG",                       "t-dsig",               testDSIG),
    ("Metadata - Offset and Length",        "m-offsetlength",       testMetadataOffsetAndLength),
    ("Metadata - Decompression",            "m-decompression",      testMetadataDecompression),
    ("Metadata - Original Length",          "m-metaOriglength",     testMetadataDecompressedLength),
    ("Metadata - Parse",                    "m-parse",              testMetadataParse),
    ("Metadata - Structure",                "m-structure",          testMetadataStructure),
    ("Private Data - Offset and Length",    "m-structure",          testPrivateDataOffsetAndLength),
]

def validateFont(path, options, writeFile=True):
    reporter = HTMLReporter()
    reporter.logTitle("Report: %s" % os.path.basename(path))
    # log fileinfo
    reporter.logFileInfo("FILE", os.path.basename(path))
    reporter.logFileInfo("DIRECTORY", os.path.dirname(path))
    # run tests and log results
    skip = options.excludeTests
    f = open(path, "rb")
    data = f.read()
    f.close()
    shouldStop = False
    for title, tag, func in tests:
        if tag in skip:
            continue
        reporter.logTestTitle(title)
        shouldStop = func(data, reporter)
        if shouldStop:
            break
    reporter.haveReadError = shouldStop
    # get the report
    report = reporter.getReport()
    # write
    if writeFile:
        # make the output file name
        if options.outputFileName is not None:
            fileName = options.outputFileName
        else:
            fileName = os.path.splitext(os.path.basename(path))[0]
            fileName += "_validate"
            fileName += ".html"
        # make the output directory
        if options.outputDirectory is not None:
            directory = options.outputDirectory
        else:
            directory = os.path.dirname(path)
        # write the file
        reportPath = os.path.join(directory, fileName)
        reportPath = findUniqueFileName(reportPath)
        f = open(reportPath, "wb")
        f.write(report)
        f.close()
    return report

# --------------------
# Command Line Behvior
# --------------------

usage = "%prog [options] fontpath1 fontpath2"

description = """This tool examines the structure of one
or more WOFF files and issues a detailed report about
the validity of the file structure. It does not validate
the wrapped font data.
"""
identifiers = []
for name, identifier, func in tests:
    identifiers.append(identifier)

def main():
    parser = optparse.OptionParser(usage=usage, description=description, version="%prog 0.1beta")
    parser.add_option("-x", action="append", dest="excludeTests", help="Exclude tests. Supply an identifier from this list: %s" % ", ".join(identifiers))
    parser.add_option("-d", dest="outputDirectory", help="Output directory. The default is to output the report into the same directory as the font file.")
    parser.add_option("-o", dest="outputFileName", help="Output file name. The default is \"fontfilename_validate.html\".")
    parser.set_defaults(excludeTests=[])
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
            print "Testing: %s..." % fontPath
            fontPath = fontPath.decode("utf-8")
            validateFont(fontPath, options)

if __name__ == "__main__":
    main()
