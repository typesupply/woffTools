"""
A module for validating the the file structure of WOFF Files.
*validateFont* is the only public function.

This can also be used as a command line tool for validating WOFF files.
"""

"""
TO DO:
- merge metadata and table info from woff-info
- split length and offset tests into smaller functions that can be more easily doctested
- test for proper ordering of table data, metadata, private data
- test metadata extension element
- test for gaps in table data
- test for overlapping tables
- review spec testable assertions and make sure they are all covered here
- check conformance levels of all tests
"""

# import

import os
import time
import sys
import struct
import zlib
import optparse
from cStringIO import StringIO
from xml.etree import ElementTree
from xml.parsers.expat import ExpatError

# ----------------------
# Support: struct Helper
# ----------------------

# This was inspired by Just van Rossum's sstruct module.
# http://fonttools.svn.sourceforge.net/svnroot/fonttools/trunk/Lib/sstruct.py

def structPack(format, obj):
    keys, formatString = _structGetFormat(format)
    values = []
    for key in keys:
        values.append(obj[key])
    data = struct.pack(formatString, *values)
    return data

def structUnpack(format, data):
    keys, formatString = _structGetFormat(format)
    size = struct.calcsize(formatString)
    values = struct.unpack(formatString, data[:size])
    unpacked = {}
    for index, key in enumerate(keys):
        value = values[index]
        unpacked[key] = value
    return unpacked, data[size:]

def structCalcSize(format):
    keys, formatString = _structGetFormat(format)
    return struct.calcsize(formatString)

_structFormatCache = {}

def _structGetFormat(format):
    if format not in _structFormatCache:
        keys = []
        formatString = [">"] # always big endian
        for line in format.strip().splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            key, formatCharacter = line.split(":")
            key = key.strip()
            formatCharacter = formatCharacter.strip()
            keys.append(key)
            formatString.append(formatCharacter)
        _structFormatCache[format] = (keys, "".join(formatString))
    return _structFormatCache[format]


# -------------
# Tests: Header
# -------------

headerFormat = """
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
headerSize = structCalcSize(headerFormat)

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
        structUnpack(headerFormat, data)
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
    requiredSize = sfntHeaderSize + (numTables * sfntDirectoryEntrySize)
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


# ----------------------
# Tests: Table Directory
# ----------------------

directoryFormat = """
    tag:            4s
    offset:         L
    compLength:     L
    origLength:     L
    origChecksum:   L
"""
directorySize = structCalcSize(directoryFormat)

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
            d, data = structUnpack(directoryFormat, data)
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

# -------------
# Tests: Tables
# -------------

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
    newChecksum = calcHeadChecksum(data)
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

# ----------------
# Tests: Metadata
# ----------------

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

# -------------------
# Tests: Private Data
# -------------------

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

# -------------------------
# Support: Misc. SFNT Stuff
# -------------------------

# Some of this was adapted from fontTools.ttLib.sfnt

sfntHeaderFormat = """
    sfntVersion:    4s
    numTables:      H
    searchRange:    H
    entrySelector:  H
    rangeShift:     H
"""
sfntHeaderSize = structCalcSize(sfntHeaderFormat)

sfntDirectoryEntryFormat = """
    tag:            4s
    checkSum:       L
    offset:         L
    length:         L
"""
sfntDirectoryEntrySize = structCalcSize(sfntDirectoryEntryFormat)

def maxPowerOfTwo(value):
    exponent = 0
    while value:
        value = value >> 1
        exponent += 1
    return max(exponent - 1, 0)

def getSearchRange(numTables):
    exponent = maxPowerOfTwo(numTables)
    searchRange = (2 ** exponent) * 16
    entrySelector = exponent
    rangeShift = numTables * 16 - searchRange
    return searchRange, entrySelector, rangeShift

def calcPaddingLength(length):
    return 4 - (length % 4)

def padData(data):
    data += "\0" * calcPaddingLength(len(data))
    return data

def sumDataULongs(data):
    longs = struct.unpack(">%dL" % (len(data) / 4), data)
    value = sum(longs) % (2 ** 32)
    return value

def calcChecksum(tag, data):
    if tag == "head":
        data = data[:8] + "\0\0\0\0" + data[12:]
    data = padData(data)
    value = sumDataULongs(data)
    return value

def calcHeadChecksum(data):
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
    sfntHeaderData = dict(
        sfntVersion=header["flavor"],
        numTables=numTables,
        searchRange=searchRange,
        entrySelector=entrySelector,
        rangeShift=rangeShift
    )
    sfntData = structPack(sfntHeaderFormat, sfntHeaderData)
    sfntEntries = {}
    offset = sfntHeaderSize + (sfntDirectoryEntrySize * numTables)
    for index, entry, data in sorted(sorter):
        if entry["tag"] == "head":
            checksum = calcChecksum("head", data)
        else:
            checksum = entry["origChecksum"]
        tag = entry["tag"]
        length = entry["origLength"]
        sfntEntries[tag] = dict(
            tag=tag,
            checkSum=entry["origChecksum"],
            offset=offset,
            length=length
        )
        offset += length + calcPaddingLength(length)
    for tag, sfntEntry in sorted(sfntEntries.items()):
        sfntData += structPack(sfntDirectoryEntryFormat, sfntEntry)
    # calculate
    tags = sfntEntries.keys()
    checkSums = [entry["checkSum"] for entry in sfntEntries.values()]
    directoryEnd = sfntHeaderSize + (len(tags) * sfntDirectoryEntrySize)
    assert directoryEnd == len(sfntData)
    checkSums.append(calcChecksum(None, sfntData))
    checkSum = sum(checkSums)
    checkSum = 0xB1B0AFBA - checkSum
    return checkSum

# ------------------
# Support XML Writer
# ------------------

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

# ---------------------------------
# Support: Reporters and HTML Stuff
# ---------------------------------

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

# ------------------
# Support: Unpackers
# ------------------

def unpackHeader(data):
    return structUnpack(headerFormat, data)[0]

def unpackDirectory(data):
    header = unpackHeader(data)
    numTables = header["numTables"]
    data = data[headerSize:]
    directory = []
    for index in range(numTables):
        table, data = structUnpack(directoryFormat, data)
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

# -----------------------
# Support: Report Helpers
# -----------------------

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


# ---------------
# Public Function
# ---------------

tests = [
    ("Header - Size",                    testHeaderSize),
    ("Header - Structure",               testHeaderStructure),
    ("Header - Signature",               testHeaderSignature),
    ("Header - Flavor",                  testHeaderFlavor),
    ("Header - Length",                  testHeaderLength),
    ("Header - Reserved",                testHeaderReserved),
    ("Header - Total sfnt Size",         testHeaderTotalSFNTSize),
    ("Header - Version",                 testHeaderMajorVersionAndMinorVersion),
    ("Header - Number of Tables",        testHeaderNumTables),
    ("Directory - Table Order",          testDirectoryTableOrder),
    ("Directory - Table Borders",        testDirectoryBorders),
    ("Directory - Compressed Length",    testDirectoryCompressedLength),
    ("Directory - Table Checksums",      testDirectoryChecksums),
    ("Tables - Start Position",          testTableDataStart),
    ("Tables - Padding",                 testTablePadding),
    ("Tables - Decompression",           testTableDecompression),
    ("Tables - Original Length",         testDirectoryDecompressedLength),
    ("Tables - checkSumAdjustment",      testHeadCheckSumAdjustment),
    ("Tables - DSIG",                    testDSIG),
    ("Metadata - Offset and Length",     testMetadataOffsetAndLength),
    ("Metadata - Decompression",         testMetadataDecompression),
    ("Metadata - Original Length",       testMetadataDecompressedLength),
    ("Metadata - Parse",                 testMetadataParse),
    ("Metadata - Structure",             testMetadataStructure),
    ("Private Data - Offset and Length", testPrivateDataOffsetAndLength),
]

def validateFont(path, options, writeFile=True):
    reporter = HTMLReporter()
    reporter.logTitle("Report: %s" % os.path.basename(path))
    # log fileinfo
    reporter.logFileInfo("FILE", os.path.basename(path))
    reporter.logFileInfo("DIRECTORY", os.path.dirname(path))
    # run tests and log results
    f = open(path, "rb")
    data = f.read()
    f.close()
    shouldStop = False
    for title, func in tests:
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

def main():
    parser = optparse.OptionParser(usage=usage, description=description, version="%prog 0.1beta")
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
