import os
import re

def parseFile(filename):
    fileExtension = os.path.splitext(filename)[-1]

    returnData = ''

    if fileExtension == '.txt':
        returnData = parseTxt(filename)
    elif fileExtension == '.bvh':
        returnData = parseBvh(filename)
    else:
        print('File with extension {} cannot be parsed'.format(fileExtension))

    return returnData

def parseTxt(filename):
    filedata = open(filename).readlines()

    # check if first line is \n. If so, remove it.
    if filedata[0] == '\n':
        filedata = filedata[1:]

    txtDict = parseTxtDict(filename, filedata)

    return txtDict


def parseBvh(filename):
    pass

def parseTxtDict(filename, filedata):
    txtDict = {'filename': filename,
               'frames': [],
               'nodes': {}}

    nodeline = filedata[0]
    # remove \n at end
    #nodeline = nodeline.strip()

    if nodeline.lower().startswith('frame'):
        nodes = re.split(r'\t+', nodeline)
        allNodesDict = {}
        for node in nodes:
            uniqueNodeKey = node.split(' ')[0]
            # node's unique identifier does not yet exist in allNodesDict --> add unique identifier as key AND node as value
            if not node.lower().startswith('frame') and uniqueNodeKey not in allNodesDict:
                xyzNodeValueDict = {node: {}}
                allNodesDict[uniqueNodeKey] = {'enabled': True, 'xyzNodes': xyzNodeValueDict}
            # node's unique identifier already exists in allNodesDict --> update its value dictionary with new child node
            elif uniqueNodeKey in allNodesDict:
                allNodesNestedDict = allNodesDict[uniqueNodeKey]
                allNodesNestedDict['xyzNodes'].update({node: {}})
        txtDict['nodes'].update(allNodesDict)
    else:
        print('Cannot parse nodes from first line in {}. Expected line start with "frame".\nFirst line is: {}'.format(os.path.basename(filename), filedata[0]))

    # this may need to be placed higher up --> we also don't want this to happen if the block above did not succeed
    # TODO: what if framelines len is 0? this shouldn't really happen, but we do need to handle this
    framelines = filedata[1:]
    frameList = []

    testLine = framelines[0]
    testLine = testLine.strip()
    testValues = re.split(r'\t+', testLine)
    nodeNum = len(testValues[1:])

    frameValueList = []
    for i in range(nodeNum):
        frameValueList.append({})

    for line in framelines:
        # remove \n at end
        line = line.strip()
        values = re.split(r'\t+', line)
        frame = int(values[0])
        frameList.append(frame)

        for index, value in enumerate(values[1:]):
            tempRootDict = frameValueList[index]
            tempNestedDict = {'enabled': True, 'value': value}
            tempRootDict[frame] = tempNestedDict
            frameValueList[index] = tempRootDict

    nodesDict = txtDict.get('nodes')
    listIndex = 0
    for nodesDictKey in nodesDict:
        nestedNodeDict = nodesDict.get(nodesDictKey)
        xyzNodesDict = nestedNodeDict['xyzNodes']
        for xyzNodesDictKey in xyzNodesDict:
            xyzNodesDict[xyzNodesDictKey] = {'enabled': True, 'coords': frameValueList[listIndex]}
            listIndex += 1

    txtDict['frames'] = frameList

    import json
    print("* * * * * * * * * * txtDict: {}".format(json.dumps(txtDict, indent=4)))

    return txtDict

def getFrameRange(framesList):
    condensedFramerangeList = []

    currentIndex = 1
    previousIndex = 0
    startValue = framesList[0]

    if len(framesList) == 0:
        print('framesList is empty')
    elif len(framesList) == 1:
        condensedFramerangeList = framesList
    else:
        while currentIndex != len(framesList):
            if (int(framesList[currentIndex]) != (int(framesList[previousIndex]) + 1)) or (currentIndex == (len(framesList) - 1)):
                if (int(framesList[currentIndex]) == (int(framesList[previousIndex]) + 1)) and (currentIndex == (len(framesList) - 1)):
                    endValue = framesList[currentIndex]
                else:
                    endValue = framesList[previousIndex]
                if startValue == endValue:
                    condensedFramerangeList.append(str(endValue))
                else:
                    appendStr = '{}-{}'.format(startValue, endValue)
                    condensedFramerangeList.append(appendStr)
                if (int(framesList[currentIndex]) != (int(framesList[previousIndex]) + 1)) and (currentIndex == (len(framesList) - 1)):
                    condensedFramerangeList.append(framesList[currentIndex])
                startValue = framesList[currentIndex]
                previousIndex = currentIndex
                currentIndex += 1
            else:
                previousIndex = currentIndex
                currentIndex += 1

    print("frames: {}".format(condensedFramerangeList))

    return condensedFramerangeList