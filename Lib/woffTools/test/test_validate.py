import struct
import zlib
from copy import deepcopy
from xml.etree import ElementTree
from woffTools.tools.validate import structPack, \
    HTMLReporter,\
    calcChecksum, calcHeadChecksum,\
    calcPaddingLength, \
    sfntHeaderFormat, sfntHeaderSize, sfntDirectoryEntryFormat, sfntDirectoryEntrySize, \
    shouldSkipMetadataTest,\
    testDirectoryBorders,\
    testDirectoryChecksums,\
    testDirectoryCompressedLength,\
    testDirectoryDecompressedLength,\
    testDirectoryTableOrder,\
    testHeadCheckSumAdjustment,\
    testHeaderFlavor,\
    testHeaderLength,\
    testHeaderMajorVersionAndMinorVersion,\
    testHeaderNumTables,\
    testHeaderReserved,\
    testHeaderSignature,\
    testHeaderSize,\
    testHeaderStructure,\
    testHeaderTotalSFNTSize,\
    testMetadataAbstractElementEmptyValue,\
    testMetadataAbstractElementIllegalChildElements,\
    testMetadataAbstractElementIllegalText,\
    testMetadataAbstractElementKnownChildElements,\
    testMetadataAbstractElementOptionalAttributes,\
    testMetadataAbstractElementOptionalChildElements,\
    testMetadataAbstractElementRequiredAttributes,\
    testMetadataAbstractElementRequiredText,\
    testMetadataAbstractElementUnknownAttributes,\
    testMetadataAbstractElementLanguages,\
    testMetadataAbstractTextElements,\
    testMetadataChildElements,\
    testMetadataCopyright,\
    testMetadataCredit,\
    testMetadataCredits,\
    testMetadataDecompressedLength,\
    testMetadataDecompression,\
    testMetadataDescription,\
    testMetadataDuplicateElements,\
    testMetadataElementExistence,\
    testMetadataExtension,\
    testMetadataIsCompressed,\
    testMetadataLicense,\
    testMetadataLicensee,\
    testMetadataOffsetAndLength,\
    testMetadataPadding,\
    testMetadataParse,\
    testMetadataStructureTopElement,\
    testMetadataTrademark,\
    testMetadataUniqueid,\
    testMetadataVendor,\
    testPrivateDataOffsetAndLength,\
    testPrivateDataPadding,\
    testTableDataStart,\
    testTableDecompression,\
    testTableGaps, \
    testTablePadding,\
    headerFormat, headerSize,\
    directoryFormat, directorySize

# ---------------
# doctest Support
# ---------------

def doctestFunction1(func, data, resultIndex=-1):
    reporter = HTMLReporter()
    reporter.logTestTitle("doctest")
    shouldStop = func(data, reporter)
    r = reporter.testResults[-1]
    r = r[resultIndex]
    r = r["type"]
    return shouldStop, r

def doctestFunction2(func, data):
    reporter = HTMLReporter()
    reporter.logTestTitle("doctest")
    func(data, reporter)
    r = [i["type"] for i in reporter.testResults[-1]]
    return r

def doctestMetadataAbstractElementFunction(func, element, **kwargs):
    reporter = HTMLReporter()
    reporter.logTestTitle("doctest")
    func(element, reporter, "test", **kwargs)
    return [i["type"] for i in reporter.testResults[-1]]

testDataHeaderDict = dict(
    signature="wOFF",
    flavor="OTTO",
    length=0,
    reserved=0,
    numTables=0,
    totalSfntSize=0,
    majorVersion=0,
    minorVersion=0,
    metaOffset=0,
    metaLength=0,
    metaOrigLength=0,
    privOffset=0,
    privLength=0
)

testDataDirectoryList = [
    dict(
        tag="cmap",
        offset=0,
        compLength=0,
        origLength=0,
        origChecksum=0
    ),
    dict(
        tag="head",
        offset=0,
        compLength=0,
        origLength=0,
        origChecksum=0
    ),
    dict(
        tag="hhea",
        offset=0,
        compLength=0,
        origLength=0,
        origChecksum=0
    )
]

def defaultTestData(header=False, directory=False, tableData=False, metadata=False, privateData=False):
    parts = []
    if header:
        header = deepcopy(testDataHeaderDict)
        header["length"] = headerSize
        parts.append(header)
    if directory:
        directory = deepcopy(testDataDirectoryList)
        if header:
            # set header numTables
            header["numTables"] = len(directory)
            # set header totalSfntSize
            neededSize = sfntHeaderSize
            for table in directory:
                neededSize += sfntDirectoryEntrySize
                neededSize += table["origLength"]
            header["totalSfntSize"] = neededSize
            # set header length
            header["length"] += header["numTables"] * directorySize
            # store the offset for later
            dataOffset = header["length"]
        parts.append(directory)
    if tableData:
        tableData = {}
        parts.append(tableData)
        for entry in deepcopy(testDataDirectoryList):
            tableData[entry["tag"]] = (testDataTableData, testDataTableData)
        if header:
            header["length"] += len(tableData) * len(testDataTableData)
        if directory:
            updateDirectoryEntries(directory=directory, tableData=tableData)
    if metadata:
        metadata = "\0" * 1000 # XXX use real xml!
        compMetadata = zlib.compress(metadata)
        if header:
            header["metaOrigLength"] = len(metadata)
            header["metaLength"] = len(compMetadata)
            header["metaOffset"] = header["length"]
            header["length"] = len(compMetadata) + calcPaddingLength(len(compMetadata))
        compMetadata += "\0" * calcPaddingLength(len(compMetadata))
        parts.append(compMetadata)
    if len(parts) == 1:
        return parts[0]
    return parts

def updateDirectoryEntries(directory=None, tableData=None):
    offset = headerSize + (len(directory) * directorySize)
    for entry in directory:
        origData, compData = tableData[entry["tag"]]
        entry["offset"] = offset
        entry["compLength"] = len(compData)
        entry["origLength"] = len(origData)
        entry["origChecksum"] = 0
        offset += len(compData)

testDataTableData = "\0" * 1000

def packTestHeader(data):
    return structPack(headerFormat, data)

def packTestDirectory(directory):
    data = ""
    for table in directory:
        data += structPack(directoryFormat, table)
    return data

def packTestTableData(directory, tableData):
    if tableData is None:
        tableData = {}
        for entry in directory:
            tableData[entry["tag"]] = (testDataTableData, testDataTableData)
    orderedData = []
    for entry in directory:
        tag = entry["tag"]
        origData, compData = tableData[tag]
        orderedData.append(compData)
    return "".join(orderedData)

# --------------
# test functions
# --------------

# calcPaddingLength

def testCalcPaddedLength():
    """
    >>> calcPaddingLength(0)
    0
    >>> calcPaddingLength(1)
    3
    >>> calcPaddingLength(2)
    2
    >>> calcPaddingLength(3)
    1
    >>> calcPaddingLength(4)
    0
    >>> calcPaddingLength(13)
    3
    >>> calcPaddingLength(14)
    2
    >>> calcPaddingLength(15)
    1
    >>> calcPaddingLength(16)
    0
    """

# testHeaderSize

def headerSizeTest1():
    """
    File with proper length.

    >>> doctestFunction1(testHeaderSize, headerSizeTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    return packTestHeader(header)

def headerSizeTest2():
    """
    File with improper length.

    >>> doctestFunction1(testHeaderSize, headerSizeTest2())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    return packTestHeader(header)[-1]


# testHeaderStructure

def headerStructureTest1():
    """
    Valid structure.

    >>> doctestFunction1(testHeaderStructure, headerStructureTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    return packTestHeader(header)


# testHeaderSignature

def headerSignatureTest1():
    """
    Valid signature.

    >>> doctestFunction1(testHeaderSignature, headerSignatureTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    return packTestHeader(header)

def headerSignatureTest2():
    """
    Invalid signature.

    >>> doctestFunction1(testHeaderSignature, headerSignatureTest2())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["signature"] = "XXXX"
    return packTestHeader(header)

# testHeaderFlavor

def flavorTest1():
    """
    Unknown flavor.

    >>> doctestFunction1(testHeaderFlavor, flavorTest1())
    (None, 'WARNING')
    """
    header = defaultTestData(header=True)
    header["flavor"] = "XXXX"
    return packTestHeader(header)

def flavorTest2():
    """
    Flavor is OTTO, CFF is in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest2())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    directory[-1]["tag"] = "CFF "
    return packTestHeader(header) + packTestDirectory(directory)

def flavorTest3():
    """
    Flavor is 0x00010000, CFF is in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest3())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["flavor"] = "\000\001\000\000"
    directory[-1]["tag"] = "CFF "
    return packTestHeader(header) + packTestDirectory(directory)

def flavorTest4():
    """
    Flavor is 0x00010000, CFF is not in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest4())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["flavor"] = "\000\001\000\000"
    return packTestHeader(header) + packTestDirectory(directory)

def flavorTest5():
    """
    Flavor is OTTO, CFF is not in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest5())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["flavor"] = "OTTO"
    return packTestHeader(header) + packTestDirectory(directory)


# testHeaderLength

def headerLengthTest1():
    """
    Data is long enough for defined length.

    >>> doctestFunction1(testHeaderLength, headerLengthTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 3
    return packTestHeader(header) + ("\0" * 3)

def headerLengthTest2():
    """
    Data is not long enough for defined length.

    >>> doctestFunction1(testHeaderLength, headerLengthTest2())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 3
    return packTestHeader(header) + "\0"

def headerLengthTest3():
    """
    Data is long enough for header and directory.

    >>> doctestFunction1(testHeaderLength, headerLengthTest3())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for table in directory:
        table["offset"] = 0
        table["compLength"] = 0
    return packTestHeader(header) + packTestDirectory(directory)

def headerLengthTest4():
    """
    Data is not long enough for header and directory.

    >>> doctestFunction1(testHeaderLength, headerLengthTest4())
    (True, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["length"] = 1
    return packTestHeader(header) + packTestDirectory(directory)

def headerLengthTest5():
    """
    Data is long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest5())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 10
    header["metaLength"] = 10
    return packTestHeader(header) + ("\0" * 10)

def headerLengthTest6():
    """
    Data is not long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest6())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 10
    header["metaLength"] = 10
    return packTestHeader(header) + ("\0" * 5)

def headerLengthTest7():
    """
    Data is long enough for header and private data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest7())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 10
    header["privLength"] = 10
    return packTestHeader(header) + ("\0" * 10)

def headerLengthTest8():
    """
    Data is long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest8())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] = headerSize + 10
    header["privLength"] = 10
    return packTestHeader(header) + ("\0" * 5)


# testHeaderReserved

def headerReservedTest1():
    """
    reserved is 0.

    >>> doctestFunction1(testHeaderReserved, headerReservedTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["reserved"] = 0
    return packTestHeader(header)

def headerReservedTest2():
    """
    reserved is 1.

    >>> doctestFunction1(testHeaderReserved, headerReservedTest2())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["reserved"] = 1
    return packTestHeader(header)


# testHeaderTotalSFNTSize

def totalSFNTSizeTest1():
    """
    Valid totalSfntSize.

    >>> doctestFunction1(testHeaderTotalSFNTSize, totalSFNTSizeTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    return packTestHeader(header) + packTestDirectory(directory)

def totalSFNTSizeTest2():
    """
    Invalid totalSfntSize. is not a multiple of 4.

    >>> doctestFunction1(testHeaderTotalSFNTSize, totalSFNTSizeTest2())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["totalSfntSize"] -= 1
    return packTestHeader(header) + packTestDirectory(directory)

def totalSFNTSizeTest3():
    """
    Invalid totalSfntSize compared to the table sizes.

    >>> doctestFunction1(testHeaderTotalSFNTSize, totalSFNTSizeTest3())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["totalSfntSize"] += 4
    return packTestHeader(header) + packTestDirectory(directory)


# testHeaderMajorVersionAndMinorVersion

def headerVersionTest1():
    """
    0.0

    >>> doctestFunction1(testHeaderMajorVersionAndMinorVersion, headerVersionTest1())
    (None, 'WARNING')
    """
    header = defaultTestData(header=True)
    header["majorVersion"] = 0
    header["minorVersion"] = 0
    return packTestHeader(header)

def headerVersionTest2():
    """
    1.0

    >>> doctestFunction1(testHeaderMajorVersionAndMinorVersion, headerVersionTest2())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["majorVersion"] = 1
    return packTestHeader(header)


# testHeaderNumTables

def headerNumTablesTest1():
    """
    numTables is 0.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest1())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["numTables"] = 0
    return packTestHeader(header)

def headerNumTablesTest2():
    """
    numTables is 3 and 3 directory entries are packed.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest2())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    return packTestHeader(header) + packTestDirectory(directory)

def headerNumTablesTest3():
    """
    numTables is 4 and 3 directory entries are packed.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest3())
    (True, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    header["numTables"] += 1
    return packTestHeader(header) + packTestDirectory(directory)


# testDirectoryTableOrder

def directoryOrderTest1():
    """
    Valid order.

    >>> doctestFunction1(testDirectoryTableOrder, directoryOrderTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOrderTest2():
    """
    Reversed order.

    >>> doctestFunction1(testDirectoryTableOrder, directoryOrderTest2())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    return packTestHeader(header) + packTestDirectory(reversed(directory))


# testDirectoryBorders

def directoryOffsetLengthTest1():
    """
    Valid offsets and lengths.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"]
    for table in directory:
        table["offset"] = offset
        table["compLength"] = 1
        offset += 1
    header["length"] += len(directory)
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest2():
    """
    Offset within header/directory block.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest2())
    (True, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for table in directory:
        table["offset"] = 0
        table["compLength"] = 1
    header["length"] += len(directory)
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest3():
    """
    Offset after end of file.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest3())
    (True, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for table in directory:
        table["offset"] = 1000
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest4():
    """
    Offset + length after end of file.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest4())
    (True, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"]
    for table in directory:
        table["offset"] = 1000
        table["compLength"] = 1
        offset += 1
    header["length"] += len(directory)
    return packTestHeader(header) + packTestDirectory(directory)


# testDirectoryCompressedLength

def directoryCompressedLengthTest1():
    """
    compLength less than origLength.

    >>> doctestFunction1(testDirectoryCompressedLength, directoryCompressedLengthTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for table in directory:
        table["compLength"] = 10
        table["origLength"] = 11
    return packTestHeader(header) + packTestDirectory(directory)

def directoryCompressedLengthTest2():
    """
    compLength greater than origLength.

    >>> doctestFunction1(testDirectoryCompressedLength, directoryCompressedLengthTest2())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for table in directory:
        table["compLength"] = 11
        table["origLength"] = 10
    return packTestHeader(header) + packTestDirectory(directory)


# testDirectoryDecompressedLength

def decompressedLengthTest1():
    """
    Matching decompressed and origLengths.

    >>> doctestFunction1(testDirectoryDecompressedLength, decompressedLengthTest1())
    (None, 'PASS')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    origData = testDataTableData
    compData = zlib.compress(origData)
    for tag, (origData, compData) in tableData.items():
        tableData[tag] = (origData, zlib.compress(origData))
    updateDirectoryEntries(directory, tableData)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)

def decompressedLengthTest2():
    """
    Non-matching decompressed and origLengths.

    >>> doctestFunction1(testDirectoryDecompressedLength, decompressedLengthTest2())
    (None, 'ERROR')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    origData = testDataTableData
    compData = zlib.compress(origData)
    for tag, (origData, compData) in tableData.items():
        tableData[tag] = (origData, zlib.compress(origData))
    updateDirectoryEntries(directory, tableData)
    for entry in directory:
        entry["origLength"] += 1
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)


# testDirectoryChecksums

def checksumTest1():
    """
    Correct checksums.

    >>> doctestFunction1(testDirectoryChecksums, checksumTest1())
    (None, 'PASS')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)

def checksumTest2():
    """
    Incorrect checksums.

    >>> doctestFunction1(testDirectoryChecksums, checksumTest2())
    (None, 'ERROR')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    for entry in directory:
        entry["origChecksum"] = 123
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)


# testTableDataStart

def tableStartTest1():
    """
    Proper position.

    >>> doctestFunction1(testTableDataStart, tableStartTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"]
    for entry in directory:
        entry["offset"] = offset
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)

def tableStartTest2():
    """
    Improper position.

    >>> doctestFunction1(testTableDataStart, tableStartTest2())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"] + 1
    for entry in directory:
        entry["offset"] = offset
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)


# testTableGaps

def tableGapsTest1():
    """
    No gaps between tables.

    >>> doctestFunction1(testTableGaps, tableGapsTest1())
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"]
    for entry in directory:
        entry["offset"] = offset
        entry["compLength"] = 100
        offset += 100
    return packTestHeader(header) + packTestDirectory(directory)

def tableGapsTest2():
    """
    Gaps between tables.

    >>> doctestFunction1(testTableGaps, tableGapsTest2())
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    offset = header["length"]
    for entry in directory:
        entry["offset"] = offset
        entry["compLength"] = 100
        offset += 104
    return packTestHeader(header) + packTestDirectory(directory)


# testTablePadding

def paddingTest1():
    """
    Proper padding.

    >>> doctestFunction1(testTablePadding, paddingTest1(), -2)
    (None, 'PASS')
    """
    header, directory = defaultTestData(header=True, directory=True)
    return packTestHeader(header) + packTestDirectory(directory)

def paddingTest2():
    """
    Offset not on a 4-bye boundary.

    >>> doctestFunction1(testTablePadding, paddingTest2(), -2)
    (None, 'ERROR')
    """
    header, directory = defaultTestData(header=True, directory=True)
    for entry in directory:
        entry["offset"] = 1
    return packTestHeader(header) + packTestDirectory(directory)

def paddingTest3():
    """
    Proper end padding, no metadata or private data.

    >>> doctestFunction1(testTablePadding, paddingTest3())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] += 4
    return packTestHeader(header)

def paddingTest4():
    """
    Improper end padding, no metadata or private data.

    >>> doctestFunction1(testTablePadding, paddingTest4())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] += 3
    return packTestHeader(header)

def paddingTest5():
    """
    Proper end padding, metadata, no private data.

    >>> doctestFunction1(testTablePadding, paddingTest5())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] += 4
    header["metaOffset"] = header["length"]
    return packTestHeader(header)

def paddingTest6():
    """
    Improper end padding, metadata, no private data.

    >>> doctestFunction1(testTablePadding, paddingTest6())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] += 3
    header["metaOffset"] = header["length"]
    return packTestHeader(header)

def paddingTest7():
    """
    Proper end padding, no metadata, private data.

    >>> doctestFunction1(testTablePadding, paddingTest7())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["length"] += 4
    header["privOffset"] = header["length"]
    return packTestHeader(header)

def paddingTest8():
    """
    Improper end padding, no metadata, private data.

    >>> doctestFunction1(testTablePadding, paddingTest8())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["length"] += 3
    header["privOffset"] = header["length"]
    return packTestHeader(header)


# testTableDecompression

def decompressionTest1():
    """
    Properly compressed data.

    >>> doctestFunction1(testTableDecompression, decompressionTest1())
    (False, 'PASS')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    for tag, (origData, compData) in tableData.items():
        tableData[tag] = (origData, zlib.compress(compData))
    updateDirectoryEntries(directory, tableData)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)

def decompressionTest2():
    """
    Improperly compressed data.

    >>> doctestFunction1(testTableDecompression, decompressionTest2())
    (True, 'ERROR')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    for tag, (origData, compData) in tableData.items():
        compData = "".join(reversed(zlib.compress(compData)))
        tableData[tag] = (origData, compData)
    updateDirectoryEntries(directory, tableData)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)


# testHeadCheckSumAdjustment

def headCheckSumAdjustmentTest1():
    """
    Valid checksum.

    >>> doctestFunction1(testHeadCheckSumAdjustment, headCheckSumAdjustmentTest1())
    (None, 'PASS')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    woffData = packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)
    for entry in directory:
        if entry["tag"] == "head":
            headOffset = entry["offset"]
    checkSumAdjustment = calcHeadChecksum(woffData)
    checkSumAdjustment = struct.pack(">L", checkSumAdjustment)
    woffData = woffData[:headOffset+8] + checkSumAdjustment + woffData[headOffset+12:]
    return woffData

def headCheckSumAdjustmentTest2():
    """
    Invalid checksum.

    >>> doctestFunction1(testHeadCheckSumAdjustment, headCheckSumAdjustmentTest2())
    (None, 'ERROR')
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)


# testMetadataOffsetAndLength

def metadataOffsetLengthTest1():
    """
    Valid empty offset and length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = 0
    header["metaLength"] = 0
    return packTestHeader(header)

def metadataOffsetLengthTest2():
    """
    metaOffset = 0, metaLength = 1.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest2())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = 0
    header["metaLength"] = 1
    return packTestHeader(header)

def metadataOffsetLengthTest3():
    """
    metaOffset = 1, metaLength = 3.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest3())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = 1
    header["metaLength"] = 0
    return packTestHeader(header)

def metadataOffsetLengthTest4():
    """
    Valid offset and length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest4())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def metadataOffsetLengthTest5():
    """
    Offset before end of the directory.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest5())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"] - 4
    header["metaLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def metadataOffsetLengthTest6():
    """
    Offset after end of file.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest6())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"] + 4
    header["metaLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def metadataOffsetLengthTest7():
    """
    Offset + length greater than length of file.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest7())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 2
    header["length"] += 1
    return packTestHeader(header)

def metadataOffsetLengthTest8():
    """
    Length longer than available length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest8())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 2
    header["length"] += 1
    return packTestHeader(header)

def metadataOffsetLengthTest9():
    """
    Offset doesn't begin immediately after last table.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest9())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"] + 4
    header["metaLength"] = 1
    header["length"] += 2
    return packTestHeader(header)

def metadataOffsetLengthTest10():
    """
    Offset doesn't begin on a four-byte boundary.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest10())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"] + 2
    header["metaLength"] = 1
    header["length"] += 2
    return packTestHeader(header)


# testMetadataPadding

def metadataPaddingTest1():
    """
    Valid padding: No padding needed. No private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 8
    header["length"] += 8
    return packTestHeader(header)

def metadataPaddingTest2():
    """
    Valid padding: Padded with  null. No private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest2())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    metadata = "\0" * 8
    header["metaOffset"] = header["length"]
    header["metaLength"] = 7
    header["length"] += 8
    return packTestHeader(header) + metadata

def metadataPaddingTest3():
    """
    Invalid padding: Padded with something other than null. No private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest3())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    metadata = "A" * 8
    header["metaOffset"] = header["length"]
    header["metaLength"] = 7
    header["length"] += 8
    return packTestHeader(header) + metadata

def metadataPaddingTest4():
    """
    Valid padding: No padding needed. Have private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest4())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 8
    header["privOffset"] = header["metaOffset"] + 8
    return packTestHeader(header)

def metadataPaddingTest5():
    """
    Valid padding: Padded with  null. Have private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest5())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    metadata = "\0" * 8
    header["metaOffset"] = header["length"]
    header["metaLength"] = 7
    header["privOffset"] = header["metaOffset"] + 8
    header["length"] += 8
    return packTestHeader(header) + metadata

def metadataPaddingTest6():
    """
    Invalid padding: Padded with something other than null. Have private data.

    >>> doctestFunction1(testMetadataPadding, metadataPaddingTest6())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    metadata = "\A" * 8
    header["metaOffset"] = header["length"]
    header["metaLength"] = 7
    header["privOffset"] = header["metaOffset"] + 8
    header["length"] += 8
    return packTestHeader(header) + metadata


# testMetadataIsCompressed

def metadataIsCompressedTest1():
    """
    Valid metaLength and metaOrigLength.

    >>> doctestFunction1(testMetadataIsCompressed, metadataIsCompressedTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 8
    header["metaOrigLength"] = 10
    header["length"] += 8
    return packTestHeader(header)

def metadataIsCompressedTest2():
    """
    metaLength longer than metaOrigLength.

    >>> doctestFunction1(testMetadataIsCompressed, metadataIsCompressedTest2())
    (True, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 10
    header["metaOrigLength"] = 8
    header["length"] += 10
    return packTestHeader(header)

# shouldSkipMetadataTest

def metadataSkipTest1():
    """
    Have metadata.

    >>> reporter = HTMLReporter()
    >>> shouldSkipMetadataTest(metadataSkipTest1(), reporter)
    >>> reporter.testResults
    []
    """
    header, directory, tableData, metadata = defaultTestData(header=True, directory=True, tableData=True, metadata=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + metadata

def metadataSkipTest2():
    """
    Do not have metadata.

    >>> reporter = HTMLReporter()
    >>> reporter.logTestTitle("Test")
    >>> shouldSkipMetadataTest(metadataSkipTest2(), reporter)
    True
    >>> len(reporter.testResults[0])
    1
    >>> reporter.testResults[0][0]["type"]
    'NOTE'
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData)


# testMetadataDecompression

def metadataDecompressionTest1():
    """
    Properly compressed.

    >>> doctestFunction1(testMetadataDecompression, metadataDecompressionTest1())
    (None, 'PASS')
    """
    header, directory, tableData, metadata = defaultTestData(header=True, directory=True, tableData=True, metadata=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + metadata

def metadataDecompressionTest2():
    """
    Improperly compressed.

    >>> doctestFunction1(testMetadataDecompression, metadataDecompressionTest2())
    (True, 'ERROR')
    """
    header, directory, tableData, metadata = defaultTestData(header=True, directory=True, tableData=True, metadata=True)
    metadata = "".join(reversed(metadata))
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + metadata


# testMetadataDecompressedLength

def metadataDecompressedLengthTest1():
    """
    Correct length..

    >>> doctestFunction1(testMetadataDecompressedLength, metadataDecompressedLengthTest1())
    (None, 'PASS')
    """
    header, directory, tableData, metadata = defaultTestData(header=True, directory=True, tableData=True, metadata=True)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + metadata

def metadataDecompressedLengthTest2():
    """
    Incorrect length.

    >>> doctestFunction1(testMetadataDecompressedLength, metadataDecompressedLengthTest2())
    (None, 'ERROR')
    """
    header, directory, tableData, metadata = defaultTestData(header=True, directory=True, tableData=True, metadata=True)
    header["metaOrigLength"] -= 1
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + metadata


# testMetadataParse

def metadataParseTest1():
    """
    Valid XML.

    >>> doctestFunction1(testMetadataParse, metadataParseTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <foo>
        <bar>
            Test.
        </bar>
    </foo>
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    compMetadata = zlib.compress(metadata)
    header["metaOffset"] = header["length"]
    header["metaOrigLength"] = len(metadata)
    header["metaLength"] = len(compMetadata)
    compMetadata += "\0" * calcPaddingLength(len(compMetadata))
    header["length"] += len(compMetadata)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + compMetadata

def metadataParseTest2():
    """
    Invalid XML.

    >>> doctestFunction1(testMetadataParse, metadataParseTest2())
    (True, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <foo>
        <bar>
            <blah>
                Test.
            <blah>
        </bar>
    </foo>
    """
    header, directory, tableData = defaultTestData(header=True, directory=True, tableData=True)
    compMetadata = zlib.compress(metadata)
    header["metaOffset"] = header["length"]
    header["metaOrigLength"] = len(metadata)
    header["metaLength"] = len(compMetadata)
    compMetadata += "\0" * calcPaddingLength(len(compMetadata))
    header["length"] += len(compMetadata)
    return packTestHeader(header) + packTestDirectory(directory) + packTestTableData(directory, tableData) + compMetadata


# testMetadataAbstractElementRequiredAttributes

def metadataAbstractElementRequiredAttributesTest1():
    """
    Required attributes present.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementRequiredAttributes,
    ...     metadataAbstractElementRequiredAttributesTest1(),
    ...     requiredAttributes=["required1", "required2"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" required2="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredAttributesTest2():
    """
    Required attribute not present.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementRequiredAttributes,
    ...     metadataAbstractElementRequiredAttributesTest2(),
    ...     requiredAttributes=["required1", "required2"])
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredAttributesTest3():
    """
    Unknown attribute present.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementRequiredAttributes,
    ...     metadataAbstractElementRequiredAttributesTest3(),
    ...     requiredAttributes=["required1", "required2"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" required2="foo" unknown1="foo" />
    """
    return ElementTree.fromstring(metadata)


# testMetadataAbstractElementOptionalAttributes

def metadataAbstractElementOptionalAttributesTest1():
    """
    Optional attributes present.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalAttributes,
    ...     metadataAbstractElementOptionalAttributesTest1(),
    ...     optionalAttributes=["optional1", "optional2"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test optional1="foo" optional2="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalAttributesTest2():
    """
    Optional attribute not present, issue note.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalAttributes,
    ...     metadataAbstractElementOptionalAttributesTest2(),
    ...     optionalAttributes=["optional1", "optional2"])
    ['NOTE']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test optional1="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalAttributesTest3():
    """
    Optional attribute not present, don't issue note.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalAttributes,
    ...     metadataAbstractElementOptionalAttributesTest3(),
    ...     optionalAttributes=["optional1", "optional2"],
    ...     noteMissingOptionalAttributes=False)
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test optional1="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalAttributesTest4():
    """
    Unknown attribute present.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalAttributes,
    ...     metadataAbstractElementOptionalAttributesTest4(),
    ...     optionalAttributes=["optional1", "optional2"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test optional1="foo" optional2="foo" unknown1="foo" />
    """
    return ElementTree.fromstring(metadata)


# testMetadataAbstractElementUnknownAttributes

def metadataAbstractElementUnknownAttributesTest1():
    """
    No unknown attributes.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementUnknownAttributes,
    ...     metadataAbstractElementUnknownAttributesTest1(),
    ...     requiredAttributes=["required1", "required2"],
    ...     optionalAttributes=["optional1", "optional2"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" required2="foo" optional1="foo" optional2="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementUnknownAttributesTest2():
    """
    No unknown attributes.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementUnknownAttributes,
    ...     metadataAbstractElementUnknownAttributesTest2(),
    ...     requiredAttributes=["required1", "required2"],
    ...     optionalAttributes=["optional1", "optional2"])
    ['WARNING']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" required2="foo" optional1="foo" optional2="foo" unknown1="foo" />
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementEmptyValue

def metadataAbstractElementEmptyValuesTest1():
    """
    No empty values.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementEmptyValue,
    ...     metadataAbstractElementEmptyValuesTest1(),
    ...     requiredAttributes=["required1"],
    ...     optionalAttributes=["optional1"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" optional1="foo" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementEmptyValuesTest2():
    """
    Empty values.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementEmptyValue,
    ...     metadataAbstractElementEmptyValuesTest2(),
    ...     requiredAttributes=["required1"],
    ...     optionalAttributes=["optional1"])
    ['ERROR', 'ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="" optional1="" />
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementEmptyValuesTest3():
    """
    Empty value for unknown attribute.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementEmptyValue,
    ...     metadataAbstractElementEmptyValuesTest3(),
    ...     requiredAttributes=["required1"],
    ...     optionalAttributes=["optional1"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test required1="foo" optional1="foo" unknown1="" />
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementIllegalText

def metadataAbstractElementIllegalTextTest1():
    """
    No text, text not required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementIllegalText,
    ...     metadataAbstractElementIllegalTextTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementIllegalTextTest2():
    """
    Text, text not required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementIllegalText,
    ...     metadataAbstractElementIllegalTextTest2())
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        Foo.
    </test>
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementRequiredText

def metadataAbstractElementRequireTextTest1():
    """
    No text, text required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementRequiredText,
    ...     metadataAbstractElementRequireTextTest1())
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequireTextTest2():
    """
    Text, text required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementRequiredText,
    ...     metadataAbstractElementRequireTextTest2())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        Foo.
    </test>
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementIllegalChildElements

def metadataAbstractElementIllegalChildElementTest1():
    """
    No child elements, child elements not allowed.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementIllegalChildElements,
    ...     metadataAbstractElementIllegalChildElementTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementIllegalChildElementTest2():
    """
    Child elements, child elements not allowed.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementIllegalChildElements,
    ...     metadataAbstractElementIllegalChildElementTest2())
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
        <bar />
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementIllegalChildElementTest2():
    """
    Child elements, child elements are optional.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementIllegalChildElements,
    ...     metadataAbstractElementIllegalChildElementTest2(),
    ...     optionalChildElements=["foo", "bar"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
        <bar />
    </test>
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementKnownChildElements

def metadataAbstractElementRequiredChildElementTest1():
    """
    No child elements, child elements required. Report error.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest1(),
    ...     requiredChildElements=["foo"])
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredChildElementTest2():
    """
    No child elements, child elements required. Report warning.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest2(),
    ...     requiredChildElements=["foo"], missingChildElementsAlertLevel="warning")
    ['WARNING']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredChildElementTest3():
    """
    Child elements, child elements required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest3(),
    ...     requiredChildElements=["foo"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredChildElementTest4():
    """
    Child elements, unknown child elements, child elements required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest4(),
    ...     requiredChildElements=["foo"])
    ['WARNING']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
        <bar />
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredChildElementTest5():
    """
    Unknown child elements, child elements required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest5(),
    ...     requiredChildElements=["foo"])
    ['WARNING', 'ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <bar />
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementRequiredChildElementTest6():
    """
    Optional child elements, child elements required.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest6(),
    ...     requiredChildElements=["foo"],
    ...     optionalChildElements=["bar"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
        <bar />
    </test>
    """
    return ElementTree.fromstring(metadata)

# testMetadataAbstractElementOptionalChildElements

def metadataAbstractElementOptionalChildElementTest1():
    """
    No child elements. No optional child elements.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalChildElements,
    ...     metadataAbstractElementOptionalChildElementTest1(),
    ...     optionalChildElements=[])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalChildElementTest2():
    """
    No child elements. Optional child elements. Don't note.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalChildElements,
    ...     metadataAbstractElementOptionalChildElementTest2(),
    ...     optionalChildElements=["foo"],
    ...     noteMissingChildElements=False)
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalChildElementTest3():
    """
    No child elements. Optional child elements. Do note.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalChildElements,
    ...     metadataAbstractElementOptionalChildElementTest3(),
    ...     optionalChildElements=["foo"],
    ...     noteMissingChildElements=True)
    ['NOTE']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementOptionalChildElementTest4():
    """
    Child elements. Optional child elements.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementOptionalChildElements,
    ...     metadataAbstractElementOptionalChildElementTest4(),
    ...     optionalChildElements=["foo"])
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <foo />
    </test>
    """
    return ElementTree.fromstring(metadata)



# testMetadataAbstractTextElements

def metadataAbstractElementTextTest1():
    """
    Valid.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractTextElements,
    ...     metadataAbstractElementTextTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </test>
    """
    return ElementTree.fromstring(metadata)


# testMetadataAbstractElementLanguages

def metadataAbstractElementTextLanguagesTest1():
    """
    Valid.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementLanguages,
    ...     metadataAbstractElementTextLanguagesTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementTextLanguagesTest2():
    """
    Duplicate undefined.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementLanguages,
    ...     metadataAbstractElementTextLanguagesTest2())
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <text>Foo.</text>
        <text>Foo.</text>
    </test>
    """
    return ElementTree.fromstring(metadata)

def metadataAbstractElementTextLanguagesTest3():
    """
    Duplicate defined.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementLanguages,
    ...     metadataAbstractElementTextLanguagesTest3())
    ['ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <text lang="en">Foo.</text>
        <text lang="en">Foo.</text>
    </test>
    """
    return ElementTree.fromstring(metadata)


# testMetadataStructureTopElement

def metadataTopElementTest1():
    """
    Valid metadata and version.

    >>> doctestFunction1(testMetadataStructureTopElement, metadataTopElementTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataTopElementTest2():
    """
    Metadata not top element.

    >>> doctestFunction1(testMetadataStructureTopElement, metadataTopElementTest2())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <notmetadata version="1.0">
    </notmetadata>
    """
    return ElementTree.fromstring(metadata)

def metadataTopElementTest3():
    """
    Unknown attribute.

    >>> doctestFunction1(testMetadataStructureTopElement, metadataTopElementTest3())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0" something="ABC">
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataTopElementTest4():
    """
    Version is not 1.0

    >>> doctestFunction1(testMetadataStructureTopElement, metadataTopElementTest4())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="2.0">
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataTopElementTest5():
    """
    Text in top element.

    >>> doctestFunction1(testMetadataStructureTopElement, metadataTopElementTest5())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        ABC
    </metadata>
    """
    return ElementTree.fromstring(metadata)


# testMetadataChildElements

def metadataChildElementTest1():
    """
    Unknown element.

    >>> doctestFunction1(testMetadataChildElements, metadataChildElementTest1())
    (None, 'WARNING')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        <foo>bar</foo>
    </metadata>
    """
    return ElementTree.fromstring(metadata)


# testMetadataElementExistence

def metadataMissingElementExistenceTest1():
    """
    All elements present.

    >>> doctestFunction2(testMetadataElementExistence, metadataMissingElementExistenceTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        <uniqueid />
        <vendor />
        <credits />
        <description />
        <license />
        <copyright />
        <trademark />
        <licensee />
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataMissingElementExistenceTest2():
    """
    Missing uniqueid.

    >>> doctestFunction2(testMetadataElementExistence, metadataMissingElementExistenceTest2())
    ['WARNING']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        <vendor />
        <credits />
        <description />
        <license />
        <copyright />
        <trademark />
        <licensee />
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataMissingElementExistenceTest3():
    """
    No elements present.

    >>> doctestFunction2(testMetadataElementExistence, metadataMissingElementExistenceTest3())
    ['WARNING', 'NOTE', 'NOTE', 'NOTE', 'NOTE', 'NOTE', 'NOTE', 'NOTE']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
    </metadata>
    """
    return ElementTree.fromstring(metadata)


# testMetadataDuplicateElements

def metadataMissingDuplicateElementsTest1():
    """
    No duplicates.

    >>> doctestFunction2(testMetadataDuplicateElements, metadataMissingDuplicateElementsTest1())
    []
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        <uniqueid />
        <vendor />
        <credits />
        <description />
        <license />
        <copyright />
        <trademark />
        <licensee />
    </metadata>
    """
    return ElementTree.fromstring(metadata)

def metadataMissingDuplicateElementsTest2():
    """
    Two duplicates.

    >>> doctestFunction2(testMetadataDuplicateElements, metadataMissingDuplicateElementsTest2())
    ['WARNING', 'WARNING']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <metadata version="1.0">
        <uniqueid />
        <uniqueid />
        <vendor />
        <credits />
        <description />
        <license />
        <copyright />
        <trademark />
        <licensee />
        <licensee />
    </metadata>
    """
    return ElementTree.fromstring(metadata)

# testMetadataUniqueid

def metadataUniqueidTest1():
    """
    Valid element.

    >>> doctestFunction1(testMetadataUniqueid, metadataUniqueidTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <uniqueid id="com.example.foo.1234" />
    """
    return ElementTree.fromstring(metadata)


# testMetadataVendor

def metadataVendorTest1():
    """
    Valid element.

    >>> doctestFunction1(testMetadataVendor, metadataVendorTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <vendor name="Example" url="http://example.com" />
    """
    return ElementTree.fromstring(metadata)


# testMetadataCredits

def metadataCreditsTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataCredits, metadataCreditsTest1(), resultIndex=0)
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <credits>
        <credit name="Example" url="http://example.com" role="example.com"/>
    </credits>
    """
    return ElementTree.fromstring(metadata)

def metadataCreditsTest2():
    """
    No credit element.

    >>> doctestFunction1(testMetadataCredits, metadataCreditsTest2(), resultIndex=0)
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <credits>
    </credits>
    """
    return ElementTree.fromstring(metadata)


# testMetadataCredit

def metadataCreditTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataCredit, metadataCreditTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <credit name="Example" url="http://example.com" role="Test"/>
    """
    return ElementTree.fromstring(metadata)


# testMetadataDescription

def metadataDescriptionTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataDescription, metadataDescriptionTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <description>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </description>
    """
    return ElementTree.fromstring(metadata)


# testMetadataLicense

def metadataLicenseTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataLicense, metadataLicenseTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <license>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </license>
    """
    return ElementTree.fromstring(metadata)


# testMetadataCopyright

def metadataCopyrightTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataCopyright, metadataCopyrightTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <copyright>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </copyright>
    """
    return ElementTree.fromstring(metadata)


# testMetadataTrademark

def metadataTrademarkTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataTrademark, metadataTrademarkTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <trademark>
        <text>Foo.</text>
        <text lang="en">Foo.</text>
        <text lang="ko">Foo.</text>
    </trademark>
    """
    return ElementTree.fromstring(metadata)

# testMetadataLicensee

def metadataLicenseeTest1():
    """
    Valid element.

    >>> doctestFunction1(testMetadataLicensee, metadataLicenseeTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <licensee name="Example" />
    """
    return ElementTree.fromstring(metadata)

# testMetadataExtension

def metadataExtensionTest1():
    """
    Valid.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest1())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <name>Foo Item Name</name>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest2():
    """
    Valid. No name.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest2())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <item>
            <name>Foo Item Name</name>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest3():
    """
    Invalid. No item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest3())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest4():
    """
    Invalid. No name in item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest4())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest5():
    """
    Invalid. No value in item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest5())
    (None, 'ERROR')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest6():
    """
    Valid. More than one name.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest6())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <name lang="en">Extension Name</name>
        <name lang="ko">Extension Name</name>
        <item>
            <name>Foo Item Name</name>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest7():
    """
    Valid. More than one item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest7())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <name>Foo Item Name</name>
            <value>Foo Item Value</value>
        </item>
        <item>
            <name>Bar Item Name</name>
            <value>Bar Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest8():
    """
    Valid. More than one name in item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest8())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <name>Foo Item Name</name>
            <name lang="en">Foo Item Name</name>
            <name lang="ko">Foo Item Name</name>
            <value>Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

def metadataExtensionTest9():
    """
    Valid. More than one value in item.

    >>> doctestFunction1(testMetadataExtension, metadataExtensionTest9())
    (None, 'PASS')
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <extension>
        <name>Extension Name</name>
        <item>
            <name>Foo Item Name</name>
            <value>Foo Item Value</value>
            <value lang="en">Foo Item Value</value>
            <value lang="ko">Foo Item Value</value>
        </item>
    </extension>
    """
    return ElementTree.fromstring(metadata)

# testPrivateDataOffsetAndLength

def privateDataOffsetLengthTest1():
    """
    Valid empty offset and length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = 0
    header["privLength"] = 0
    return packTestHeader(header)

def privateDataOffsetLengthTest2():
    """
    privOffset = 0, privLength = 1.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest2())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = 0
    header["privLength"] = 1
    return packTestHeader(header)

def privateDataOffsetLengthTest3():
    """
    privOffset = 1, privLength = 3.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest3())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = 1
    header["privLength"] = 0
    return packTestHeader(header)

def privateDataOffsetLengthTest4():
    """
    Valid offset and length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest4())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"]
    header["privLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def privateDataOffsetLengthTest5():
    """
    Offset before end of the directory.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest5())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"] - 4
    header["privLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def privateDataOffsetLengthTest6():
    """
    Offset before end of the metadata.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest6())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["metaOffset"] = header["length"]
    header["metaLength"] = 4
    header["privOffset"] = header["length"] + 2
    header["privLength"] = 4
    header["length"] += 8
    return packTestHeader(header)

def privateDataOffsetLengthTest7():
    """
    Offset after end of file.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest7())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"] + 2
    header["privLength"] = 1
    header["length"] += 1
    return packTestHeader(header)

def privateDataOffsetLengthTest8():
    """
    Offset + length greater than length of file.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest8())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"]
    header["privLength"] = 2
    header["length"] += 1
    return packTestHeader(header)

def privateDataOffsetLengthTest9():
    """
    Length longer than available length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest9())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"]
    header["privLength"] = 2
    header["length"] += 1
    return packTestHeader(header)

def privateDataOffsetLengthTest10():
    """
    Offset doesn't begin immediately after last table.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest10())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"] + 4
    header["privLength"] = 1
    header["length"] += 2
    return packTestHeader(header)

def privateDataOffsetLengthTest11():
    """
    Offset doesn't begin on a four-byte boundary.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest11())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    header["privOffset"] = header["length"] + 3
    header["privLength"] = 1
    header["length"] += 2
    return packTestHeader(header)

# testPrivateDataPadding

def privateDataPaddingTest1():
    """
    Valid padding: No padding needed.

    >>> doctestFunction1(testPrivateDataPadding, privateDataPaddingTest1())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    header["priveOffset"] = header["length"]
    header["privLength"] = 8
    header["length"] += 8
    return packTestHeader(header)

def privateDataPaddingTest2():
    """
    Valid padding: Padded with  null.

    >>> doctestFunction1(testPrivateDataPadding, privateDataPaddingTest2())
    (None, 'PASS')
    """
    header = defaultTestData(header=True)
    privateData = "\0" * 8
    header["privOffset"] = header["length"]
    header["privLength"] = 7
    header["length"] += 8
    return packTestHeader(header) + privateData

def privateDataPaddingTest3():
    """
    Invalid padding: Padded with something other than null.

    >>> doctestFunction1(testPrivateDataPadding, privateDataPaddingTest3())
    (None, 'ERROR')
    """
    header = defaultTestData(header=True)
    privateData = "A" * 8
    header["privOffset"] = header["length"]
    header["privLength"] = 7
    header["length"] += 8
    return packTestHeader(header) + privateData

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=False)
