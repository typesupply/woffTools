import struct
import zlib
from xml.etree import ElementTree
from fontTools.ttLib.sfnt import getSearchRange, SFNTDirectoryEntry
from woffTools.tools.validate import structPack, HTMLReporter,\
    calcChecksum, calcHeadCheckSum,\
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
    testMetadataAbstractElementOptionalAttributes,\
    testMetadataAbstractElementRequiredAttributes,\
    testMetadataAbstractElementKnownChildElements,\
    testMetadataAbstractElementRequiredText,\
    testMetadataAbstractElementUnknownAttributes,\
    testMetadataAbstractTextElements,\
    testMetadataAbstractTextElementLanguages,\
    testMetadataChildElements,\
    testMetadataCopyright,\
    testMetadataCredit,\
    testMetadataCredits,\
    testMetadataDecompressedLength,\
    testMetadataDecompression,\
    testMetadataDescription,\
    testMetadataDuplicateElements,\
    testMetadataElementExistence,\
    testMetadataLicense,\
    testMetadataLicensee,\
    testMetadataOffsetAndLength,\
    testMetadataParse,\
    testMetadataStructureTopElement,\
    testMetadataTrademark,\
    testMetadataUniqueid,\
    testMetadataVendor,\
    testPrivateDataOffsetAndLength,\
    testTableDataStart,\
    testTableDecompression,\
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

def doctestMetadataAbstractElementFunction(func, element,
    requiredAttributes=None, optionalAttributes=None,
    requireText=None,
    knownChildElements=None, missingChildElementsAlertLevel=None,
    noteMissingOptionalAttributes=None):
    reporter = HTMLReporter()
    reporter.logTestTitle("doctest")
    kwargs = {}
    if requiredAttributes is not None:
        kwargs["requiredAttributes"] = requiredAttributes
    if optionalAttributes is not None:
        kwargs["optionalAttributes"] = optionalAttributes
    if knownChildElements:
        kwargs["knownChildElements"] = knownChildElements
    if missingChildElementsAlertLevel:
        kwargs["missingChildElementsAlertLevel"] = missingChildElementsAlertLevel
    if noteMissingOptionalAttributes is not None:
        kwargs["noteMissingOptionalAttributes"] = noteMissingOptionalAttributes
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

testDataTableData = "\0" * 1000

def packTestHeader(data=None):
    if data is None:
        data = testDataHeaderDict
    return structPack(headerFormat, data)

def packTestDirectory(directory=None):
    if directory is None:
        directory = testDataDirectoryList
    data = ""
    for table in directory:
        data += structPack(directoryFormat, table)
    return data

def packTestFont(header=None, directory=None, tableData=None, metadata=None,
        updateDirectoryEntries=True,
        compressMetadata=True, metaOrigLength=None):
    from copy import deepcopy
    if header is None:
        header = testDataHeaderDict
    if directory is None:
        directory = testDataDirectoryList
    if tableData is None:
        tableData = {}
        for entry in directory:
            tableData[entry["tag"]] = (testDataTableData, testDataTableData)
    # copy
    header = dict(header)
    directory = deepcopy(directory)
    tableData = dict(tableData)
    # storage
    orderedData = []
    # table data
    header["numTables"] = len(tableData)
    offset = headerSize + (directorySize * 3)
    for entry in directory:
        tag = entry["tag"]
        origData, compData = tableData[tag]
        if updateDirectoryEntries:
            entry["offset"] = offset
            entry["origLength"] = len(origData)
            entry["compLength"] = len(compData)
            entry["origChecksum"] = calcChecksum(tag, origData)
        offset += len(compData)
        orderedData.append(compData)
    # metadata
    if metadata is not None:
        if metaOrigLength is None:
            metaOrigLength = len(metadata)
        if compressMetadata:
            metadata = zlib.compress(metadata)
        header["metaOffset"] = offset
        header["metaOrigLength"] = metaOrigLength
        header["metaLength"] = len(metadata)
        header["length"] += len(metadata)
        orderedData.append(metadata)
    # compile and return
    return packTestHeader(header) + packTestDirectory(directory) + "".join(orderedData)


# --------------
# test functions
# --------------

# testHeaderSize

def headerSizeTest1():
    """
    File with proper length.

    >>> doctestFunction1(testHeaderSize, headerSizeTest1())
    (None, 'PASS')
    """
    return packTestHeader()

def headerSizeTest2():
    """
    File with improper length.

    >>> doctestFunction1(testHeaderSize, headerSizeTest2())
    (True, 'ERROR')
    """
    return packTestHeader()[:-1]


# testHeaderStructure

def headerStructureTest1():
    """
    Valid structure.

    >>> doctestFunction1(testHeaderStructure, headerStructureTest1())
    (None, 'PASS')
    """
    return packTestHeader()


# testHeaderSignature

def headerSignatureTest1():
    """
    Valid signature.

    >>> doctestFunction1(testHeaderSignature, headerSignatureTest1())
    (None, 'PASS')
    """
    return packTestHeader()

def headerSignatureTest2():
    """
    Invalid signature.

    >>> doctestFunction1(testHeaderSignature, headerSignatureTest2())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["signature"] = "XXXX"
    return packTestHeader(header)


# testHeaderFlavor

def flavorTest1():
    """
    Unknown flavor.

    >>> doctestFunction1(testHeaderFlavor, flavorTest1())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["flavor"] = "XXXX"
    return packTestHeader(header)

def flavorTest2():
    """
    Flavor is OTTO, CFF is in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest2())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = [dict(d) for d in testDataDirectoryList]
    directory[-1]["tag"] = "CFF "
    return packTestHeader(header) + packTestDirectory(directory)

def flavorTest3():
    """
    Flavor is 0x00010000, CFF is in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest3())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["flavor"] = "\000\001\000\000"
    header["numTables"] = len(testDataDirectoryList)
    directory = [dict(d) for d in testDataDirectoryList]
    directory[-1]["tag"] = "CFF "
    return packTestHeader(header) + packTestDirectory(directory)

def flavorTest4():
    """
    Flavor is 0x00010000, CFF is not in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest4())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["flavor"] = "\000\001\000\000"
    header["numTables"] = len(testDataDirectoryList)
    return packTestHeader(header) + packTestDirectory(testDataDirectoryList)

def flavorTest5():
    """
    Flavor is OTTO, CFF is not in tables.

    >>> doctestFunction1(testHeaderFlavor, flavorTest5())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["flavor"] = "OTTO"
    header["numTables"] = len(testDataDirectoryList)
    return packTestHeader(header) + packTestDirectory(testDataDirectoryList)


# testHeaderLength

def headerLengthTest1():
    """
    Data is long enough for defined length.

    >>> doctestFunction1(testHeaderLength, headerLengthTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + 3
    return packTestHeader(header) + ("\0" * 3)

def headerLengthTest2():
    """
    Data is not long enough for defined length.

    >>> doctestFunction1(testHeaderLength, headerLengthTest2())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + 3
    return packTestHeader(header) + "\0"

def headerLengthTest3():
    """
    Data is long enough for header and directory.

    >>> doctestFunction1(testHeaderLength, headerLengthTest3())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + (directorySize * len(testDataDirectoryList))
    return packTestHeader(header) + packTestDirectory()

def headerLengthTest4():
    """
    Data is not long enough for header and directory.

    >>> doctestFunction1(testHeaderLength, headerLengthTest4())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["length"] = 1
    return packTestHeader(header) + packTestDirectory()

def headerLengthTest5():
    """
    Data is long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest5())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + 10
    header["metaLength"] = 10
    return packTestHeader(header) + ("\0" * 10)

def headerLengthTest6():
    """
    Data is not long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest6())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + 10
    header["metaLength"] = 10
    return packTestHeader(header) + ("\0" * 5)

def headerLengthTest7():
    """
    Data is long enough for header and private data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest7())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["length"] = headerSize + 10
    header["privLength"] = 10
    return packTestHeader(header) + ("\0" * 10)

def headerLengthTest8():
    """
    Data is long enough for header and meta data.

    >>> doctestFunction1(testHeaderLength, headerLengthTest8())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
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
    header = dict(testDataHeaderDict)
    header["reserved"] = 0
    return packTestHeader(header)

def headerReservedTest2():
    """
    reserved is 1.

    >>> doctestFunction1(testHeaderReserved, headerReservedTest2())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["reserved"] = 1
    return packTestHeader(header)


# testHeaderTotalSFNTSize

def totalSFNTSizeTest1():
    """
    Valid totalSfntSize.

    >>> doctestFunction1(testHeaderTotalSFNTSize, totalSFNTSizeTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    numTables = len(testDataDirectoryList)
    header["numTables"] = numTables
    header["totalSfntSize"] = sfntHeaderSize + (numTables * sfntDirectoryEntrySize) + (len(testDataTableData) * numTables)
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["origLength"] = len(testDataTableData)
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)

def totalSFNTSizeTest2():
    """
    Invalid totalSfntSize.

    >>> doctestFunction1(testHeaderTotalSFNTSize, totalSFNTSizeTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    numTables = len(testDataDirectoryList)
    header["numTables"] = numTables
    header["totalSfntSize"] = sfntHeaderSize + (numTables * sfntDirectoryEntrySize) + (len(testDataTableData) * numTables) - 1
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["origLength"] = len(testDataTableData)
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)


# testHeaderMajorVersionAndMinorVersion

def headerVersionTest1():
    """
    0.0

    >>> doctestFunction1(testHeaderMajorVersionAndMinorVersion, headerVersionTest1())
    (None, 'WARNING')
    """
    header = dict(testDataHeaderDict)
    header["majorVersion"] = 0
    header["minorVersion"] = 0
    return packTestHeader(header)

def headerVersionTest2():
    """
    1.0

    >>> doctestFunction1(testHeaderMajorVersionAndMinorVersion, headerVersionTest2())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["majorVersion"] = 1
    return packTestHeader(header)


# testHeaderNumTables

def headerNumTablesTest1():
    """
    numTables is 0.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest1())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = 0
    return packTestHeader(header)

def headerNumTablesTest2():
    """
    numTables is 3 and 3 directory entries are packed.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest2())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    return packTestHeader(header) + packTestDirectory()

def headerNumTablesTest3():
    """
    numTables is 4 and 3 directory entries are packed.

    >>> doctestFunction1(testHeaderNumTables, headerNumTablesTest3())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList) + 1
    return packTestHeader(header) + packTestDirectory()


# testDirectoryTableOrder

def directoryOrderTest1():
    """
    Valid order.

    >>> doctestFunction1(testDirectoryTableOrder, directoryOrderTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    return packTestHeader(header) + packTestDirectory()

def directoryOrderTest2():
    """
    Reversed order.

    >>> doctestFunction1(testDirectoryTableOrder, directoryOrderTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    return packTestHeader(header) + packTestDirectory(reversed(testDataDirectoryList))


# testDirectoryBorders

def directoryOffsetLengthTest1():
    """
    Valid offsets and lengths.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + len(testDataDirectoryList)
    length = 1
    directory = [dict(d) for d in testDataDirectoryList]
    for d in directory:
        d["offset"] = offset
        d["compLength"] = length
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest2():
    """
    Offset within header/directory block.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest2())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + len(testDataDirectoryList)
    length = 1
    directory = [dict(d) for d in testDataDirectoryList]
    for d in directory:
        d["offset"] = 0
        d["compLength"] = length
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest3():
    """
    Offset after end of file.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest3())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + len(testDataDirectoryList)
    length = 1
    directory = [dict(d) for d in testDataDirectoryList]
    for d in directory:
        d["offset"] = 1000
    return packTestHeader(header) + packTestDirectory(directory)

def directoryOffsetLengthTest4():
    """
    Offset + length after end of file.

    >>> doctestFunction1(testDirectoryBorders, directoryOffsetLengthTest4())
    (True, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + len(testDataDirectoryList)
    length = 1
    directory = [dict(d) for d in testDataDirectoryList]
    for d in directory:
        d["offset"] = offset
        d["compLength"] = 10000
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)


# testDirectoryCompressedLength

def directoryCompressedLengthTest1():
    """
    compLength less than origLength.

    >>> doctestFunction1(testDirectoryCompressedLength, directoryCompressedLengthTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["compLength"] = len(testDataTableData)
        table["origLength"] = len(testDataTableData) + 1
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)

def directoryCompressedLengthTest2():
    """
    compLength greater than origLength.

    >>> doctestFunction1(testDirectoryCompressedLength, directoryCompressedLengthTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["compLength"] = len(testDataTableData) + 1
        table["origLength"] = len(testDataTableData)
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)


# testDirectoryDecompressedLength

def decompressedLengthTest1():
    """
    Matching decompressed and origLengths.

    >>> doctestFunction1(testDirectoryDecompressedLength, decompressedLengthTest1())
    (None, 'PASS')
    """
    origData = testDataTableData
    compData = zlib.compress(origData)
    tableData = {}
    for table in testDataDirectoryList:
        tag = table["tag"]
        tableData[tag] = (origData, compData)
    return packTestFont(tableData=tableData)

def decompressedLengthTest2():
    """
    Non-matching decompressed and origLengths.

    >>> doctestFunction1(testDirectoryDecompressedLength, decompressedLengthTest2())
    (None, 'ERROR')
    """
    origData = testDataTableData
    compData = zlib.compress(origData)
    directory = []
    tableData = {}
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    for table in testDataDirectoryList:
        table = dict(table)
        tag = table["tag"]
        table["offset"] = offset
        table["origLength"] = len(testDataTableData) + 1
        table["compLength"] = len(compData)
        directory.append(table)
        tableData[tag] = (origData, compData)
        offset += len(compData)
    return packTestFont(directory=directory, tableData=tableData, updateDirectoryEntries=False)


# testDirectoryChecksums

def checksumTest1():
    """
    Correct checksums.

    >>> doctestFunction1(testDirectoryChecksums, checksumTest1())
    (None, 'PASS')
    """
    return packTestFont()

def checksumTest2():
    """
    Incorrect checksums.

    >>> doctestFunction1(testDirectoryChecksums, checksumTest2())
    (None, 'ERROR')
    """
    directory = []
    offset = headerSize + (directorySize * 3)
    for table in testDataDirectoryList:
        table = dict(table)
        table["offset"] = offset
        table["origLength"] = len(testDataTableData)
        table["compLength"] = len(testDataTableData)
        table["origChecksum"] = 123
        directory.append(table)
        offset += len(testDataTableData)
    return packTestFont(directory=directory, updateDirectoryEntries=False)


# testTableDataStart

def tableStartTest1():
    """
    Proper position.

    >>> doctestFunction1(testTableDataStart, tableStartTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    for table in testDataDirectoryList:
        table = dict(table)
        table["offset"] = offset
        directory.append(table)
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)

def tableStartTest2():
    """
    Improper position.

    >>> doctestFunction1(testTableDataStart, tableStartTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    offset = headerSize + (directorySize * len(testDataDirectoryList)) + 1
    for table in testDataDirectoryList:
        table = dict(table)
        table["offset"] = offset
        directory.append(table)
        offset += 1
    return packTestHeader(header) + packTestDirectory(directory)


# testTablePadding

def paddingTest1():
    """
    Proper padding.

    >>> doctestFunction1(testTablePadding, paddingTest1(), -2)
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["offset"] = 0
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)

def paddingTest2():
    """
    Offset not on a 4-bye boundary.

    >>> doctestFunction1(testTablePadding, paddingTest2(), -2)
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    directory = []
    for table in testDataDirectoryList:
        table = dict(table)
        table["offset"] = 1
        directory.append(table)
    return packTestHeader(header) + packTestDirectory(directory)

def paddingTest3():
    """
    Proper end padding, no metadata or private data.

    >>> doctestFunction1(testTablePadding, paddingTest3())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["length"] = len(testDataTableData)
    return packTestHeader(header) + packTestDirectory([])

def paddingTest4():
    """
    Improper end padding, no metadata or private data.

    >>> doctestFunction1(testTablePadding, paddingTest4())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["length"] = len(testDataTableData) + 1
    return packTestHeader(header) + packTestDirectory([])

def paddingTest5():
    """
    Proper end padding, metadata, no private data.

    >>> doctestFunction1(testTablePadding, paddingTest5())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["metaOffset"] = len(testDataTableData)
    return packTestHeader(header) + packTestDirectory([])

def paddingTest6():
    """
    Improper end padding, metadata, no private data.

    >>> doctestFunction1(testTablePadding, paddingTest6())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["metaOffset"] = len(testDataTableData) + 1
    return packTestHeader(header) + packTestDirectory([])

def paddingTest7():
    """
    Proper end padding, no metadata, private data.

    >>> doctestFunction1(testTablePadding, paddingTest7())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["privOffset"] = len(testDataTableData)
    return packTestHeader(header) + packTestDirectory([])

def paddingTest8():
    """
    Improper end padding, no metadata, private data.

    >>> doctestFunction1(testTablePadding, paddingTest8())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["privOffset"] = len(testDataTableData) + 1
    return packTestHeader(header) + packTestDirectory([])


# testTableDecompression

def decompressionTest1():
    """
    Properly compressed data.

    >>> doctestFunction1(testTableDecompression, decompressionTest1())
    (False, 'PASS')
    """
    origData = testDataTableData
    compData = zlib.compress(origData)
    tableData = {}
    for table in testDataDirectoryList:
        tag = table["tag"]
        tableData[tag] = (origData, compData)
    return packTestFont(tableData=tableData)

def decompressionTest2():
    """
    Improperly compressed data.

    >>> doctestFunction1(testTableDecompression, decompressionTest2())
    (True, 'ERROR')
    """
    origData = testDataTableData
    compData = zlib.compress(origData)
    compData = "".join(reversed([i for i in compData]))
    tableData = {}
    for table in testDataDirectoryList:
        tag = table["tag"]
        tableData[tag] = (origData, compData)
    return packTestFont(tableData=tableData)

# testHeadCheckSumAdjustment

def headCheckSumAdjustmentTest1():
    """
    Valid checksum.

    >>> doctestFunction1(testHeadCheckSumAdjustment, headCheckSumAdjustmentTest1())
    (None, 'PASS')
    """
    origData = testDataTableData
    tableData = {}
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    for table in testDataDirectoryList:
        tag = table["tag"]
        tableData[tag] = (origData, origData)
        if table["tag"] == "head":
            headOffset = offset
        offset += len(origData)
    woffData = packTestFont(tableData=tableData)
    checkSumAdjustment = calcHeadCheckSum(woffData)
    checkSumAdjustment = struct.pack(">L", checkSumAdjustment)
    woffData = woffData[:headOffset+8] + checkSumAdjustment + woffData[headOffset+12:]
    return woffData

def headCheckSumAdjustmentTest2():
    """
    Invalid checksum.

    >>> doctestFunction1(testHeadCheckSumAdjustment, headCheckSumAdjustmentTest2())
    (None, 'ERROR')
    """
    return packTestFont()


# testMetadataOffsetAndLength

def metadataOffsetLengthTest1():
    """
    Valid empty offset and length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["metaOffset"] = 0
    header["metaLength"] = 0
    return packTestHeader(header)

def metadataOffsetLengthTest2():
    """
    metaOffset = 0, metaLength = 1.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["metaOffset"] = 0
    header["metaLength"] = 1
    return packTestHeader(header)

def metadataOffsetLengthTest3():
    """
    metaOffset = 1, metaLength = 3.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest3())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["metaOffset"] = 1
    header["metaLength"] = 0
    return packTestHeader(header)

def metadataOffsetLengthTest4():
    """
    Valid offset and length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest4())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["metaLength"] = 1
    return packTestFont(header=header)

def metadataOffsetLengthTest5():
    """
    Offset before end of the directory.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest5())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) - 4
    header["metaLength"] = 1
    return packTestFont(header=header)

def metadataOffsetLengthTest6():
    """
    Offset after end of file.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest6())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaOffset"] = header["length"] + 4
    header["metaLength"] = 1
    return packTestFont(header=header)

def metadataOffsetLengthTest7():
    """
    Offset + length greater than length of file.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest7())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["metaLength"] = 2
    return packTestFont(header=header)

def metadataOffsetLengthTest8():
    """
    Length longer than available length.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest8())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["metaLength"] = 2
    return packTestFont(header=header)

def metadataOffsetLengthTest9():
    """
    Offset doesn't begin immediately after last table.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest9())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 2
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 4
    header["metaLength"] = 1
    return packTestFont(header=header)

def metadataOffsetLengthTest10():
    """
    Offset doesn't begin on a four-byte boundary.

    >>> doctestFunction1(testMetadataOffsetAndLength, metadataOffsetLengthTest10())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 2
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["metaLength"] = 1
    return packTestFont(header=header)


# shouldSkipMetadataTest

def metadataSkipTest1():
    """
    Have metadata.

    >>> reporter = HTMLReporter()
    >>> shouldSkipMetadataTest(metadataSkipTest1(), reporter)
    >>> reporter.testResults
    []
    """
    metadata = "\0" * 1000
    return packTestFont(metadata=metadata)

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
    return packTestFont()


# testMetadataDecompression

def metadataDecompressionTest1():
    """
    Properly compressed.

    >>> doctestFunction1(testMetadataDecompression, metadataDecompressionTest1())
    (None, 'PASS')
    """
    metadata = "\0" * 1000
    return packTestFont(metadata=metadata)

def metadataDecompressionTest2():
    """
    Improperly compressed.

    >>> doctestFunction1(testMetadataDecompression, metadataDecompressionTest2())
    (True, 'ERROR')
    """
    metadata = "\0" * 1000
    metadata = "".join(reversed(zlib.compress(metadata)))
    return packTestFont(metadata=metadata, compressMetadata=False)


# testMetadataDecompressedLength

def metadataDecompressedLengthTest1():
    """
    Correct length..

    >>> doctestFunction1(testMetadataDecompressedLength, metadataDecompressedLengthTest1())
    (None, 'PASS')
    """
    metadata = "\0" * 1000
    return packTestFont(metadata=metadata)

def metadataDecompressedLengthTest2():
    """
    Incorrect length.

    >>> doctestFunction1(testMetadataDecompressedLength, metadataDecompressedLengthTest2())
    (None, 'ERROR')
    """
    metadata = "\0" * 1000
    return packTestFont(metadata=metadata, metaOrigLength=len(metadata) - 1)


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
    return packTestFont(metadata=metadata)

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
    return packTestFont(metadata=metadata)


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

# testMetadataAbstractElementKnownChildElements

def metadataAbstractElementRequiredChildElementTest1():
    """
    No child elements, child elements required. Report error.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractElementKnownChildElements,
    ...     metadataAbstractElementRequiredChildElementTest1(),
    ...     knownChildElements=["foo"])
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
    ...     knownChildElements=["foo"], missingChildElementsAlertLevel="warning")
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
    ...     knownChildElements=["foo"])
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
    ...     knownChildElements=["foo"])
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
    ...     knownChildElements=["foo"])
    ['WARNING', 'ERROR']
    """
    metadata = """<?xml version="1.0" encoding="UTF-8"?>
    <test>
        <bar />
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


# testMetadataAbstractTextElementLanguages

def metadataAbstractElementTextLanguagesTest1():
    """
    Valid.

    >>> doctestMetadataAbstractElementFunction(
    ...     testMetadataAbstractTextElementLanguages,
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
    ...     testMetadataAbstractTextElementLanguages,
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
    ...     testMetadataAbstractTextElementLanguages,
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


# testPrivateDataOffsetAndLength

def privateDataOffsetLengthTest1():
    """
    Valid empty offset and length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest1())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["privOffset"] = 0
    header["privLength"] = 0
    return packTestHeader(header)

def privateDataOffsetLengthTest2():
    """
    privOffset = 0, privLength = 1.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest2())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["privOffset"] = 0
    header["privLength"] = 1
    return packTestHeader(header)

def privateDataOffsetLengthTest3():
    """
    privOffset = 1, privLength = 3.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest3())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["privOffset"] = 1
    header["privLength"] = 0
    return packTestHeader(header)

def privateDataOffsetLengthTest4():
    """
    Valid offset and length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest4())
    (None, 'PASS')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["privLength"] = 1
    return packTestFont(header=header)

def privateDataOffsetLengthTest5():
    """
    Offset before end of the directory.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest5())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) - 4
    header["privLength"] = 1
    return packTestFont(header=header)

def privateDataOffsetLengthTest6():
    """
    Offset before end of the metadata.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest6())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 2
    header["metaOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["metaLength"] = 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) - 1
    header["privLength"] = 1
    return packTestFont(header=header)

def privateDataOffsetLengthTest7():
    """
    Offset after end of file.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest7())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData))
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 2
    header["privLength"] = 1
    return packTestFont(header=header)

def privateDataOffsetLengthTest8():
    """
    Offset + length greater than length of file.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest8())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) 
    header["privLength"] = 2
    return packTestFont(header=header)

def privateDataOffsetLengthTest9():
    """
    Length longer than available length.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest9())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privLength"] = 2
    return packTestFont(header=header)

def privateDataOffsetLengthTest10():
    """
    Offset doesn't begin immediately after last table.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest10())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 4
    header["privLength"] = 1
    return packTestFont(header=header)

def privateDataOffsetLengthTest11():
    """
    Offset doesn't begin on a four-byte boundary.

    >>> doctestFunction1(testPrivateDataOffsetAndLength, privateDataOffsetLengthTest11())
    (None, 'ERROR')
    """
    header = dict(testDataHeaderDict)
    header["numTables"] = len(testDataDirectoryList)
    offset = headerSize + (directorySize * len(testDataDirectoryList))
    header["length"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 3
    header["privOffset"] = offset + (len(testDataDirectoryList) * len(testDataTableData)) + 1
    header["privLength"] = 2
    return packTestFont(header=header)

if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=False)
